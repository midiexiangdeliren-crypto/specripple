"""Bundled demo project runner (cold-start experience)."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import typer

from .detect import SEVERITIES, detect
from .impact import compute_impact
from .index_build import build_index, write_index
from .repo import load_entries
from .verify import run_verify

DEMO_DIR = Path(__file__).parent / "demo_project"


def prepare_demo_temp() -> Path:
    """Copy the bundled demo project into a fresh temp directory."""
    target = Path(tempfile.mkdtemp(prefix="specripple-demo-")) / "demo-project"
    shutil.copytree(DEMO_DIR, target)
    return target


def run_demo(project_root: Path) -> None:
    """Run index/impact/detect/verify against a demo project copy."""
    typer.secho(f"[demo] project at {project_root.as_posix()}", fg=typer.colors.CYAN)

    idx = build_index(load_entries(project_root))
    write_index(idx, project_root)
    typer.secho(f"[index] {len(idx['entries'])} entries indexed", fg=typer.colors.GREEN)

    result = compute_impact(load_entries(project_root), "REQ-001")
    typer.secho(f"[impact REQ-001] {len(result['impacts'])} artifact(s) affected:", fg=typer.colors.GREEN)
    for node in result["impacts"]:
        segments = [node["path"][0]]
        for edge, nxt in zip(node["edges"], node["path"][1:]):
            segments.append(f"--{edge}--> {nxt}")
        typer.echo(f"  [{node['id']}] depth {node['depth']} via " + " ".join(segments))

    findings = detect(load_entries(project_root), project_root)
    counts = {severity: 0 for severity in SEVERITIES}
    for finding in findings:
        counts[finding["severity"]] += 1
    typer.secho(
        f"[detect] {len(findings)} finding(s) "
        f"(CRITICAL {counts['CRITICAL']}, HIGH {counts['HIGH']}, MEDIUM {counts['MEDIUM']}, LOW {counts['LOW']})",
        fg=typer.colors.YELLOW if findings else typer.colors.GREEN,
    )
    for finding in findings:
        typer.echo(f"  [{finding['severity']} {finding['rule']}] {finding['message']}")

    report = run_verify(project_root)
    for group, items in report["groups"].items():
        for item in items:
            ok = item["status"] == "pass"
            typer.secho(
                f"[verify {'PASS' if ok else 'FAIL'}] {group} #{item['index'] + 1} "
                f"{item['checker']} {item['file']}",
                fg=typer.colors.GREEN if ok else typer.colors.RED,
            )
    summary = report["summary"]
    if summary["failed"]:
        typer.secho(f"[verify] FAIL ({summary['failed']} of {summary['total']} failed)", fg=typer.colors.RED)
    else:
        typer.secho(f"[verify] PASS ({summary['total']} assertions)", fg=typer.colors.GREEN)
    typer.secho("[demo] done - re-run any command with --root pointing at the path above", fg=typer.colors.CYAN)
