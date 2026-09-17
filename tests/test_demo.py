import shutil
from pathlib import Path

from specripple.demo import DEMO_DIR, run_demo


def test_demo_full_run(tmp_path, capsys):
    target = tmp_path / "demo-project"
    shutil.copytree(DEMO_DIR, target)
    run_demo(target)
    out = capsys.readouterr().out
    assert "[index] 10 entries indexed" in out
    assert "[impact REQ-001] 5 artifact(s) affected" in out
    assert "[detect] 2 finding(s)" in out
    assert "[CRITICAL D1]" in out
    assert "[HIGH D5]" in out
    assert "[verify] PASS (4 assertions)" in out
    assert (target / "index.json").exists()


def test_demo_impact_chain_depths(tmp_path, capsys):
    target = tmp_path / "demo-project"
    shutil.copytree(DEMO_DIR, target)
    run_demo(target)
    out = capsys.readouterr().out
    # REQ-001 -> REQ-002 (d1) -> REQ-004 (d2) -> TASK-003 (d3), plus TASK-001 (d1),
    # TASK-002 (d2): the REQ->REQ->TASK dependency chain the demo exists to show.
    assert "[TASK-003] depth 3" in out
    assert "[REQ-004] depth 2" in out
    assert "[TASK-001] depth 1" in out
