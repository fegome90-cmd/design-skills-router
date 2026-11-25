#!/usr/bin/env python3
"""Check that the documentation is reachable and that roadmap IDs are defined.

Uses only the standard library. Two checks:

Reachability
    The Markdown files form a directed graph through their relative links.
    Every ``docs/**/*.md`` must be reachable from an entry point: ``README.md``,
    ``AGENTS.md`` or ``docs/agent/*.md``. A group of documents that only link
    to each other is still an orphan. Exceptions need a reason in
    ``ORPHAN_EXCEPTIONS``.

Roadmap IDs
    Every ``\\b[RF]\\d{2}[A-Z]?\\b`` in ``docs/**/*.md`` must come from a
    recognised source:
    * an ``id`` value in ``board/src/*/datos.json``;
    * a roadmap unit file name, ``docs/specs/**/units/<ID>-*.md``;
    * the first column of a definition table declared in
      ``DEFINITION_TABLES``.
    A mention in any other table defines nothing.

Files are read as ``utf-8-sig``. Fenced code blocks are ignored by both
checks; inline code is ignored for links but still counts as an ID mention.
Link validity itself (missing files, missing anchors) is checked by lychee in
``.github/workflows/docs.yml``.

Exit status: 0 when clean, 1 when a finding is reported, 2 on usage errors.
"""

from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent

ID = re.compile(r'\b[RF]\d{2}[A-Z]?\b')
SKIPPED_DIRS = ('vendor/', 'release/', 'node_modules/')
ENTRY_POINTS = ('README.md', 'AGENTS.md')
ENTRY_GLOB = 'docs/agent/*.md'

# Documents under docs/ that may stay unreachable. Each entry needs a reason.
ORPHAN_EXCEPTIONS: dict[str, str] = {}

# Declared definition tables: file -> header of the first column. Only the
# first column of a table whose first header cell matches defines IDs.
DEFINITION_TABLES = {
    'docs/specs/mcp-roadmap/README.md': 'Unidad',
}

FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})')
INLINE_CODE = re.compile(r'(`+)(?:(?!\1).)+?\1')
INLINE_LINK = re.compile(r'!?\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)')
REFERENCE_DEF = re.compile(r'^ {0,3}\[[^\]]+\]:\s*<?(\S+?)>?(?:\s+.*)?$')
HTML_LINK = re.compile(r'\b(?:href|src)\s*=\s*["\']([^"\']+)["\']', re.I)
SCHEME = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*:')
UNIT_FILE = re.compile(r'^docs/specs/(?:.+/)?units/([RF]\d{2}[A-Z]?)-[^/]*\.md$')
MD_LINK_TEXT = re.compile(r'^\[([^\]]+)\]\([^)]*\)$')


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8-sig')


def prose_lines(text: str):
    """Yield (line number, line) outside fenced code blocks."""
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        match = FENCE.match(line)
        if fence is None:
            if match:
                fence = match.group(1)
                continue
            yield number, line
        elif match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence) \
                and not line.strip()[len(match.group(1)):].strip():
            fence = None


def markdown_files(root: Path) -> list[str]:
    try:
        result = subprocess.run(['git', 'ls-files', '-z', '--', '*.md'], cwd=root,
                                capture_output=True, check=True)
        files = [p for p in result.stdout.decode('utf-8').split('\0') if p]
    except (OSError, subprocess.CalledProcessError):
        files = [p.relative_to(root).as_posix() for p in root.rglob('*.md') if '.git' not in p.parts]
    return sorted(p for p in files if not p.startswith(SKIPPED_DIRS) and (root / p).is_file())


def link_targets(text: str):
    for number, line in prose_lines(text):
        line = INLINE_CODE.sub('', line)
        for pattern in (INLINE_LINK, HTML_LINK):
            for match in pattern.finditer(line):
                yield number, match.group(1)
        match = REFERENCE_DEF.match(line)
        if match:
            yield number, match.group(1)


def resolve(source: str, target: str, files: set[str]) -> str | None:
    """Return the Markdown file a relative link points to, if any."""
    if SCHEME.match(target) or target.startswith(('#', '/')):
        return None
    path = unquote(target.split('#', 1)[0].split('?', 1)[0])
    if not path:
        return None
    joined = PurePosixPath(source).parent / path
    parts: list[str] = []
    for part in joined.parts:
        if part == '..':
            if not parts:
                return None
            parts.pop()
        elif part != '.':
            parts.append(part)
    candidate = '/'.join(parts)
    if candidate in files:
        return candidate
    readme = f'{candidate}/README.md' if candidate else 'README.md'
    return readme if readme in files else None


def check_reachability(root: Path, files: list[str], texts: dict[str, str]) -> tuple[list[str], dict]:
    known = set(files)
    edges = {f: {t for _, link in link_targets(texts[f]) if (t := resolve(f, link, known))} for f in files}
    entries = [f for f in files if f in ENTRY_POINTS or PurePosixPath(f).match(ENTRY_GLOB)]
    seen = set(entries)
    queue = deque(entries)
    while queue:
        for target in edges[queue.popleft()]:
            if target not in seen:
                seen.add(target)
                queue.append(target)
    docs = [f for f in files if f.startswith('docs/')]
    findings = [f'{f}:1: ORPHAN: not reachable from README.md, AGENTS.md or docs/agent/*.md'
                for f in docs if f not in seen and f not in ORPHAN_EXCEPTIONS]
    findings += [f'{f}:1: STALE_EXCEPTION: listed in ORPHAN_EXCEPTIONS but missing or reachable'
                 for f in ORPHAN_EXCEPTIONS if f not in known or f in seen]
    stats = {'entry_points': len(entries), 'docs': len(docs), 'reachable_docs': len([d for d in docs if d in seen])}
    return findings, stats


def json_ids(root: Path) -> set[str]:
    found: set[str] = set()

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == 'id' and isinstance(item, str) and ID.fullmatch(item):
                    found.add(item)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for path in sorted(root.glob('board/src/*/datos.json')):
        walk(json.loads(read(path)))
    return found


def table_ids(text: str, header: str) -> set[str]:
    """IDs in the first column of the tables whose first header cell is ``header``."""
    found: set[str] = set()
    rows = [line.strip() for _, line in prose_lines(text)]
    active = False
    for index, row in enumerate(rows):
        if not row.startswith('|'):
            active = False
            continue
        cells = [cell.strip() for cell in row.strip('|').split('|')]
        following = rows[index + 1] if index + 1 < len(rows) else ''
        if re.fullmatch(r'\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?', following):
            active = cells[0] == header
            continue
        if active and not re.fullmatch(r'[\s:|-]+', row):
            cell = cells[0].strip('*` ')
            match = MD_LINK_TEXT.match(cell)
            cell = match.group(1).strip('*` ') if match else cell
            if ID.fullmatch(cell):
                found.add(cell)
    return found


def check_ids(root: Path, files: list[str], texts: dict[str, str]) -> tuple[list[str], dict]:
    sources = {'json': json_ids(root),
               'unit': {m.group(1) for f in files if (m := UNIT_FILE.match(f))},
               'table': set()}
    missing_tables = []
    for path, header in DEFINITION_TABLES.items():
        if path in texts:
            sources['table'] |= table_ids(texts[path], header)
        else:
            missing_tables.append(path)
    defined = set().union(*sources.values())
    findings = [f'{p}:1: MISSING_DEFINITION_TABLE: declared in DEFINITION_TABLES' for p in missing_tables]
    mentioned: set[str] = set()
    for path in files:
        if not path.startswith('docs/'):
            continue
        for number, line in prose_lines(texts[path]):
            for match in ID.finditer(line):
                mentioned.add(match.group(0))
                if match.group(0) not in defined:
                    findings.append(f'{path}:{number}: UNDEFINED_ID: {match.group(0)} has no recognised definition')
    stats = {'ids_mentioned': len(mentioned), 'ids_defined': len(defined),
             **{f'defined_by_{k}': len(v) for k, v in sources.items()}}
    return findings, stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', type=Path, default=ROOT, help='Repository root (default: this checkout)')
    parser.add_argument('--summary', action='store_true', help='Print counts')
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        print(f'{root}: not a directory', file=sys.stderr)
        return 2
    files = markdown_files(root)
    try:
        texts = {f: read(root / f) for f in files}
    except (OSError, UnicodeDecodeError) as error:
        print(f'cannot read Markdown: {error}', file=sys.stderr)
        return 2
    reach, reach_stats = check_reachability(root, files, texts)
    try:
        ids, id_stats = check_ids(root, files, texts)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        print(f'cannot read ID sources: {error}', file=sys.stderr)
        return 2
    findings = reach + ids
    for finding in findings:
        print(finding)
    if args.summary or findings:
        stats = {'markdown_files': len(files), **reach_stats, **id_stats, 'findings': len(findings)}
        print(', '.join(f'{k}={v}' for k, v in stats.items()), file=sys.stderr)
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
