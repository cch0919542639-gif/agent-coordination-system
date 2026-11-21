"""Verify console Hermes model switches without exposing routes or credentials."""
import contextvars
from urllib.parse import urlsplit


def project_config(config):
    """Snapshot routing metadata without retaining credentials or headers."""
    if not isinstance(config, dict):
        return None
    model = config.get('model')
    def scalar(value):
        return value is None or isinstance(value, (str, bool, int))
    if isinstance(model, dict):
        model = {k: model.get(k) for k in ('provider', 'default', 'base_url')}
        if not all(scalar(v) for v in model.values()):
            return None
    elif not isinstance(model, str):
        return None
    providers = config.get('providers', {})
    legacy = config.get('custom_providers', [])
    if not isinstance(providers, dict) or (legacy is not None and not isinstance(legacy, list)):
        return None
    keys = ('name', 'enabled', 'api', 'url', 'base_url', 'provider_key', 'key_env')
    def project(entry):
        if not isinstance(entry, dict):
            return None
        values = {k: entry[k] for k in keys if k in entry}
        if not all(scalar(v) for v in values.values()):
            raise ValueError('invalid route metadata')
        return values
    try:
        if not all(isinstance(k, str) for k in providers):
            return None
        return {'model': model, 'providers': {k: project(v) for k, v in providers.items()},
                'custom_providers': [project(v) for v in legacy or []]}
    except ValueError:
        return None


def endpoint(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = urlsplit(value.strip())
        if (parsed.scheme.lower() not in ('http', 'https') or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment):
            return None
        return (parsed.scheme.lower(), parsed.hostname.lower(), parsed.port,
                parsed.path.rstrip('/') or '/')
    except ValueError:
        return None


def agent_signature(agent):
    provider = getattr(agent, 'provider', None)
    model = getattr(agent, 'model', None)
    base = endpoint(getattr(agent, 'base_url', None))
    client = getattr(agent, 'client', None)
    client_base = getattr(client, 'base_url', None)
    if (not isinstance(provider, str) or not provider or not isinstance(model, str) or not model
            or base is None or client_base is None or endpoint(str(client_base)) != base
            or getattr(agent, '_fallback_chain', None)):
        return None
    return provider, model, base


def custom_records(config, aliases, enabled):
    """Project only names, enabled flags and URLs."""
    records = []
    providers = config.get('providers', {})
    if not isinstance(providers, dict):
        return None
    for key, entry in providers.items():
        if isinstance(entry, dict) and enabled(entry):
            url = endpoint(entry.get('api') or entry.get('url') or entry.get('base_url') or '')
            records.append((aliases(str(entry.get('name') or key), str(key)), url))
    legacy = config.get('custom_providers', [])
    if legacy is not None and not isinstance(legacy, list):
        return None
    for entry in legacy or []:
        if isinstance(entry, dict) and enabled(entry):
            url = endpoint(entry.get('base_url') or entry.get('url') or entry.get('api') or '')
            records.append((aliases(str(entry.get('name') or ''), str(entry.get('provider_key') or '')), url))
    return records


def custom_endpoint(config, requested, aliases, enabled):
    records = custom_records(config, aliases, enabled)
    if records is None:
        return None
    matches = [url for names, url in records if requested in names]
    if len(matches) != 1 or matches[0] is None:
        return None
    target = matches[0]
    return target if sum(url == target for _, url in records) == 1 else None


def unambiguous_endpoint(config, target, aliases, enabled):
    records = custom_records(config, aliases, enabled)
    return records is not None and target is not None and sum(url == target for _, url in records) <= 1


def verified_candidate(requested, model, candidate, resolved, config, normalize_provider,
                       normalize_model, aliases, enabled, previous_base=None):
    if not isinstance(resolved, dict) or resolved.get('requested_provider') != requested:
        return False
    signature = agent_signature(candidate)
    if signature is None:
        return False
    provider = signature[0]
    resolved_provider = str(resolved.get('provider') or '')
    if not provider or normalize_provider(provider) != normalize_provider(resolved_provider):
        return False
    if requested.startswith('custom:'):
        expected_provider = 'custom'
        expected_endpoint = custom_endpoint(config, requested, aliases, enabled)
    elif requested == 'custom':
        expected_provider = 'custom'
        model_config = config.get('model')
        expected_endpoint = endpoint(model_config.get('base_url')) if isinstance(model_config, dict) else None
        if not unambiguous_endpoint(config, expected_endpoint, aliases, enabled):
            return False
    else:
        expected_provider = normalize_provider(requested)
        expected_endpoint = endpoint(resolved.get('base_url'))
    actual_endpoint = endpoint(getattr(candidate, 'base_url', None))
    resolved_endpoint = endpoint(resolved.get('base_url'))
    if (normalize_provider(provider) != expected_provider or expected_endpoint is None
            or actual_endpoint != expected_endpoint or resolved_endpoint != expected_endpoint
            or (previous_base and endpoint(previous_base) != expected_endpoint)):
        return False
    return getattr(candidate, 'model', None) == normalize_model(model, provider)


def verified_initial(candidate, resolved, config, normalize_provider, normalize_model, aliases, enabled):
    if not isinstance(resolved, dict):
        return False
    model_config = config.get('model')
    if isinstance(model_config, dict):
        expected_model = model_config.get('default')
        requested = str(model_config.get('provider') or '').strip().lower()
        configured_endpoint = model_config.get('base_url')
    else:
        expected_model = model_config
        requested = ''
        configured_endpoint = None
    signature = agent_signature(candidate)
    if signature is None:
        return False
    actual_provider = signature[0]
    resolved_provider = str(resolved.get('provider') or '')
    actual_endpoint = endpoint(getattr(candidate, 'base_url', None))
    resolved_endpoint = endpoint(resolved.get('base_url'))
    if (not isinstance(expected_model, str) or not expected_model or not actual_provider
            or not resolved_provider or actual_endpoint is None or actual_endpoint != resolved_endpoint
            or normalize_provider(actual_provider) != normalize_provider(resolved_provider)):
        return False
    if requested and str(resolved.get('requested_provider') or '').strip().lower() != requested:
        return False
    if requested.startswith('custom:'):
        if normalize_provider(actual_provider) != 'custom' or custom_endpoint(config, requested, aliases, enabled) != actual_endpoint:
            return False
    elif configured_endpoint:
        if (endpoint(configured_endpoint) != actual_endpoint
                or not unambiguous_endpoint(config, actual_endpoint, aliases, enabled)):
            return False
        # Native Hermes may explicitly use its generic custom transport for
        # a configured endpoint. It must be displayed as custom, not as the
        # configured provider; other provider substitutions are rejected.
        if (requested and requested != 'auto'
                and normalize_provider(actual_provider) not in ('custom', normalize_provider(requested))):
            return False
    elif requested and requested != 'auto' and normalize_provider(actual_provider) != normalize_provider(requested):
        return False
    if not unambiguous_endpoint(config, actual_endpoint, aliases, enabled):
        return False
    return getattr(candidate, 'model', None) == normalize_model(expected_model, actual_provider)


def install(session_module, server_module, runtime_module, schema, load_config,
            normalize_provider, normalize_model, aliases, enabled, parse_model):
    selection = contextvars.ContextVar('console_hermes_selection', default=None)
    original_resolve = runtime_module.resolve_runtime_provider
    original_make = session_module.SessionManager._make_agent
    original_persist = session_module.SessionManager._persist
    original_switch = server_module.HermesACPAgent.set_session_model
    original_new = server_module.HermesACPAgent.new_session
    original_cmd_model = server_module.HermesACPAgent._cmd_model
    original_prompt = server_module.HermesACPAgent.prompt

    def persist(self, state):
        slot = selection.get()
        if slot is not None and slot.get('defer'):
            slot['pending_persist'] = (self, state)
            return None
        return original_persist(self, state)

    def resolve(*args, **kwargs):
        slot = selection.get()
        observed = slot is not None and not slot['seen'] and kwargs.get('requested') == slot['provider']
        if observed:
            slot['seen'] = True
        result = original_resolve(*args, **kwargs)
        if observed and isinstance(result, dict):
            slot['resolved'] = {k: result.get(k) for k in ('provider', 'base_url', 'requested_provider')}
        return result

    def make_agent(self, **kwargs):
        agent = original_make(self, **kwargs)
        slot = selection.get()
        if slot is not None:
            if slot['kind'] == 'initial':
                slot['verified'] = verified_initial(
                    agent, slot.get('resolved'), slot['config'], normalize_provider,
                    normalize_model, aliases, enabled)
            else:
                slot['verified'] = verified_candidate(
                    slot['provider'], slot['model'], agent, slot.get('resolved'), slot['config'],
                    normalize_provider, normalize_model, aliases, enabled, kwargs.get('base_url'))
            if not slot['verified']:
                raise RuntimeError('console route verification failed')
            slot['actual_provider'] = agent.provider
            slot['actual_model'] = agent.model
            slot['candidate'] = agent
        return agent

    async def new(self, cwd, mcp_servers=None, **kwargs):
        config = project_config(load_config())
        if config is None:
            raise RuntimeError('console route verification failed')
        model_config = config.get('model')
        provider = model_config.get('provider') if isinstance(model_config, dict) else None
        slot = {'kind': 'initial', 'provider': provider, 'config': config, 'seen': False, 'verified': False, 'defer': True}
        token = selection.set(slot)
        try:
            result = await original_new(self, cwd, mcp_servers, **kwargs)
            current = getattr(getattr(result, 'models', None), 'current_model_id', None)
            if not slot['seen'] or not slot['verified'] or not isinstance(current, str):
                raise RuntimeError('console route verification failed')
            parsed_provider, parsed_model = parse_model(current, slot['actual_provider'])
            if (normalize_provider(parsed_provider) != normalize_provider(slot['actual_provider'])
                    or normalize_model(parsed_model, slot['actual_provider']) != slot['actual_model']):
                raise RuntimeError('console route verification failed')
            if project_config(load_config()) != config:
                raise RuntimeError('console route verification failed')
            with self.session_manager._lock:
                state = self.session_manager._sessions.get(result.session_id)
            if state is None or state.agent is not slot['candidate']:
                raise RuntimeError('console route verification failed')
            state._console_route_snapshot = config
            state._console_verified_agent = state.agent
            state._console_route_signature = agent_signature(state.agent)
            if slot.get('pending_persist') != (self.session_manager, state):
                raise RuntimeError('console route verification failed')
            slot['defer'] = False
            original_persist(self.session_manager, state)
            result.field_meta = {**(result.field_meta or {}), 'consoleRouteVerified': True,
                                 'accountVerified': False, 'modelId': current}
            return result
        except BaseException:
            pending = slot.get('pending_persist')
            if pending and pending[0] is self.session_manager:
                state = pending[1]
                with self.session_manager._lock:
                    if self.session_manager._sessions.get(state.session_id) is state:
                        self.session_manager._sessions.pop(state.session_id)
            raise
        finally:
            slot['defer'] = False
            selection.reset(token)

    async def switch(self, model_id, session_id, **kwargs):
        with self.session_manager._lock:
            state = self.session_manager._sessions.get(session_id)
        if state is None:
            raise RuntimeError('console route verification failed')
        snapshot = getattr(state, '_console_route_snapshot', None)
        if (snapshot is None or getattr(state, '_console_verified_agent', None) is not state.agent
                or project_config(load_config()) != snapshot):
            raise RuntimeError('console route verification failed')
        previous_model, previous_agent = state.model, state.agent
        current_provider = getattr(state.agent, 'provider', None) or 'openrouter'
        requested, model = self._resolve_model_selection(model_id, current_provider)
        selected_provider, selected_model = parse_model(model_id, current_provider)
        if not isinstance(requested, str) or not isinstance(model, str) or not requested or not model:
            raise RuntimeError('console route verification failed')
        if (normalize_provider(selected_provider) != normalize_provider(requested)
                or normalize_model(selected_model, requested) != normalize_model(model, requested)):
            raise RuntimeError('console route verification failed')
        slot = {'kind': 'switch', 'provider': requested, 'model': model, 'config': snapshot,
                'seen': False, 'verified': False, 'defer': True}
        token = selection.set(slot)
        try:
            result = await original_switch(self, model_id, session_id, **kwargs)
            if (result is None or not slot['seen'] or not slot['verified']
                    or state.agent is not slot['candidate'] or project_config(load_config()) != snapshot
                    or slot.get('pending_persist') != (self.session_manager, state)):
                raise RuntimeError('console route verification failed')
            slot['defer'] = False
            original_persist(self.session_manager, state)
            state._console_verified_agent = state.agent
            state._console_route_signature = agent_signature(state.agent)
            return schema(field_meta={'consoleRouteVerified': True, 'accountVerified': False, 'modelId': model_id})
        except BaseException:
            state.model, state.agent = previous_model, previous_agent
            raise
        finally:
            slot['defer'] = False
            selection.reset(token)

    def cmd_model(self, args, state):
        if args.strip():
            return 'Use the console model selector to switch models.'
        return original_cmd_model(self, args, state)

    async def prompt(self, prompt, session_id, **kwargs):
        with self.session_manager._lock:
            state = self.session_manager._sessions.get(session_id)
        if (state is None or getattr(state, '_console_verified_agent', None) is not state.agent
                or not getattr(state, '_console_route_signature', None)
                or agent_signature(state.agent) != state._console_route_signature
                or project_config(load_config()) != getattr(state, '_console_route_snapshot', None)):
            raise RuntimeError('console route verification failed')
        return await original_prompt(self, prompt, session_id, **kwargs)

    runtime_module.resolve_runtime_provider = resolve
    session_module.SessionManager._make_agent = make_agent
    session_module.SessionManager._persist = persist
    server_module.HermesACPAgent.set_session_model = switch
    server_module.HermesACPAgent.new_session = new
    server_module.HermesACPAgent._cmd_model = cmd_model
    server_module.HermesACPAgent.prompt = prompt
