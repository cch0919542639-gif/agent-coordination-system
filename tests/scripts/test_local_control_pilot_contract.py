from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_l1_is_best_effort_not_an_enforced_isolation_claim() -> None:
    architecture = (ROOT / "docs/architecture/controlled-orchestration-architecture.md").read_text(encoding="utf-8")
    protocol = (ROOT / "docs/operations/phase14.5-six-agent-pilot-protocol.md").read_text(encoding="utf-8")
    card = (ROOT / "coordination/task-board/blocked/2026-09-03_phase14.5-six-agent-pilot-08_supervised-acceptance-pilot.md").read_text(encoding="utf-8")
    task_map = (ROOT / "docs/operations/phase14.5-controlled-orchestration-task-map.md").read_text(encoding="utf-8")
    for text in (architecture, protocol, card):
        assert "L1" in text and "best_effort" in text
        assert "not a security sandbox" in text or "not a sandbox" in text
    assert "It does not claim to protect against\nmalicious code" in architecture
    assert "not evidence of enforced restricted\nwrites" in protocol
    assert "no credentials, merge,\npush, destructive cleanup" in architecture
    for text in (architecture, protocol, card, task_map):
        assert "phase14.5-local-control-adapter-12" in text
        assert "L2-only" in text or "L2-only:" in text
    assert "cannot enable or authorize\nan L1 launch" in architecture
    assert "cannot enable a launch" in protocol
    assert "cannot launch L1 workers" in card
