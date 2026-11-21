"""Run native Hermes ACP with a process-local, compact console toolset."""
import os
import subprocess
import sys
from pathlib import Path

TOOLS = frozenset({'terminal', 'process', 'read_file', 'write_file', 'patch', 'search_files'})


def enforce_console_environment():
    """Keep this process's MCP and approval policy after native env loading."""
    os.environ['HERMES_ACP_SKIP_CONFIGURED_MCP'] = '1'
    os.environ['HERMES_YOLO_MODE'] = '0'
    os.environ['HERMES_DISABLE_LAZY_INSTALLS'] = '1'
    os.environ.pop('HERMES_LAZY_INSTALL_TARGET', None)
    approval = sys.modules.get('tools.approval')
    if approval is not None and getattr(approval, '_YOLO_MODE_FROZEN', None) is not False:
        raise RuntimeError('compact profile unavailable')


def guard_environment_loading(env_loader):
    if 'hermes_cli.main' in sys.modules:
        raise RuntimeError('compact profile unavailable')
    original = env_loader.load_hermes_dotenv

    def guarded_load(*args, **kwargs):
        try:
            return original(*args, **kwargs)
        finally:
            enforce_console_environment()

    env_loader.load_hermes_dotenv = guarded_load
    enforce_console_environment()


def block_native_lazy_install(lazy):
    """Fail closed even while native environment loading temporarily overrides flags."""
    if not callable(getattr(lazy, '_allow_lazy_installs', None)) or not callable(getattr(lazy, '_venv_pip_install', None)):
        raise RuntimeError('compact profile unavailable')
    lazy._allow_lazy_installs = lambda: False
    def blocked(*args, **kwargs):
        raise RuntimeError('console lazy installs disabled')
    lazy._venv_pip_install = blocked


def block_native_bws_install(bitwarden):
    """Use an installed Bitwarden helper without downloading one."""
    find = getattr(bitwarden, 'find_bws', None)
    if not callable(find) or not callable(getattr(bitwarden, 'install_bws', None)):
        raise RuntimeError('compact profile unavailable')
    bitwarden.find_bws = lambda **kwargs: find(install_if_missing=False)
    def blocked(*args, **kwargs):
        raise RuntimeError('console Bitwarden helper installation disabled')
    bitwarden.install_bws = blocked


def enforce_approval_policy(approval):
    """Require per-operation native approval for detected dangerous commands."""
    names = ('_get_approval_mode', '_command_matches_permanent_allowlist',
             'is_current_session_yolo_enabled', 'is_session_yolo_enabled', 'is_approved')
    if approval._YOLO_MODE_FROZEN is not False or any(not callable(getattr(approval, n, None)) for n in names):
        raise RuntimeError('compact profile unavailable')
    approval._get_approval_mode = lambda: 'manual'
    approval._command_matches_permanent_allowlist = lambda command: False
    approval.is_current_session_yolo_enabled = lambda: False
    approval.is_session_yolo_enabled = lambda session_key: False
    approval.is_approved = lambda session_key, pattern_key: False


def enforce_managed_approval_policy(approval, context, batch):
    """Prepare v0.23 approval guards for an owned in-process adapter only."""
    required = ((approval, ('_yolo_active', '_command_matches_permanent_allowlist', '_approval_scope')),
                (context, ('_get_approval_mode',)), (batch, ('consume_prepared_guard',)))
    if (getattr(approval, '_YOLO_MODE_FROZEN', None) is not False
            or any(not callable(getattr(module, name, None)) for module, names in required for name in names)):
        raise RuntimeError('compact profile unavailable')
    context._get_approval_mode = lambda: 'manual'
    approval._yolo_active = lambda: False
    approval._command_matches_permanent_allowlist = lambda command: False
    approval._approval_scope = lambda session_key, pattern_key: None
    batch.consume_prepared_guard = lambda *args, **kwargs: None


def block_process_stdin(registry):
    """Prevent process input from bypassing the terminal command guard."""
    if not callable(getattr(registry, 'write_stdin', None)) or not callable(getattr(registry, 'submit_stdin', None)):
        raise RuntimeError('compact profile unavailable')
    def blocked(*args, **kwargs):
        return {'error': 'Console process input is disabled; use a terminal command.'}
    registry.write_stdin = blocked
    registry.submit_stdin = blocked


def configure_bash_probe(local_env, job_type):
    """Keep Windows Git Bash probes bounded inside their own process tree."""
    def probe(path):
        cached = local_env._bash_starts_cache.get(path)
        if cached is not None:
            return cached
        job = job_type([path, '--noprofile', '--norc', '-c', local_env._BASH_EXTERNAL_PROGRAM_PROBE],
                       cwd=os.getcwd())
        try:
            job.resume()
            try:
                code = job.wait(6)
                empty = job.wait_empty(3)
                if not empty:
                    job.stop()
                ok = code == 0 and empty
            except subprocess.TimeoutExpired:
                job.stop()
                ok = False
        finally:
            job.close()
        if not ok:
            local_env._bash_probe_details_cache[path] = 'Console-owned Git Bash probe failed or timed out.'
        local_env._bash_starts_cache[path] = ok
        return ok

    local_env._bash_starts = probe


def configure():
    import toolsets
    import acp_adapter.session as session
    import hermes_cli.mcp_startup as mcp

    # Fail closed if an updated Hermes runtime no longer has the expected hooks.
    if not isinstance(toolsets.TOOLSETS, dict) or not callable(session._expand_acp_enabled_toolsets):
        raise RuntimeError('compact profile unavailable')
    toolsets.TOOLSETS['console-compact'] = {
        'description': 'Console file and terminal tools', 'tools': sorted(TOOLS), 'includes': []}
    session._expand_acp_enabled_toolsets = lambda *args, **kwargs: ['console-compact']
    mcp.ensure_mcp_discovery_before_agent_build = lambda **kwargs: None
    original = session.SessionManager._make_agent

    def make_agent(self, **kwargs):
        agent = original(self, **kwargs)
        names = {item.get('function', {}).get('name') for item in agent.tools}
        if names != TOOLS:
            print('CONSOLE_COMPACT_PROFILE_UNAVAILABLE', file=sys.stderr, flush=True)
            raise RuntimeError('compact profile unavailable')
        return agent

    session.SessionManager._make_agent = make_agent


if __name__ == '__main__':
    try:
        from hermes_cli import env_loader
        guard_environment_loading(env_loader)
        from tools import lazy_deps
        block_native_lazy_install(lazy_deps)
        from agent.secret_sources import bitwarden
        block_native_bws_install(bitwarden)
        configure()
        if os.name == 'nt':
            sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
            from worker_process_guard import JobProcess
            from tools.environments import local as local_env
            configure_bash_probe(local_env, JobProcess)
    except Exception:
        print('CONSOLE_COMPACT_PROFILE_UNAVAILABLE', file=sys.stderr, flush=True)
        raise SystemExit(1)
    sys.argv = ['hermes', 'acp']
    from hermes_cli.main import main
    try:
        from tools import approval
        enforce_approval_policy(approval)
        from tools.process_registry import process_registry
        block_process_stdin(process_registry)
        from acp.schema import SetSessionModelResponse
        from acp_adapter import session, server
        from hermes_cli import runtime_provider
        from hermes_cli.config import load_config, is_provider_enabled
        from hermes_cli.models import normalize_provider, parse_model_input
        from hermes_cli.model_normalize import normalize_model_for_provider
        from hermes_cli.providers import custom_provider_aliases
        from hermes_route_guard import install
        install(session, server, runtime_provider, SetSessionModelResponse, load_config,
                normalize_provider, normalize_model_for_provider, custom_provider_aliases,
                is_provider_enabled, parse_model_input)
    except Exception:
        print('CONSOLE_COMPACT_PROFILE_UNAVAILABLE', file=sys.stderr, flush=True)
        raise SystemExit(1)
    main()
