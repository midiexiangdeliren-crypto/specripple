"""align-kit command line interface."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from .impact import compute_impact
from .index_build import build_index, write_index
from .repo import load_entries

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
