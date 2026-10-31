# Synthetic NAS and adapter pilot

Date: 2026-11-01. Scope: a dedicated AgentMemory 0.4.3 NAS pilot, one
fictional Git source and the local Qwen2.5-3B model. No actual candidate source
or private transcript was submitted to a model.

- The dedicated core passed health, unauthenticated 401 and container restart
  checks. Existing running-container IDs were unchanged in the installation
  check. The core listens on loopback; host networking is not network isolation.
- One NAS-local synthetic backup was restored to a separate volume and core.
  The restored core and the restarted source each returned the synthetic marker.
  Restore resources were removed. An earlier restore failed and its backup is
  not claimed as valid. A NAS-local copy does not protect against NAS loss.
- An actual ACS adapter sent one fictional source through SSH to the NAS core.
  Agent-scoped strategy readback, exact source-marker verification, query,
  replay without resubmission, adapter withdrawal and stale-batch refusal passed.
  This does not prove deletion of upstream L1/L2/L3 memory.
- Two SSH processes on one Windows computer reached the core; requests without
  a key and with an invalid key received 401. This is not a two-computer test.
  The focused adapter suite passed 54 tests using synthetic fixtures.
- The local on-demand model and SSH reverse tunnel passed model health from the
  NAS. Abrupt parent termination stopped both child processes while NAS core
  health remained good. The helper is local to the operator's machine; no
  automatic startup was enabled.

The synthetic NAS scope uses an operator-created test administrator;
it is not an approved real-data identity. The synthetic department and upstream
memories remain on the dedicated pilot. The NAS core may retry queued work when
the local model or tunnel is offline; after reconnecting the model the observed
queue drained, without claiming every historical failure's cause.

Not yet verified or approved: independent review of source candidates,
processing real summaries, off-device backup and restore, two physical clients,
upstream data deletion, endurance or full production deployment. The real
candidate batch remains `pending-human-review`. No raw logs, credentials, local
network identifiers or private configuration are published here.
