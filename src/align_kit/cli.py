"""align-kit command line interface."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from .detect import SEVERITIES
from .detect import detect as run_detect
from .demo import prepare_demo_temp, run_demo
from .impact import compute_impact
from .index_build import build_index, write_index
from .init_host import run_init
from .repo import load_entries
from .verify import run_verify

app = typer.Typer(
    add_completion=False,
    help="align-kit: change-driven multi-artifact alignment (deterministic core).",
)


def _fail(message: str) -> None:
    typer.secho(f"error: {message}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=2)


@app.command()
def index(
    root: Path = typer.Option(Path("."), "--root", help="Project root containing artifacts/."),
    json_out: bool = typer.Option(False, "--json", help="Print the index JSON instead of a summary."),
) -> None:
    """Build and write index.json (rebuildable derived artifact)."""
    try:
        idx = build_index(load_entries(root))
    except ValueError as exc:
        _fail(str(exc))
        return
    out = write_index(idx, root)
    if json_out:
        typer.echo(json.dumps(idx, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        typer.echo(f"wrote {out.as_posix()} ({len(idx['entries'])} entries)")


@app.command()
def impact(
    entry_id: str = typer.Argument(..., help="Root artifact id, e.g. REQ-001."),
    root: Path = typer.Option(Path("."), "--root", help="Project root containing artifacts/."),
    json_out: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Compute the change impact closure of one artifact."""
    try:
        result = compute_impact(load_entries(root), entry_id)
    except KeyError as exc:
        _fail(str(exc.args[0]) if exc.args else str(exc))
        return
    except ValueError as exc:
        _fail(str(exc))
        return
    if json_out:
        typer.echo(json.dumps(result, ensure_ascii=False, indent=2))
        return
    typer.echo(
        f"impact of {result['root']}: {len(result['impacts'])} artifact(s), "
        f"{len(result['unresolved'])} unresolved"
    )
    for node in result["impacts"]:
        segments = [node["path"][0]]
        for edge, nxt in zip(node["edges"], node["path"][1:]):
            segments.append(f"--{edge}--> {nxt}")
        typer.echo(f"  [{node['id']}] depth {node['depth']} via " + " ".join(segments))
    for ref in result["unresolved"]:
        typer.secho(f"  [unresolved] {ref}", fg=typer.colors.YELLOW)


SEVERITY_COLORS = {
    "CRITICAL": typer.colors.RED,
    "HIGH": typer.colors.YELLOW,
    "MEDIUM": typer.colors.CYAN,
    "LOW": typer.colors.WHITE,
}


@app.command()
def detect(
    root: Path = typer.Option(Path("."), "--root", help="Project root containing artifacts/."),
    json_out: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Run the zero-token rule layer over the artifact repository."""
    try:
        findings = run_detect(load_entries(root), root)
    except ValueError as exc:
        _fail(str(exc))
        return
    counts = {severity: 0 for severity in SEVERITIES}
    for finding in findings:
        counts[finding["severity"]] += 1
    if json_out:
        payload = {"findings": findings, "summary": {"total": len(findings), "counts": counts}}
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    typer.echo(
        f"detect: {len(findings)} finding(s) "
        f"(CRITICAL {counts['CRITICAL']}, HIGH {counts['HIGH']}, MEDIUM {counts['MEDIUM']}, LOW {counts['LOW']})"
    )
    for finding in findings:
        typer.secho(
            f"  [{finding['severity']} {finding['rule']}] {finding['message']}",
            fg=SEVERITY_COLORS[finding["severity"]],
        )


@app.command()
def verify(
    root: Path = typer.Option(Path("."), "--root", help="Project root containing assertions.yaml."),
    json_out: bool = typer.Option(False, "--json", help="Print machine-readable JSON."),
) -> None:
    """Run assertions.yaml (fail_to_pass / pass_to_pass) against the project."""
    try:
        report = run_verify(root)
    except ValueError as exc:
        _fail(str(exc))
        return
    if json_out:
        typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
        return
    for group, items in report["groups"].items():
        for item in items:
            mark = "PASS" if item["status"] == "pass" else "FAIL"
            color = typer.colors.GREEN if item["status"] == "pass" else typer.colors.RED
            suffix = f" ({item['detail']})" if item["detail"] else ""
            typer.secho(
                f"  [{mark}] {group} #{item['index'] + 1} {item['checker']} {item['file']}{suffix}",
                fg=color,
            )
    summary = report["summary"]
    if summary["failed"]:
        typer.secho(f"verify: FAIL ({summary['failed']} of {summary['total']} failed)", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    typer.secho(f"verify: PASS ({summary['total']} assertions)", fg=typer.colors.GREEN)


@app.command()
def demo() -> None:
    """Copy the bundled demo project to a temp dir and run index/impact/detect/verify."""
    run_demo(prepare_demo_temp())


@app.command()
def init(
    host: str = typer.Option(..., "--host", help="Target host: codex or claude."),
    root: Path = typer.Option(Path("."), "--root", help="Project root to set up."),
    remove: bool = typer.Option(False, "--remove", help="Remove align-kit managed files."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print actions without writing."),
) -> None:
    """Install (or remove) align-kit host integration files."""
    try:
        actions = run_init(root, host, remove=remove, dry_run=dry_run)
    except ValueError as exc:
        _fail(str(exc))
        return
    prefix = "[dry-run] " if dry_run else ""
    for action in actions:
        typer.echo(f"{prefix}{action}")
    tag = " (dry-run)" if dry_run else ""
    typer.secho(f"init{tag} done: {len(actions)} action(s)", fg=typer.colors.GREEN)
