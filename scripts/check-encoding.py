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
* ``fileinput.input`` and ``fileinput.FileInput`` in text mode, unless the
  ``openhook`` is ``hook_encoded(enc)`` or ``hook_compressed(encoding=enc)``
  (fileinput passes its own ``encoding`` to any other hook);
* ``subprocess.run``, ``Popen``, ``call``, ``check_call`` and
  ``check_output`` with ``text``, ``universal_newlines`` or ``errors``
  enabled (any of them puts the pipes in text mode).

A mode is binary only when it is a string literal that contains ``b``.
Any other mode, including a variable, is treated as text. ``mkstemp``,
``mkdtemp``, ``TemporaryDirectory`` and ``gettempdir`` do not open text
streams and are never reported.

A call is skipped when the line where it starts carries the comment
``# check-encoding: ignore[reason]``. The reason is mandatory, the marker
must be a real comment (not text inside a string), and it covers a single
reportable call: a marked line with two of them reports both. ``--summary``
lists every skipped call. Use it only for a false positive, for example the
``open`` method of a binary API that the heuristics take for ``Path.open``.

Known limits, covered at run time by ``EncodingWarning`` in CI: a local
function that shadows ``open``, arguments passed through ``**kwargs``,
``os.popen`` and ``subprocess.getoutput`` (no ``encoding`` parameter on
Python 3.10), dynamic lookups such as ``getattr(io, 'open')``, and imports inside a
function, which apply from that point to the end of the function.

By default the check reads the Python files tracked by Git, minus the
frozen paths listed in ``EXCLUDED``. Exit status: 0 when clean, 1 when a
violation is found, 2 on usage or parse errors.
"""

from __future__ import annotations

import argparse
import ast
import re
import io
import subprocess
import sys
import tokenize
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
    def __init__(self, path: str, ignore_lines: set[int] | None = None):
        self.path = path
        self.ignore_lines = ignore_lines or set()
        self.found: list[tuple[str, int, int, str]] = []
        self.ignored: list[tuple[str, int, int, str]] = []
        self.modules: dict[str, str] = {}  # local alias -> module
        self.names: dict[str, str] = {}    # local name -> 'module.attr'

    def collect_imports(self, tree: ast.AST) -> None:
        """Register module-level imports first, so a use before them resolves.

        Imports inside functions, classes and lambdas are left to the normal
        visit, so they cannot hide calls elsewhere in the module.
        """
        pending = list(ast.iter_child_nodes(tree))
        while pending:
            node = pending.pop()
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            if isinstance(node, ast.Import):
                self.visit_Import(node, recurse=False)
            elif isinstance(node, ast.ImportFrom):
                self.visit_ImportFrom(node, recurse=False)
            pending.extend(ast.iter_child_nodes(node))

    def visit_scope(self, node: ast.AST) -> None:
        """Imports inside a function, class or lambda stay inside it."""
        saved = dict(self.modules), dict(self.names)
        self.generic_visit(node)
        self.modules, self.names = saved

    visit_FunctionDef = visit_AsyncFunctionDef = visit_Lambda = visit_scope

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Class-body bindings are visible in the class body, not in its methods."""
        outer = dict(self.modules), dict(self.names)
        for child in [*node.decorator_list, *node.bases, *node.keywords]:
            self.visit(child)
        for statement in node.body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                inner = self.modules, self.names
                self.modules, self.names = dict(outer[0]), dict(outer[1])
                self.visit(statement)
                self.modules, self.names = inner
            else:
                self.visit(statement)
        self.modules, self.names = outer

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
        entry = (self.path, node.lineno, node.col_offset + 1, f'{name}: {detail}')
        (self.ignored if node.lineno in self.ignore_lines else self.found).append(entry)

    def finish(self) -> None:
        """A marker covers one call: report every call of a line that holds several."""
        per_line: dict[int, int] = {}
        for entry in self.ignored:
            per_line[entry[1]] = per_line.get(entry[1], 0) + 1
        crowded = {line for line, count in per_line.items() if count > 1}
        for entry in self.ignored:
            if entry[1] in crowded:
                self.found.append((*entry[:3], entry[3] + ' (ignore marker covers more than one call)'))
        self.ignored = [entry for entry in self.ignored if entry[1] not in crowded]
        self.found.sort()

    def is_path_class(self, value: ast.expr) -> bool:
        """True for the ``pathlib.Path`` class itself, as in ``Path.read_text(p)``."""
        if isinstance(value, ast.Name):
            return self.names.get(value.id) == 'pathlib.Path'
        return (isinstance(value, ast.Attribute) and value.attr == 'Path'
                and isinstance(value.value, ast.Name) and self.modules.get(value.value.id) == 'pathlib')

    def visit_Call(self, node: ast.Call) -> None:
        name = self.qualified(node.func)
        # Calling a method on the class passes the path as the first argument.
        shift = 1 if (isinstance(node.func, ast.Attribute) and self.is_path_class(node.func.value)) else 0
        if name == 'pathlib.Path.open':
            name = 'Path.open'
        elif name == 'builtins.open':
            name = 'open'
        if name in OPEN_LIKE:
            self.check_open(node, name, shift if name == 'Path.open' else 0)
        elif name in ('Path.read_text', 'Path.write_text'):
            index = 0 if name == 'Path.read_text' else 1
            self.check_encoding(node, name, index + shift)
        elif name and name.startswith('subprocess.') and name.split('.', 1)[1] in SUBPROCESS_CALLS:
            self.check_subprocess(node, name)
        self.generic_visit(node)

    def check_open(self, node: ast.Call, name: str, shift: int = 0) -> None:
        mode_index, encoding_index, text_by_default = OPEN_LIKE[name]
        if shift:
            mode_index, encoding_index = mode_index + shift, encoding_index + shift
        mode = keyword(node, 'mode')
        if mode is None and mode_index is not None and len(node.args) > mode_index:
            mode = node.args[mode_index]
        if mode is None:
            is_text = text_by_default
        else:
            is_text = not (isinstance(mode, ast.Constant) and isinstance(mode.value, str) and 'b' in mode.value)
        if not is_text:
            return
        if name.startswith('fileinput.') and self.hook_sets_encoding(keyword(node, 'openhook')):
            return
        self.check_encoding(node, name, encoding_index)

    def hook_sets_encoding(self, hook: ast.expr | None) -> bool:
        """``hook_encoded(enc)`` or ``hook_compressed(encoding=enc)`` with a real encoding.

        Any other hook gets fileinput's own ``encoding``, which is checked as usual.
        """
        if not isinstance(hook, ast.Call):
            return False
        name = self.qualified(hook.func)
        if name == 'fileinput.hook_encoded':
            value = keyword(hook, 'encoding') or (hook.args[0] if hook.args else None)
        elif name == 'fileinput.hook_compressed':
            value = keyword(hook, 'encoding')
        else:
            return False
        return value is not None and not is_none(value)

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


def marked_lines(source: str) -> set[int]:
    """Lines whose comment token carries a valid ignore marker."""
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    return {tok.start[0] for tok in tokens if tok.type == tokenize.COMMENT and IGNORE.search(tok.string)}


def inspect_file(path: Path, relative: str) -> Visitor:
    source = path.read_text(encoding='utf-8')
    tree = ast.parse(source, filename=relative)
    visitor = Visitor(relative, marked_lines(source))
    visitor.collect_imports(tree)
    visitor.visit(tree)
    visitor.finish()
    return visitor


def check_file(path: Path, relative: str) -> list[tuple[str, int, int, str]]:
    return inspect_file(path, relative).found


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
    ignored: list[tuple[str, int, int, str]] = []
    for path, relative in targets:
        try:
            visitor = inspect_file(path, relative)
            found.extend(visitor.found)
            ignored.extend(visitor.ignored)
        except (OSError, SyntaxError, UnicodeDecodeError, tokenize.TokenError) as error:
            print(f'{relative}: cannot check: {error}', file=sys.stderr)
            return 2

    for relative, line, column, message in found:
        print(f'{relative}:{line}:{column}: {message}')
    if args.summary or found:
        lines = {(f[0], f[1]) for f in found}
        files = {f[0] for f in found}
        print(f'{len(found)} calls, {len(lines)} lines, {len(files)} files '
              f'({len(targets)} files checked, {len(ignored)} calls ignored by marker)', file=sys.stderr)
        for relative, line, column, message in ignored:
            print(f'ignored: {relative}:{line}:{column}: {message}', file=sys.stderr)
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
