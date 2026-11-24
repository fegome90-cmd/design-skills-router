"""Rebuildable SQLite index and source sections for the G5 audit pilot."""
from __future__ import annotations

from contextlib import closing
import json
import re
import sqlite3
import struct
import zlib


PROFILE = 'g5'
NODE = 'E05__LAY01'
SKILL_SECTIONS = {
    'fegome90-cmd/my-skills/layout-grid-hierarchy': 'Fase 3: Jerarquía Visual y Squint Test',
    'jakubkrehel/skills/better-layout': 'Plan for growth and clipping',
}


def is_png(data):
    """Check PNG framing, checksums and encoded scanlines."""
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        return False
    cursor = 8
    image_data = []
    palette = False
    while cursor + 12 <= len(data):
        size, kind = struct.unpack_from('>I4s', data, cursor)
        end = cursor + 8 + size
        if end + 4 > len(data) or zlib.crc32(data[cursor + 4:end]) != struct.unpack_from('>I', data, end)[0]:
            return False
        if cursor == 8:
            if kind != b'IHDR' or size != 13:
                return False
            width, height, depth, color, compression, filtering, interlace = struct.unpack_from('>IIBBBBB', data, cursor + 8)
            depths = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
            if not (width and height) or depth not in depths.get(color, ()):
                return False
            if compression or filtering or interlace not in (0, 1):
                return False
            bits = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color] * depth
            passes = ((0, 0, 1, 1),) if not interlace else (
                (0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
                (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2),
            )
            scanlines = [((bits * ((width - x + dx - 1) // dx) + 7) // 8 + 1, (height - y + dy - 1) // dy)
                         for x, y, dx, dy in passes if width > x and height > y]
            expected = sum(stride * count for stride, count in scanlines)
            if expected > 128 * 1024 * 1024:
                return False
        elif kind == b'IHDR':
            return False
        if kind == b'PLTE':
            palette_limit = (1 << depth) if color == 3 else 256
            if palette or image_data or color in (0, 4) or size % 3 or not 1 <= size // 3 <= palette_limit:
                return False
            palette = True
        if kind == b'IDAT' and size:
            if color == 3 and not palette:
                return False
            image_data.append(data[cursor + 8:end])
        if kind == b'IEND':
            if size or not image_data or end + 4 != len(data):
                return False
            stream = zlib.decompressobj()
            try:
                decoded = stream.decompress(b''.join(image_data), expected + 1)
            except zlib.error:
                return False
            if not stream.eof or stream.unused_data or len(decoded) != expected:
                return False
            start = 0
            for stride, count in scanlines:
                stop = start + stride * count
                if any(decoded[offset] > 4 for offset in range(start, stop, stride)):
                    return False
                start = stop
            return True
        cursor = end + 4
    return False


def sections(skill_id, text):
    """Return named body sections, excluding metadata and fenced headings."""
    lines = text.splitlines(keepends=True)
    if lines and lines[0].strip() == '---':
        end = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == '---'), None)
        lines = lines[end + 1:] if end is not None else []
    headings = []
    fence = None
    for i, line in enumerate(lines):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if marker:
            chars, suffix = marker.groups()
            if fence is None:
                fence = chars
            elif chars[0] == fence[0] and len(chars) >= len(fence) and not suffix.strip():
                fence = None
            continue
        if fence is None:
            heading = re.match(r'^ {0,3}(#{1,6}) +(.+?)\s*$', line)
            if heading:
                _, title = heading.groups()
                headings.append((i, title))
    out = []
    for i, (start, title) in enumerate(headings):
        # Sections stop at the next heading of any level, avoiding duplicate bodies.
        end = headings[i + 1][0] if i + 1 < len(headings) else len(lines)
        body = ''.join(lines[start + 1:end]).strip()
        if body:
            out.append({'id': f'{skill_id}#{title}', 'skill_id': skill_id, 'title': title, 'body': body})
    return out


def read_index(path, context_id, rows, required_ids, query=None):
    """Refresh an outdated snapshot, then look up required IDs or search optional sections."""
    if path.is_symlink():
        raise ValueError('CONTEXT_INDEX_SYMLINK')
    with closing(sqlite3.connect(path)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('CREATE TABLE IF NOT EXISTS snapshot (slot INTEGER PRIMARY KEY, id TEXT NOT NULL)')
        db.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS sections USING fts5(
            id UNINDEXED, payload UNINDEXED, title, body, tokenize='unicode61 remove_diacritics 2')''')
        previous = db.execute('SELECT id FROM snapshot WHERE slot = 1').fetchone()
        count = db.execute('SELECT count(*) FROM sections').fetchone()[0]
        if previous != (context_id,) or count != len(rows):
            db.execute('DELETE FROM sections')
            db.executemany('INSERT INTO sections VALUES (?, ?, ?, ?)',
                           ((r['id'], json.dumps(r, ensure_ascii=False), r['title'], r['body']) for r in rows))
            db.execute('INSERT OR REPLACE INTO snapshot VALUES (1, ?)', (context_id,))
        slots = ','.join('?' for _ in required_ids)
        if query is None:
            result = db.execute(f'SELECT payload FROM sections WHERE id IN ({slots}) ORDER BY rowid', required_ids)
        else:
            terms = re.findall(r'[^\W_]+', query[:256], re.UNICODE)[:12]
            if not terms:
                return []
            match = ' OR '.join(f'"{term}"' for term in terms)
            result = db.execute(f'SELECT payload FROM sections WHERE sections MATCH ? AND id NOT IN ({slots}) '
                                'ORDER BY bm25(sections), rowid LIMIT 5', (match, *required_ids))
        retrieved = [json.loads(row[0]) for row in result]
        originals = {row['id']: row for row in rows}
        if any(not isinstance(row, dict) or originals.get(row.get('id')) != row for row in retrieved):
            raise ValueError('CONTEXT_INDEX_DRIFT')
        return retrieved
