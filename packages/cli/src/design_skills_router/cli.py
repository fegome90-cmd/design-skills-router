"""Typed commands for the portable runner; JSON is the default interface."""

from enum import Enum
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

app = typer.Typer(
    name="design-skills-router",
    help="Inspect and maintain a portable design ledger. Results are JSON by default.",
    no_args_is_help=True,
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
)
_RUNNER = Path(__file__).resolve().parent / "_portable/skills/design-tree/scripts/runner.py"
Payload = Annotated[Path, typer.Option("--file", help="JSON input file.")]
Bundle = Annotated[Path, typer.Option("--bundle", help="Path to the portable bundle directory.")]
Destination = Annotated[Path, typer.Option("--output", help="Destination outside the plugin.")]
Node = Annotated[str, typer.Argument(help="Decision node ID.")]
Phase = Annotated[str, typer.Argument(help="Phase ID.")]
Reason = Annotated[str, typer.Option("--reason", help="Reason to record in the ledger.")]


class Mode(str, Enum):
    design = "design"
    audit = "audit"


class Level(str, Enum):
    manual = "manual"
    guided = "guided"
    phase_auto = "phase_auto"


@app.callback()
def options(
    ctx: typer.Context,
    state: Annotated[Path | None, typer.Option(help="Ledger path. Set before the command.")] = None,
) -> None:
    ctx.obj = state


def _echo_json(payload: bytes, *, err: bool = False) -> None:
    try:
        typer.get_binary_stream("stderr" if err else "stdout")
    except RuntimeError:
        # Embedded callers may redirect a standard stream to a text-only writer.
        typer.echo(payload.decode("utf-8"), err=err, nl=False)
    else:
        typer.echo(payload, err=err, nl=False)


def _safe_console_value(value: object, encoding: str) -> str:
    escaped: list[str] = []
    for character in str(value):
        if not character.isprintable():
            escaped.append(ascii(character)[1:-1])
            continue
        try:
            character.encode(encoding)
        except UnicodeEncodeError:
            escaped.append(ascii(character)[1:-1])
        else:
            escaped.append(character)
    return "".join(escaped)


def _status_table(stdout: bytes) -> None:
    try:
        status = json.loads(stdout)
    except (json.JSONDecodeError, UnicodeDecodeError):
        status = None
    if not isinstance(status, dict):
        _echo_json(b'{"status":"BLOCKED","error":"INVALID_STATUS_OUTPUT"}\n', err=True)
        raise typer.Exit(1)
    console = Console(
        force_terminal=False if not sys.stdout.isatty() or os.getenv("CI") else None,
        color_system=None if os.getenv("NO_COLOR") else "auto",
    )
    table = Table(title="Ledger status", expand=True, box=None)
    table.add_column("Field", style="bold")
    table.add_column("Value", overflow="fold")
    for key, label in (
        ("project_id", "Project"),
        ("revision", "Revision"),
        ("active_phase_id", "Active phase"),
        ("assistance_level", "Assistance"),
    ):
        if key in status:
            # Escape controls and characters the output stream cannot encode before rendering.
            value = _safe_console_value(status[key], console.encoding)
            table.add_row(label, Text(value))
    console.print(table)


def _run(
    ctx: typer.Context, command: str, *positional: str, pretty: bool = False,
    nodes: list[str] | None = None, **options: str | Path | Enum | bool | None,
) -> None:
    argv = [f"--state={ctx.obj}"] if ctx.obj is not None else []
    argv.append(command)
    for name, value in options.items():
        flag = "--" + name.replace("_", "-")
        if value is True:
            argv.append(flag)
        elif value is not None and value is not False:
            # Preserve dash-prefixed values when passing through the legacy parser.
            argv.append(f"{flag}={value.value if isinstance(value, Enum) else value}")
    if nodes:
        if any(node.startswith("-") for node in nodes):
            raise typer.BadParameter("Node IDs must not start with '-'.", param_hint="--nodes")
        argv.extend(["--nodes", *nodes])
    if positional:
        argv.extend(["--", *positional])

    # Execute the bundled sibling scripts without consulting PYTHONPATH or site packages.
    # Do not use -I: the portable scripts intentionally import their siblings.
    try:
        result = subprocess.run(
            [sys.executable, "-ESB", "-X", "utf8", str(_RUNNER), *argv],
            stdin=subprocess.DEVNULL, capture_output=True, check=False,
        )
    except KeyboardInterrupt:
        raise typer.Exit(130) from None
    except OSError:
        _echo_json(b'{"status":"BLOCKED","error":"PORTABLE_RUNNER_LAUNCH_FAILED"}\n', err=True)
        raise typer.Exit(1) from None
    if result.stderr:
        _echo_json(result.stderr, err=True)
    if result.stdout:
        if pretty and result.returncode == 0:
            _status_table(result.stdout)
        else:
            _echo_json(result.stdout)
    if result.returncode:
        code = result.returncode
        raise typer.Exit(code if code > 0 else 128 - code)


@app.command()
def init(
    ctx: typer.Context,
    project_id: Annotated[str, typer.Option(help="Identifier for the new project.")],
    scope: Annotated[str, typer.Option(help="Authorized project scope.")],
    mode: Annotated[Mode, typer.Option(help="Design or read-only audit proposals.")] = Mode.design,
    medium: Annotated[str, typer.Option(help="Project medium.")] = "web",
    context_pilot: Annotated[bool, typer.Option("--context-pilot", help="Enable the G5 context audit pilot.")] = False,
) -> None:
    """Create a new ledger. Does not approve or publish anything."""
    _run(ctx, "init", project_id=project_id, scope=scope, mode=mode, medium=medium, context_pilot=context_pilot)


@app.command()
def context_next(ctx: typer.Context) -> None:
    """Show pending nodes in the current project and phase."""
    _run(ctx, "context-next")


@app.command()
def context_open(ctx: typer.Context, node_id: Node) -> None:
    """Prepare the required source sections for the G5 pilot node."""
    _run(ctx, "context-open", node_id)


@app.command()
def context_search(ctx: typer.Context, node_id: Node, query: Annotated[str, typer.Option()]) -> None:
    """Search optional sections in the current G5 node."""
    _run(ctx, "context-search", node_id, query=query)


@app.command()
def mcp(ctx: typer.Context) -> None:
    """Serve the local G5 context tools over MCP stdio."""
    if ctx.obj is None:
        raise typer.BadParameter("Pass --state before mcp.", param_hint="--state")
    executable = _RUNNER.with_name("mcp_server.py")
    try:
        result = subprocess.run([sys.executable, "-EB", "-X", "utf8", str(executable),
                                 f"--state={ctx.obj}"], check=False)
    except KeyboardInterrupt:
        raise typer.Exit(130) from None
    except OSError:
        _echo_json(b'{"status":"BLOCKED","error":"MCP_SERVER_LAUNCH_FAILED"}\n', err=True)
        raise typer.Exit(1) from None
    if result.returncode:
        raise typer.Exit(result.returncode if result.returncode > 0 else 128 - result.returncode)


@app.command()
def status(
    ctx: typer.Context,
    pretty: Annotated[bool, typer.Option("--pretty", help="Show a short table instead of full JSON.")] = False,
) -> None:
    """Read the current ledger without changing it."""
    _run(ctx, "status", pretty=pretty)


@app.command()
def verify_package(ctx: typer.Context) -> None:
    """Verify the pinned design-tree baseline."""
    _run(ctx, "verify-package")


@app.command()
def phase_template(ctx: typer.Context) -> None:
    """Print the default phase map and its receipt hash."""
    _run(ctx, "phase-template")


@app.command()
def upgrade_state(
    ctx: typer.Context, bundle: Bundle, output: Destination | None = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Inspect without writing a bundle.")] = False,
) -> None:
    """Upgrade an older bundle to a new destination."""
    _run(ctx, "upgrade-state", bundle=bundle, output=output, dry_run=dry_run)


@app.command()
def configure(
    ctx: typer.Context,
    file: Annotated[Path, typer.Option(help="JSON object containing phase_map and receipt.")],
) -> None:
    """Record a confirmed phase map and its receipt."""
    _run(ctx, "configure", file=file)


@app.command()
def structure_set(ctx: typer.Context, file: Payload) -> None:
    """Confirm a set of decision nodes with a receipt."""
    _run(ctx, "structure-set", file=file)


@app.command()
def grant(ctx: typer.Context, file: Payload) -> None:
    """Record explicit authorization for a phase."""
    _run(ctx, "grant", file=file)


@app.command()
def grant_packet(ctx: typer.Context, file: Payload) -> None:
    """Calculate the hash of a delegation before recording it."""
    _run(ctx, "grant-packet", file=file)


@app.command()
def structure_manifest(
    ctx: typer.Context,
    nodes: Annotated[list[str] | None, typer.Option("--nodes", help="Repeat for each node; defaults to ALL.")] = None,
) -> None:
    """Print the selected decision nodes and their receipt hash."""
    _run(ctx, "structure-manifest", nodes=nodes)


@app.command()
def grant_template(
    ctx: typer.Context, phase_id: Phase,
    level: Annotated[Level, typer.Option(help="Requested assistance level.")] = Level.manual,
) -> None:
    """Prepare a delegation template. Does not authorize it."""
    _run(ctx, "grant-template", phase_id, level=level)


@app.command()
def delegate(ctx: typer.Context, node_id: Node) -> None:
    """Record a delegated decision under an existing authorization."""
    _run(ctx, "delegate", node_id)


@app.command()
def phase_prepare(ctx: typer.Context, phase_id: Phase, file: Payload) -> None:
    """Prepare a phase packet for human review."""
    _run(ctx, "phase-prepare", phase_id, file=file)


@app.command()
def phase_accept(ctx: typer.Context, phase_id: Phase, file: Payload) -> None:
    """Record human acceptance of a prepared phase packet."""
    _run(ctx, "phase-accept", phase_id, file=file)


@app.command()
def phase_reopen(ctx: typer.Context, phase_id: Phase, reason: Reason, file: Payload) -> None:
    """Reopen an accepted phase using the dedicated receipt."""
    _run(ctx, "phase-reopen", phase_id, reason=reason, file=file)


@app.command()
def revoke(ctx: typer.Context, reason: Reason) -> None:
    """Revoke the active delegation and return to manual assistance."""
    _run(ctx, "revoke", reason=reason)


@app.command()
def fact(ctx: typer.Context, fact_id: Annotated[str, typer.Argument(help="Fact ID.")], file: Payload) -> None:
    """Record a fact and invalidate affected records."""
    _run(ctx, "fact", fact_id, file=file)


@app.command()
def resume(ctx: typer.Context, bundle: Bundle) -> None:
    """Resume a bundle in a new ledger in manual mode."""
    _run(ctx, "resume", bundle=bundle)


@app.command()
def node(ctx: typer.Context, node_id: Node) -> None:
    """Read the decision packet for a node."""
    _run(ctx, "node", node_id)


@app.command()
def source(
    ctx: typer.Context,
    skill: Annotated[str, typer.Option(help="Inventory skill ID.")],
    file: Annotated[str, typer.Option(help="Local source file.")],
    commit: Annotated[str, typer.Option(help="Pinned source commit.")],
    git_blob: Annotated[str, typer.Option(help="Pinned Git blob hash.")],
    source_ref: Annotated[str, typer.Option(help="Reference identifying the source.")],
) -> None:
    """Register pinned local source evidence. Does not invoke the skill."""
    _run(ctx, "source", skill=skill, file=file, commit=commit, git_blob=git_blob, source_ref=source_ref)


@app.command()
def structure(ctx: typer.Context, node_id: Node, file: Payload) -> None:
    """Confirm a node structure with a receipt."""
    _run(ctx, "structure", node_id, file=file)


@app.command()
def propose(ctx: typer.Context, node_id: Node, file: Payload) -> None:
    """Record a proposed decision for human review."""
    _run(ctx, "propose", node_id, file=file)


@app.command()
def confirm(ctx: typer.Context, node_id: Node, file: Payload) -> None:
    """Record the human receipt for a proposed decision."""
    _run(ctx, "confirm", node_id, file=file)


@app.command()
def invalidate(ctx: typer.Context, node_id: Node, reason: Reason) -> None:
    """Invalidate a decision and dependent records."""
    _run(ctx, "invalidate", node_id, reason=reason)


@app.command()
def inventory(
    ctx: typer.Context,
    file: Annotated[Path | None, typer.Option(help=(
        "JSON array with one entry per skill. Each entry requires "
        "skill_id, disposition, reason and evidence_refs."
    ))] = None,
) -> None:
    """List the skill catalog or submit a disposition proposal with --file."""
    _run(ctx, "inventory", file=file)


@app.command()
def confirm_inventory(ctx: typer.Context, file: Payload) -> None:
    """Record human confirmation of inventory dispositions."""
    _run(ctx, "confirm-inventory", file=file)


@app.command()
def export(ctx: typer.Context, output: Destination) -> None:
    """Export the ledger and evidence to a new bundle."""
    _run(ctx, "export", output=output)
