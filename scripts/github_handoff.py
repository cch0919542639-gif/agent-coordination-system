"""Explicit Git handoff commands and finite foreground watch; no provider activation."""
import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from coordination_runtime.github_handoff import HandoffService, HandoffError, bounded, canonical, decoded


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('init', 'sync', 'summary'): commands.add_parser(name)
    dispatch = commands.add_parser('dispatch')
    for name in ('task-id', 'machine-id', 'expected-card-sha256', 'expected-revision', 'expected-queue-head'):
        dispatch.add_argument('--' + name, required=True)
    dispatch.add_argument('--execute', action='store_true')
    receive = commands.add_parser('receive'); receive.add_argument('--execute', action='store_true')
    watch = commands.add_parser('watch'); watch.add_argument('--execute', action='store_true')
    watch.add_argument('--cycles', type=int, default=30); watch.add_argument('--interval', type=int, default=60)
    args = vars(parser.parse_args(argv)); command = args.pop('command'); path = args.pop('config')
    try:
        config = decoded(bounded(canonical(path)))
        service = HandoffService(path, config['repository'], config['project_id'])
        if command == 'init': result = service.initialize()
        elif command == 'summary': result = service.summary()
        elif command == 'sync': result = service.sync_once()
        elif command == 'dispatch': result = service.dispatch(**args)
        elif command == 'receive': result = service.receive_once(**args)
        else:
            cycles, interval = args['cycles'], args['interval']
            if not 1 <= cycles <= 120 or not 60 <= interval <= 3600 or (cycles-1)*interval > 7200:
                raise HandoffError('INVALID_WATCH_BUDGET')
            service.deadline = time.monotonic() + 7200
            result = service.summary()
            for step in range(cycles):
                if time.monotonic() >= service.deadline: break
                try:
                    result = service.receive_once(execute=args['execute']) if config['mode'] == 'worker' else service.sync_once()
                except HandoffError:
                    result = service.summary()
                print(json.dumps(result, sort_keys=True), flush=True)
                if step + 1 < cycles:
                    remaining = service.deadline - time.monotonic()
                    if remaining <= 0: break
                    time.sleep(min(interval, remaining))
        if command != 'watch': print(json.dumps(result, sort_keys=True), flush=True)
        return 0
    except KeyboardInterrupt:
        return 130
    except (HandoffError, OSError, KeyError, TypeError):
        print('Handoff refused; check local configuration, binding and cached error category.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
