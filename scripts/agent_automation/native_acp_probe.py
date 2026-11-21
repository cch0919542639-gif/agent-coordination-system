"""Explicit live native ACP check; no custom model gateway or credential reader.

Run from the checkout with a new receipt path. This is a manual-mode diagnostic,
not an isolated unattended runner. Never run it as part of automatic tests.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from web.agent_control import AgentSession

MODEL = 'opencode/big-pickle'
MARKER = 'native-acp-ok'
PROMPT = (
    'This is a disposable native ACP integration check. In the current working '
    'directory only, use a local file or shell tool to create native-check.txt '
    'containing exactly native-acp-ok (an optional final newline is fine). '
    'Do not read other files, browse, call external tools/services, launch '
    'subagents, or change any settings. Then reply exactly native-acp-ok.'
)


def check(workspace, *, timeout=120):
    """One dispatched turn. Persist only fixed classifications and booleans."""
    result = dict(route='native_acp', model=MODEL, customGateway=False,
                  osIsolated=False, dispatchedTurns=0, outcome='startup_failed',
                  fileVerified=False, replyVerified=False, toolCompleted=False,
                  cleanupConfirmed=False)
    agent = AgentSession('opencode', workspace)
    deadline = time.monotonic() + timeout
    dispatched = False
    try:
        while time.monotonic() < deadline:
            state = agent.snapshot()
            if state['phase'] in ('failed', 'stopped') or state.get('error'):
                result['outcome'] = 'native_request_failed'
                break
            if state['phase'] == 'ready':
                if state.get('model') != MODEL:
                    result['outcome'] = 'native_model_mismatch'
                    break
                if not dispatched:
                    dispatched = True
                    result['dispatchedTurns'] = 1
                    agent.prompt(PROMPT)
                else:
                    marker = Path(workspace) / 'native-check.txt'
                    result['fileVerified'] = (marker.is_file() and not marker.is_symlink()
                                              and marker.stat().st_size <= 64
                                              and marker.read_bytes().strip() == MARKER.encode())
                    result['replyVerified'] = state.get('response', '').strip() == MARKER
                    result['toolCompleted'] = any(x.get('status') == 'completed'
                                                  for x in state.get('activity', []))
                    result['outcome'] = ('passed' if all(result[k] for k in
                                         ('fileVerified', 'replyVerified', 'toolCompleted'))
                                         else 'native_result_unconfirmed')
                    break
            time.sleep(.05)
        else:
            result['outcome'] = 'native_timeout'
    except Exception:
        # Native error details may contain credentials or private paths.
        result['outcome'] = 'native_check_failed'
    finally:
        agent.close()
        # AgentSession reports stopped only if its Job stop/cleanup succeeded.
        result['cleanupConfirmed'] = agent.snapshot()['phase'] == 'stopped'
        if not result['cleanupConfirmed']:
            result['outcome'] = 'cleanup_unconfirmed'
    return result


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: native_acp_probe.py NEW_RECEIPT.json')
    # Reserve the receipt before dispatch; never overwrite a previous attempt.
    with Path(sys.argv[1]).open('x', encoding='utf-8') as receipt:
        started = time.monotonic()
        result = dict(startedUtc=datetime.now(timezone.utc).isoformat())
        with tempfile.TemporaryDirectory(prefix='native-acp-check-') as workspace:
            result.update(check(workspace))
        result['elapsedSeconds'] = round(time.monotonic() - started, 3)
        json.dump(result, receipt, indent=2)
        receipt.write('\n')
    print(json.dumps(result))
    return 0 if result['outcome'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
