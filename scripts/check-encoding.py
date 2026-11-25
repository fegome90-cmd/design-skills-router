#!/usr/bin/env python3
"""Reject text I/O that depends on the platform's default encoding.

The check is static and uses only the standard library. It reports calls
that open or decode text without an explicit ``encoding`` argument, or with
``encoding=None``:

* ``open`` (also as ``builtins.open``), ``io.open``, ``codecs.open``,
  ``os.fdopen`` and ``Path.open`` in text mode, and ``io.TextIOWrapper``;
* ``Path.read_text`` and ``Path.write_text``;
* ``tempfile.TemporaryFile``, ``NamedTemporaryFile`` and
  ``SpooledTemporaryFile`` in text mode (their default mode is binary);
* ``fileinput.input`` and ``fileinput.FileInput`` in text mode;
* ``subprocess.run``, ``Popen``, ``call``, ``check_call`` and
  ``check_output`` with ``text``, ``universal_newlines`` or ``errors``
  enabled (any of them puts the pipes in text mode).

A mode is binary only when it is a string literal that contains ``b``.
Any other mode, including a variable, is treated as text. ``mkstemp``,
``mkdtemp``, ``TemporaryDirectory`` and ``gettempdir`` do not open text
streams and are never reported.

A call on a line marked ``# check-encoding: ignore[reason]`` is skipped;
the reason is mandatory. Use it only for a false positive, for example the
``open`` method of a binary API that the heuristics take for ``Path.open``.

Known limits, covered at run time by ``EncodingWarning`` in CI: a local
function that shadows ``open``, arguments passed through ``**kwargs``,
``os.popen`` and ``subprocess.getoutput`` (no ``encoding`` parameter on
Python 3.10), and dynamic lookups such as ``getattr(io, 'open')``.

By default the check reads the Python files tracked by Git, minus the
frozen paths listed in ``EXCLUDED``. Exit status: 0 when clean, 1 when a
violation is found, 2 on usage or parse errors.
"""

from __future__ import annotations

import argparse
import ast
import re
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
IGNORE = re.compile(r'#\s*check-encoding:\s*ignore\[[^\]\s][^\]]*\]')
SUBPROCESS_CALLS = {'run', 'Popen', 'call', 'check_call', 'check_output'}
TEMPFILE_CALLS = {'TemporaryFile', 'NamedTemporaryFile', 'SpooledTemporaryFile'}

# name -> (index of mode, index of encoding, default mode is text)
# An index of None means the parameter is keyword-only.
OPEN_LIKE = {
    'open': (1, 3, True),
    'io.open': (1, 3, True),
    'codecs.open': (1, 2, True),
    'io.TextIOWrapper': (None, 1, True),
    'os.fdopen': (1, 3, True),
    'Path.open': (0, 2, True),
    'tempfile.TemporaryFile': (0, 2, False),
    'tempfile.NamedTemporaryFile': (0, 2, False),
    'tempfile.SpooledTemporaryFile': (1, 3, False),
    'fileinput.input': (None, None, True),
    'fileinput.FileInput': (None, None, True),
}


class Visitor(ast.NodeVisitor):
    def __init__(self, path: str, lines: list[str] | None = None):
        self.path = path
        self.lines = lines or []
        self.found: list[tuple[str, int, int, str]] = []
        self.modules: dict[str, str] = {}  # local alias -> module
        self.names: dict[str, str] = {}    # local name -> 'module.attr'

    def collect_imports(self, tree: ast.AST) -> None:
        """Register every import first, so a use before its import resolves."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.visit_Import(node, recurse=False)
            elif isinstance(node, ast.ImportFrom):
                self.visit_ImportFrom(node, recurse=False)

    def visit_Import(self, node: ast.Import, recurse: bool = True) -> None:
        for alias in node.names:
            if alias.asname:
                self.modules[alias.asname] = alias.name
            else:  # ``import os.path`` binds ``os``
                top = alias.name.split('.')[0]
                self.modules[top] = top
        if recurse:
            self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom, recurse: bool = True) -> None:
        if node.module and node.level == 0:
            for alias in node.names:
                self.names[alias.asname or alias.name] = f'{node.module}.{alias.name}'
        if recurse:
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
        line = self.lines[node.lineno - 1] if node.lineno <= len(self.lines) else ''
        if IGNORE.search(line):
            return
        self.found.append((self.path, node.lineno, node.col_offset + 1, f'{name}: {detail}'))

    def visit_Call(self, node: ast.Call) -> None:
        name = self.qualified(node.func)
        if name == 'pathlib.Path.open':
            name = 'Path.open'
        elif name == 'builtins.open':
            name = 'open'
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
        hook = keyword(node, 'openhook')
        if name.startswith('fileinput.') and hook is not None and not is_none(hook):
            return
        self.check_encoding(node, name, encoding_index)

    def check_encoding(self, node: ast.Call, name: str, index: int | None) -> None:
        value = keyword(node, 'encoding')
        if value is None and index is not None and len(node.args) > index:
            value = node.args[index]
        if value is None:
            self.report(node, name, 'text I/O without an explicit encoding')
        elif is_none(value):
            self.report(node, name, 'text I/O with encoding=None')

    def check_subprocess(self, node: ast.Call, name: str) -> None:
        text = [keyword(node, key) for key in ('text', 'universal_newlines', 'errors')]
        enabled = [v for v in text if v is not None and not (isinstance(v, ast.Constant) and not v.value)]
        if enabled:
            self.check_encoding(node, name, None)


def is_none(value: ast.expr) -> bool:
    return isinstance(value, ast.Constant) and value.value is None


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
    tree = ast.parse(source, filename=relative)
    visitor = Visitor(relative, re.split(r'\r\n|\r|\n', source))  # same line breaks as ast
    visitor.collect_imports(tree)
    visitor.visit(tree)
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
