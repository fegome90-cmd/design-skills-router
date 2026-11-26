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

Links are inline links and images (``<dest>``, nested parentheses and
titles included), reference definitions that a ``[text][label]`` or
``[label]`` actually uses, and HTML ``href``/``src``. HTML comments, escaped
brackets and inline code are not links.

Files are read as ``utf-8-sig``; the Markdown files are the tracked and the
untracked, not ignored ones, so a new document is checked before ``git add``.
Fenced code blocks are ignored by both checks and end a table; inline code
still counts as an ID mention. Known limits: indented code blocks and fences
nested in lists or block quotes are read as prose, a definition table cell
holds one or more IDs separated by ',' or '/' outside links (with no delimiters
inside the link text itself), and an HTML comment that opens in one table row
and closes in a later one hides the rows in between. HTML script/style
raw text is not a distinct context for tag detection. Link validity itself
(missing files and anchors) is checked by lychee in ``.github/workflows/docs.yml``.

Exit status: 0 when clean, 1 when a finding is reported, 2 on usage errors or
when a Markdown or ``datos.json`` file cannot be read or parsed.
"""

from __future__ import annotations

import argparse
from collections import deque
from html.parser import HTMLParser
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
ENTRY_DIR = 'docs/agent'  # files directly in it; subfolders are not entry points

# Documents under docs/ that may stay unreachable. Each entry needs a reason.
ORPHAN_EXCEPTIONS: dict[str, str] = {}

# Declared definition tables: file -> header of the first column. Only the
# first column of a table whose first header cell matches defines IDs.
DEFINITION_TABLES = {
    'docs/specs/mcp-roadmap/README.md': 'Unidad',
}

FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})')
INLINE_CODE = re.compile(r'(`+)(?:(?!\1).)+?\1', re.S)
LINK_TEXT = re.compile(r'(?<!\\)(?:\\\\)*!?\[(?:[^\[\]\\]|\\.|\[[^\]]*\])*\]\(')
REFERENCE_DEF = re.compile(r'^ {0,3}\[([^\]]+)\]:\s*(?:<([^>]*)>|(\S+))')
REFERENCE_DEF_START = re.compile(r'^ {0,3}\[([^\]]+)\]:[ \t]*$')
REFERENCE_DEF_TAIL = re.compile(r"""(?:[ \t]+(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\((?:\\.|[^()\\])*\)))?[ \t]*""")
REFERENCE_BLOCK_END = re.compile(r'^ {0,3}(?:#{1,6}(?:[ \t]|$)|(?:=+|-+)[ \t]*$)')
REFERENCE_USE = re.compile(r'(?<!\\)(?:\\\\)*\[([^\]]+)\](?:\[([^\]]*)\]|(?![(:]))')
# Match start tags, including quoted attributes, but not escaped opening brackets.
HTML_TAG = re.compile(r"""(?<!\\)(?:\\\\)*(?P<tag><[A-Za-z][A-Za-z0-9-]*(?=[\s/>])(?:[^<>"']|"[^"]*"|'[^']*')*>)""")
HTML_COMMENT = re.compile(r'<!--.*?-->', re.S)
SCHEME = re.compile(r'^[a-zA-Z][a-zA-Z0-9+.-]*:')
UNIT_FILE = re.compile(r'^docs/specs/(?:.+/)?units/([RF]\d{2}[A-Z]?)-[^/]*\.md$')
TABLE_SEPARATOR = re.compile(r'^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?$')
CELL_SPLIT = re.compile(r'(?<!\\)\|')


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8-sig')


def all_lines(text: str):
    """Yield (line number, line, inside a fenced code block). Fence lines count as inside."""
    fence = None
    in_comment = False
    for number, line in enumerate(text.splitlines(), 1):
        match = FENCE.match(line)
        if fence is None:
            rest = line
            if in_comment:
                end = line.find('-->')
                if end == -1:
                    yield number, line, False
                    continue
                rest, in_comment = line[end + 3:], False
            elif match:
                fence = match.group(1)
                yield number, line, True
                continue
            # An opener inside inline code is not an HTML comment.
            rest = INLINE_CODE.sub('', rest)
            in_comment = '<!--' in HTML_COMMENT.sub('', rest)
            yield number, line, False
        else:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence) \
                    and not line.strip()[len(match.group(1)):].strip():
                fence = None
            yield number, line, True


def prose_lines(text: str):
    """Yield (line number, line) outside fenced code blocks."""
    for number, line, code in all_lines(text):
        if not code:
            yield number, line


def markdown_files(root: Path) -> list[str]:
    """Tracked and untracked (not ignored) Markdown, so a new document is checked before git add."""
    try:
        result = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard',
                                 '--', '*.md'], cwd=root, capture_output=True, check=True)
        files = {p for p in result.stdout.decode('utf-8').split('\0') if p}
    except (OSError, subprocess.CalledProcessError):
        files = {p.relative_to(root).as_posix() for p in root.rglob('*.md') if '.git' not in p.parts}
    return sorted(p for p in files if not p.startswith(SKIPPED_DIRS) and (root / p).is_file())


ESCAPE = re.compile(r'\\([!-/:-@\[-`{-~])')
TITLE_END = {'"': '"', "'": "'", '(': ')'}


def unescape(value: str) -> str:
    """Decode CommonMark backslash escapes of ASCII punctuation."""
    return ESCAPE.sub(r'\1', value)


def label_key(label: str) -> str:
    """Normalise a reference label as CommonMark does: collapse whitespace, case-fold."""
    return ' '.join(label.split()).casefold()


def _parse_destination(line: str, start: int) -> tuple[str, int] | None:
    """Parse an inline link destination and optional title after ``](``.

    Returns ``(raw_target, closing_paren_index)`` or ``None`` if unclosed/invalid.
    """
    index = start
    while index < len(line) and line[index] in ' \t\n':
        index += 1
    if index < len(line) and line[index] == '<':
        index += 1
        begin = index
        while index < len(line):
            char = line[index]
            if char == '\\' and index + 1 < len(line):
                index += 2
                continue
            if char in '<\n':
                return None
            if char == '>':
                target = line[begin:index]
                index += 1
                break
            index += 1
        else:
            return None
    else:
        depth, begin = 0, index
        while index < len(line):
            char = line[index]
            if char == '\\' and index + 1 < len(line):
                index += 2
                continue
            if char in ' \t\n':
                break
            if char == '(':
                depth += 1
            elif char == ')':
                if depth == 0:
                    break
                depth -= 1
            index += 1
        target = line[begin:index]
    ws_start = index
    while index < len(line) and line[index] in ' \t\n':
        index += 1
    if index > ws_start and index < len(line) and line[index] in TITLE_END:
        closing = TITLE_END[line[index]]
        index += 1
        while index < len(line) and line[index] != closing:
            if line[index] == '\\':
                index += 2
                continue
            if closing == ')' and line[index] == '(':
                return None
            index += 1
        if index >= len(line):
            return None
        index += 1
        while index < len(line) and line[index] in ' \t\n':
            index += 1
    if index >= len(line) or line[index] != ')':
        return None
    return target, index


def destination(line: str, start: int) -> str | None:
    """Parse an inline link's destination after ``](``; None unless the link closes with ``)``."""
    parsed = _parse_destination(line, start)
    return (unescape(parsed[0]) or None) if parsed is not None else None


class HTMLLinks(HTMLParser):
    """Collect href and src only from actual HTML start tags."""

    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(value for name, value in attrs
                          if name in ('href', 'src') and value)


def link_targets(text: str):
    """Yield (line number, target) for inline, used reference and HTML links in prose."""
    lines = []
    in_comment = False
    for number, line, code in all_lines(text):
        if code:  # a fenced block ends the paragraph
            lines.append((number, ''))
            continue
        if in_comment:
            end = line.find('-->')
            if end == -1:
                continue
            line, in_comment = ' ' * (end + 3) + line[end + 3:], False
        line = INLINE_CODE.sub(lambda m: ' ' * len(m.group(0)), line)  # new openers in code are not comments
        line = HTML_COMMENT.sub(lambda m: ' ' * len(m.group(0)), line)
        if '<!--' in line:
            line, in_comment = line[:line.index('<!--')], True
        lines.append((number, line))
    definitions: dict[str, tuple[int, str]] = {}
    used: set[str] = set()
    paragraph: list[tuple[int, str]] = []
    skip_next = False
    for index, (number, line) in enumerate([*lines, (0, '')]):
        if skip_next:
            skip_next = False
            continue
        match = REFERENCE_DEF.match(line)
        # A multiline definition cannot interrupt prose. A heading ends
        # the preceding block even without a blank line.
        at_boundary = not paragraph or REFERENCE_BLOCK_END.match(paragraph[-1][1])
        if not match and at_boundary and REFERENCE_DEF_START.match(line) and index + 1 < len(lines):
            next_number, next_line = lines[index + 1]
            if (next_number == number + 1 and next_line.strip()
                    and not REFERENCE_DEF.match(next_line)
                    and not REFERENCE_DEF_START.match(next_line)):
                combined = line + '\n' + next_line
                candidate = REFERENCE_DEF.match(combined)
                # Consume the next line only for a complete destination
                # with an optional title, never for a prefix of prose/HTML.
                if candidate and REFERENCE_DEF_TAIL.fullmatch(combined[candidate.end():]):
                    match = candidate
                    skip_next = True
        if match:
            target = match.group(2) if match.group(2) is not None else match.group(3)
            definitions.setdefault(label_key(match.group(1)), (number, unescape(target)))
        if line.strip() and not match:
            paragraph.append((number, line))
            continue
        # CommonMark lets a link span line endings within a paragraph.
        if paragraph:
            text = '\n'.join(part for _, part in paragraph)
            text = INLINE_CODE.sub(lambda m: re.sub(r'[^\n]', ' ', m.group(0)), text)
            starts = [n for n, _ in paragraph]
            line_of = lambda offset: starts[text.count('\n', 0, offset)]
            for found in LINK_TEXT.finditer(text):
                target = destination(text, found.end())
                if target:
                    yield line_of(found.start()), target
            for found in REFERENCE_USE.finditer(text):
                used.add(label_key(found.group(2) or found.group(1)))
            for found in HTML_TAG.finditer(text):
                html = HTMLLinks()
                html.feed(found.group('tag'))
                html.close()
                for target in html.links:
                    yield line_of(found.start('tag')), target
            paragraph = []
    for label, (number, target) in definitions.items():
        if label in used:
            yield number, target


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
    entries = [f for f in files if f in ENTRY_POINTS or PurePosixPath(f).parent.as_posix() == ENTRY_DIR]
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


def _close_bracket(text: str, open_index: int) -> int | None:
    """Return the matching ']' index for '[' at ``open_index``, respecting escapes and nesting."""
    depth = 0
    index = open_index
    while index < len(text):
        char = text[index]
        if char == '\\' and index + 1 < len(text):
            index += 2
            continue
        if char == '[':
            depth += 1
        elif char == ']':
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _split_cell_items(cell: str) -> list[str]:
    """Split a table cell on ',' or '/' only outside '[text](url)' and balanced '()'."""
    items: list[str] = []
    start = 0
    bracket_depth = 0
    paren_depth = 0
    index = 0
    while index < len(cell):
        ch = cell[index]
        if ch == '\\' and index + 1 < len(cell):
            index += 2
            continue
        if ch == '[' and bracket_depth == 0 and paren_depth == 0:
            close_bracket = _close_bracket(cell, index)
            if (close_bracket is not None and close_bracket + 1 < len(cell) and
                    cell[close_bracket + 1] == '('):
                parsed = _parse_destination(cell, close_bracket + 2)
                if parsed is not None:
                    index = parsed[1] + 1
                    continue
        if ch == '[':
            bracket_depth += 1
        elif ch == ']' and bracket_depth > 0:
            bracket_depth -= 1
        elif ch == '(':
            paren_depth += 1
        elif ch == ')' and paren_depth > 0:
            paren_depth -= 1
        elif ch in (',', '/') and bracket_depth == 0 and paren_depth == 0:
            items.append(cell[start:index])
            start = index + 1
        index += 1
    items.append(cell[start:])
    return items


def _unwrap_cell_link(item: str) -> str:
    """Return link text when ``item`` is a single '[text](dest)' link, else ``item``."""
    if not item.startswith('['):
        return item
    close_bracket = _close_bracket(item, 0)
    if (close_bracket is None or close_bracket <= 1 or
            close_bracket + 1 >= len(item) or item[close_bracket + 1] != '('):
        return item
    parsed = _parse_destination(item, close_bracket + 2)
    if parsed is not None and parsed[1] == len(item) - 1:
        return item[1:close_bracket]
    return item


def _strip_cell_emphasis(value: str) -> str:
    """Trim surrounding whitespace (including tabs) and '*' / '`' emphasis markers."""
    while True:
        trimmed = value.strip().strip('*`')
        if trimmed == value:
            return value
        value = trimmed


def _parse_definition_cell(raw: str) -> set[str]:
    """Parse one or more delimited IDs from a definition cell (all-or-nothing)."""
    parsed: set[str] = set()
    for item in _split_cell_items(raw.strip()):
        candidate = _strip_cell_emphasis(_unwrap_cell_link(_strip_cell_emphasis(item)))
        if not ID.fullmatch(candidate):
            return set()
        parsed.add(candidate)
    return parsed


def table_ids(text: str, header: str) -> set[str]:
    """IDs in the first column of the GFM tables whose first header cell is ``header``."""
    found: set[str] = set()
    rows: list[tuple[str, bool]] = []
    in_comment = False  # a table inside an HTML comment is not rendered
    for _, line, code in all_lines(text):
        if code:
            rows.append(('', True))
            continue
        if in_comment:
            end = line.find('-->')
            if end == -1:
                rows.append(('', True))
                continue
            line, in_comment = line[end + 3:], False
        # New comment markers inside inline code are code, not comments.
        line = INLINE_CODE.sub(lambda m: m.group(0).replace('<!--', '<!-').replace('-->', '->'), line)
        line = HTML_COMMENT.sub('', line)
        if '<!--' in line:
            line, in_comment = line[:line.index('<!--')], True
        rows.append((line.strip(), False))
    active = False
    for index, (row, code) in enumerate(rows):
        if code or '|' not in row:
            active = False
            continue
        cells = [cell.strip() for cell in CELL_SPLIT.split(row.strip('|'))]
        following, following_code = rows[index + 1] if index + 1 < len(rows) else ('', True)
        if not following_code and '|' in following and TABLE_SEPARATOR.match(following):
            active = cells[0] == header
            continue
        if active and not TABLE_SEPARATOR.match(row):
            found |= _parse_definition_cell(cells[0])
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
