#!/usr/bin/env python3
"""Reject text I/O that depends on the platform's default encoding.

The check is static and uses only the standard library. It reports calls
that open or decode text without an explicit ``encoding`` argument, or with
``encoding=None``:

* ``open``, ``io.open``, ``os.fdopen`` and ``Path.open`` in text mode;
* ``Path.read_text`` and ``Path.write_text``;
* ``tempfile.TemporaryFile``, ``NamedTemporaryFile`` and
  ``SpooledTemporaryFile`` in text mode (their default mode is binary);
* ``fileinput.input`` and ``fileinput.FileInput`` in text mode;
* ``subprocess.run``, ``Popen``, ``call``, ``check_call`` and
  ``check_output`` with ``text`` or ``universal_newlines`` enabled.

A mode is binary only when it is a string literal that contains ``b``.
Any other mode, including a variable, is treated as text. ``mkstemp``,
``mkdtemp``, ``TemporaryDirectory`` and ``gettempdir`` do not open text
streams and are never reported.

By default the check reads the Python files tracked by Git, minus the
frozen paths listed in ``EXCLUDED``. Exit status: 0 when clean, 1 when a
violation is found, 2 on usage or parse errors.
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Frozen material whose bytes must not change. Each entry needs a reason.
EXCLUDED = {
    'decision-authoring/original/': 'Original histórico fijado por SHA256SUMS.txt.',
    'history/': 'Auditoría histórica v1.1 conservada con sus resultados originales.',
}

# Modules whose ``open`` is not a text-file API (or is handled separately).
NOT_PATH_OPEN = {
    'bz2', 'codecs', 'dbm', 'gzip', 'io', 'lzma', 'os', 'shelve', 'tarfile',
    'tempfile', 'wave', 'webbrowser', 'zipfile',
}
SUBPROCESS_CALLS = {'run', 'Popen', 'call', 'check_call', 'check_output'}
TEMPFILE_CALLS = {'TemporaryFile', 'NamedTemporaryFile', 'SpooledTemporaryFile'}

# name -> (index of mode, index of encoding, default mode is text)
# An index of None means the parameter is keyword-only.
OPEN_LIKE = {
    'open': (1, 3, True),
    'io.open': (1, 3, True),
    'os.fdopen': (1, 3, True),
    'Path.open': (0, 2, True),
    'tempfile.TemporaryFile': (0, 2, False),
    'tempfile.NamedTemporaryFile': (0, 2, False),
    'tempfile.SpooledTemporaryFile': (1, 3, False),
    'fileinput.input': (None, None, True),
    'fileinput.FileInput': (None, None, True),
}


class Visitor(ast.NodeVisitor):
    def __init__(self, path: str):
        self.path = path
        self.found: list[tuple[str, int, int, str]] = []
        self.modules: dict[str, str] = {}  # local alias -> module
        self.names: dict[str, str] = {}    # local name -> 'module.attr'

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.asname:
                self.modules[alias.asname] = alias.name
            else:  # ``import os.path`` binds ``os``
                top = alias.name.split('.')[0]
                self.modules[top] = top
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and node.level == 0:
            for alias in node.names:
                self.names[alias.asname or alias.name] = f'{node.module}.{alias.name}'
        self.generic_visit(node)

    def qualified(self, func: ast.expr) -> str | None:
        """Return a canonical name for the called function, if relevant."""
        if isinstance(func, ast.Name):
            if func.id in self.names:
                return self.names[func.id]
            if func.id == 'open':
                return 'open'
            return None
        if isinstance(func, ast.Attribute):
            value = func.value
            if isinstance(value, ast.Name) and value.id in self.modules:
                return f'{self.modules[value.id]}.{func.attr}'
            if func.attr in ('read_text', 'write_text'):
                return f'Path.{func.attr}'
            if func.attr == 'open':
                if isinstance(value, ast.Name) and value.id in NOT_PATH_OPEN:
                    return None
                return 'Path.open'
        return None

    def report(self, node: ast.Call, name: str, detail: str) -> None:
        self.found.append((self.path, node.lineno, node.col_offset + 1, f'{name}: {detail}'))

    def visit_Call(self, node: ast.Call) -> None:
        name = self.qualified(node.func)
        if name == 'pathlib.Path.open':
            name = 'Path.open'
        if name in OPEN_LIKE:
            self.check_open(node, name)
        elif name in ('Path.read_text', 'Path.write_text'):
            index = 0 if name == 'Path.read_text' else 1
            self.check_encoding(node, name, index)
        elif name and name.startswith('subprocess.') and name.split('.', 1)[1] in SUBPROCESS_CALLS:
            self.check_subprocess(node, name)
        self.generic_visit(node)

    def check_open(self, node: ast.Call, name: str) -> None:
        mode_index, encoding_index, text_by_default = OPEN_LIKE[name]
        mode = keyword(node, 'mode')
        if mode is None and mode_index is not None and len(node.args) > mode_index:
            mode = node.args[mode_index]
        if mode is None:
            is_text = text_by_default
        else:
            is_text = not (isinstance(mode, ast.Constant) and isinstance(mode.value, str) and 'b' in mode.value)
        if not is_text:
            return
        if name.startswith('fileinput.') and keyword(node, 'openhook') is not None:
            return
        self.check_encoding(node, name, encoding_index)

    def check_encoding(self, node: ast.Call, name: str, index: int | None) -> None:
        value = keyword(node, 'encoding')
        if value is None and index is not None and len(node.args) > index:
            value = node.args[index]
        if value is None:
            self.report(node, name, 'text I/O without an explicit encoding')
        elif isinstance(value, ast.Constant) and value.value is None:
            self.report(node, name, 'text I/O with encoding=None')

    def check_subprocess(self, node: ast.Call, name: str) -> None:
        text = [keyword(node, key) for key in ('text', 'universal_newlines')]
        enabled = [v for v in text if v is not None and not (isinstance(v, ast.Constant) and not v.value)]
        if enabled:
            self.check_encoding(node, name, None)


def keyword(node: ast.Call, name: str) -> ast.expr | None:
    for item in node.keywords:
        if item.arg == name:
            return item.value
    return None


def excluded(relative: str) -> bool:
    return any(relative.startswith(prefix) for prefix in EXCLUDED)


def tracked_files() -> list[str]:
    result = subprocess.run(
        ['git', 'ls-files', '-z', '--', '*.py'], cwd=ROOT,
        capture_output=True, check=True,
    )
    return sorted(p for p in result.stdout.decode('utf-8').split('\0') if p)


def check_file(path: Path, relative: str) -> list[tuple[str, int, int, str]]:
    source = path.read_text(encoding='utf-8')
    visitor = Visitor(relative)
    visitor.visit(ast.parse(source, filename=relative))
    return visitor.found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('paths', nargs='*', help='Files to check (default: tracked Python files)')
    parser.add_argument('--summary', action='store_true', help='Print counts of calls, lines and files')
    parser.add_argument('--list-excluded', action='store_true', help='Print the excluded paths and reasons')
    args = parser.parse_args(argv)

    if args.list_excluded:
        for prefix, reason in EXCLUDED.items():
            print(f'{prefix}\t{reason}')
        return 0

    if args.paths:
        targets = [(Path(p), Path(p).as_posix()) for p in args.paths]
    else:
        targets = [(ROOT / p, p) for p in tracked_files() if not excluded(p)]

    found: list[tuple[str, int, int, str]] = []
    for path, relative in targets:
        try:
            found.extend(check_file(path, relative))
        except (OSError, SyntaxError, UnicodeDecodeError) as error:
            print(f'{relative}: cannot check: {error}', file=sys.stderr)
            return 2

    for relative, line, column, message in found:
        print(f'{relative}:{line}:{column}: {message}')
    if args.summary or found:
        lines = {(f[0], f[1]) for f in found}
        files = {f[0] for f in found}
        print(f'{len(found)} calls, {len(lines)} lines, {len(files)} files '
              f'({len(targets)} files checked)', file=sys.stderr)
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
