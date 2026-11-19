"""Telemetry-aware process wrapper for the design-tree CLI.

The plugin itself is network-free by contract (see
plugin/tests/test_portability.py). This wrapper observes the plugin at its
process boundary: it preserves stdout, stderr and the exit code byte-for-byte,
then emits only identifiers already present in the command or its JSON reply.

Usage:
    python3 -B telemetry/observe.py -- <runner.py arguments...>
    python3 -B telemetry/observe.py --runner path/to/runner.py -- node Q00
    python3 -B telemetry/observe.py --exec design-skills-router -- node Q00

Telemetry is OFF unless DESIGN_ROUTER_TELEMETRY=1 and
DESIGN_ROUTER_TELEMETRY_URL are present. Telemetry failures never change the
observed command's behavior.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from telemetry.client import client_from_env
from telemetry import contract

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNNER = ROOT / "plugin/skills/design-tree/scripts/runner.py"
MAX_NODE_PACKET_BYTES = 1024 * 1024


_SUBCOMMAND_VALUE_OPTIONS = (
    "--file",
    "--reason",
    "--output",
    "--bundle",
    "--project-id",
    "--scope",
    "--mode",
    "--medium",
    "--level",
)


def _matches_option(token: str, canonical: str) -> bool:
    """Match an argparse long option or unambiguous prefix (e.g. --st for --state)."""
    return token.startswith("--") and len(token) >= 3 and canonical.startswith(token)


def _matches_value_option(token: str, options: tuple[str, ...]) -> bool:
    if "=" in token or not token.startswith("--") or len(token) < 3:
        return False
    matches = [opt for opt in options if opt.startswith(token)]
    return len(matches) == 1


def _find_command_index(argv: list[str]) -> int | None:
    index = 0
    while index < len(argv):
        value = argv[index]
        if value == "--":
            return index + 1 if index + 1 < len(argv) else None
        if value == "-h" or _matches_option(value, "--help"):
            return None
        if _matches_option(value, "--state"):
            index += 2
            continue
        if "=" in value and _matches_option(value.split("=", 1)[0], "--state"):
            index += 1
            continue
        if value.startswith("-"):
            return None
        sub_i = index + 1
        while sub_i < len(argv):
            tok = argv[sub_i]
            if tok == "--":
                break
            if tok == "-h" or _matches_option(tok, "--help"):
                return None
            if _matches_value_option(tok, _SUBCOMMAND_VALUE_OPTIONS):
                sub_i += 2
                continue
            sub_i += 1
        return index
    return None


def command_of(argv: list[str]) -> str | None:
    index = _find_command_index(argv)
    return argv[index] if index is not None else None


def option_value(argv: list[str], name: str) -> str | None:
    cmd_index = _find_command_index(argv)
    start = cmd_index + 1 if cmd_index is not None else 0
    index = start
    while index < len(argv):
        value = argv[index]
        if value == "--":
            break
        if _matches_option(value, name) and index + 1 < len(argv):
            return argv[index + 1]
        if "=" in value:
            opt, opt_val = value.split("=", 1)
            if _matches_option(opt, name):
                return opt_val
        index += 1
    return None


def positional_after(argv: list[str], command: str) -> str | None:
    cmd_index = _find_command_index(argv)
    if cmd_index is not None and argv[cmd_index] == command:
        index = cmd_index + 1
    else:
        try:
            index = argv.index(command) + 1
        except ValueError:
            return None
    while index < len(argv):
        value = argv[index]
        if value == "--":
            return argv[index + 1] if index + 1 < len(argv) else None
        if value.startswith("-"):
            index += 2 if _matches_value_option(value, _SUBCOMMAND_VALUE_OPTIONS) else 1
            continue
        return value
    return None


def parse_json(raw: bytes) -> dict | None:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def observe(client, command: str | None, argv: list[str], stdout: bytes, returncode: int) -> None:
    if returncode != 0 or command is None:
        return
    evaluation_id = client.new_evaluation_id()
    client.emit("router.invoked", evaluation_id=evaluation_id, command=command)
    if command == "node":
        packet = parse_json(stdout)
        if not packet:
            return
        node_id = packet.get("node_id") or positional_after(argv, command)
        if isinstance(node_id, str):
            client.emit("decision.node_visited", evaluation_id=evaluation_id, node_id=node_id)
        # packet.skills is a candidate list for the node, not an algorithmic
        # selection. It must not be counted as skill.selected.
    elif command == "propose":
        payload_path = option_value(argv, "--file")
        if not payload_path:
            return
        try:
            payload = json.loads(Path(payload_path).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return
        if not isinstance(payload, dict):
            return
        node_id = positional_after(argv, command)
        branch = payload.get("selected")
        if isinstance(node_id, str) and isinstance(branch, str):
            # Only identifiers are emitted; summary, evidence and rationale stay local.
            client.emit(
                "decision.branch_selected",
                evaluation_id=evaluation_id,
                node_id=node_id,
                branch_id=branch,
            )


def _run_child(argv: list[str], inspect_node: bool) -> tuple[int, bytes]:
    if not inspect_node:
        completed = subprocess.run(argv, stdout=sys.stdout.buffer, stderr=sys.stderr.buffer, check=False)
        return completed.returncode, b""

    # stderr is inherited. Forward stdout as it arrives, retaining only a
    # complete, size-bounded node packet for inspection after successful exit.
    packet: bytearray | None = bytearray()
    with subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=sys.stderr.buffer, bufsize=0) as child:
        assert child.stdout is not None
        while chunk := child.stdout.read(64 * 1024):
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
            if packet is not None:
                if len(packet) + len(chunk) <= MAX_NODE_PACKET_BYTES:
                    packet.extend(chunk)
                else:
                    packet = None
        return child.wait(), bytes(packet) if packet is not None else b""


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    launcher: list[str] | None = None
    verbose = False
    while args and args[0] in ("--runner", "--exec", "--verbose"):
        option = args.pop(0)
        if option == "--verbose":
            verbose = True
            continue
        if launcher is not None or not args or args[0] == "--":
            print("choose one of --runner PATH or --exec PROGRAM", file=sys.stderr)
            return 2
        target = args.pop(0)
        if option == "--runner":
            if not Path(target).is_file():
                print(f"runner not found: {target}", file=sys.stderr)
                return 2
            launcher = [sys.executable, "-B", target]
        else:
            launcher = [target]
    if args and args[0] == "--":
        args = args[1:]
    if launcher is None:
        launcher = [sys.executable, "-B", str(DEFAULT_RUNNER)]

    client = None
    try:
        client = client_from_env()
    except Exception as error:
        # Invalid telemetry configuration must not prevent the observed command.
        if verbose:
            print(f"telemetry: configuration rejected ({type(error).__name__}); running without telemetry", file=sys.stderr)
    if client is None:
        from telemetry.client import Telemetry
        client = Telemetry(contract.DISABLED)
    command = command_of(args)
    try:
        returncode, output = _run_child([*launcher, *args], client.enabled and command == "node")
    except OSError as error:
        print(f"could not start runner: {error}", file=sys.stderr)
        return 2
    try:
        if client.enabled:
            observe(client, command, args, output, returncode)
        if not client.flush() and verbose:
            print("telemetry: event batch not delivered; see telemetry state directory", file=sys.stderr)
    except Exception as error:
        # Telemetry must never change stdout, stderr or the observed exit code.
        if verbose:
            print(f"telemetry: local failure ({type(error).__name__}); command unaffected", file=sys.stderr)
    return returncode


if __name__ == "__main__":
    code = main()
    if os.name == "posix" and code < 0:
        # SystemExit(-SIGTERM) would report a normal exit with status 241.
        # Deliver the same signal so both waitpid and shell callers see it.
        signum = -code
        if signum != signal.SIGKILL:
            signal.signal(signum, signal.SIG_DFL)
            signal.pthread_sigmask(signal.SIG_UNBLOCK, {signum})
        signal.raise_signal(signum)
    raise SystemExit(code)
