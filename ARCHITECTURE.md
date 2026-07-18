# Architecture

## Coordination Layers

```text
context kit -> phase plan -> task board -> worker delivery -> review evidence
                                      ^                 |
                                      |                 v
                             monitor / routing <- Git branch evidence
```

## Key Boundaries

- `coordination/`: task evidence, templates, reviews, and local ignored monitor
  state.
- `scripts/`: validator, task lifecycle helpers, monitor, router, and worker
  commands.
- `docs/operations/`: operating contracts and guides.
- `services/coordination_api/`: optional API evolution; not required for the
  same-machine local loop.

## Deep References

- `docs/operations/phase12-event-driven-orchestration-plan.md`
- `docs/operations/phase14-same-machine-worker-automation-plan.md`
- `docs/operations/project-repository-boundary.md`
