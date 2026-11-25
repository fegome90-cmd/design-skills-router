"""Behaviour of scripts/check-docs.py on reachable, orphan and roadmap-ID cases."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / 'scripts' / 'check-docs.py'

BASE = {
    'README.md': '# Repo\n\n[Contexto](docs/agent/CONTEXT.md)\n',
    'AGENTS.md': '# Agentes\n',
    'docs/agent/CONTEXT.md': '# Contexto\n\n[Roadmap](../specs/mcp-roadmap/README.md)\n',
    'docs/specs/mcp-roadmap/README.md': textwrap.dedent('''\
        # Roadmap

        | Unidad | Estado |
        |---|---|
        | [R02](units/R02-falta.md) | Planificada |
        | **R03A** | Planificada |
        '''),
    'board/src/capas/datos.json': json.dumps({'nodes': [{'id': 'F00'}, {'id': 'X99'}]}),
}


class CheckDocsTests(unittest.TestCase):
    def run_guard(self, extra=None, remove=(), raw=None):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files = {**BASE, **(extra or {})}
            for name in remove:
                files.pop(name)
            for name, text in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding='utf-8')
            for name, data in (raw or {}).items():
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_bytes(data)
            result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--root', str(root), '--summary'],
                                    capture_output=True, encoding='utf-8')
            return result.returncode, result.stdout.splitlines(), result.stderr

    def assertClean(self, extra=None, **kwargs):
        code, lines, err = self.run_guard(extra, **kwargs)
        self.assertEqual((code, lines), (0, []), err)
        return err

    def assertFinds(self, extra, expected, **kwargs):
        code, lines, err = self.run_guard(extra, **kwargs)
        self.assertEqual(code, 1, err)
        self.assertEqual(lines, expected)

    def test_base_fixture_is_clean(self):
        err = self.assertClean()
        self.assertIn('reachable_docs=2', err)
        self.assertIn('defined_by_table=2', err)

    def test_reachable_through_any_markdown_and_directory_readme(self):
        self.assertClean({
            'AGENTS.md': '[Guía](plugin/GUIDE.md)\n',
            'plugin/GUIDE.md': '[ADR](../docs/adr/)\n',
            'docs/adr/README.md': '[Decisión](0001-decisión.md#contexto)\n',
            'docs/adr/0001-decisión.md': '# Decisión\n\n## Contexto\n',
        })

    def test_percent_encoded_and_accented_links(self):
        self.assertClean({
            'docs/agent/CONTEXT.md': '[Plan](../planificación.md) [Otro](../plan%20b.md)\n'
                                     '[Roadmap](../specs/mcp-roadmap/README.md)\n',
            'docs/planificación.md': '# Plan\n',
            'docs/plan b.md': '# B\n',
        })

    def test_orphan_document(self):
        self.assertFinds({'docs/suelto.md': '# Sin enlaces entrantes\n'}, [
            'docs/suelto.md:1: ORPHAN: not reachable from README.md, AGENTS.md or docs/agent/*.md'])

    def test_orphan_cycle_is_still_orphan(self):
        self.assertFinds({
            'docs/a.md': '[b](b.md)\n',
            'docs/b.md': '[a](a.md)\n',
        }, ['docs/a.md:1: ORPHAN: not reachable from README.md, AGENTS.md or docs/agent/*.md',
            'docs/b.md:1: ORPHAN: not reachable from README.md, AGENTS.md or docs/agent/*.md'])

    def test_links_in_code_and_external_links_do_not_reach(self):
        self.assertFinds({
            'AGENTS.md': '```md\n[x](docs/x.md)\n```\n`[y](docs/x.md)` [web](https://example.org/docs/x.md)\n',
            'docs/x.md': '# X\n',
        }, ['docs/x.md:1: ORPHAN: not reachable from README.md, AGENTS.md or docs/agent/*.md'])

    def test_id_defined_by_json_unit_file_and_declared_table(self):
        self.assertClean({
            'docs/agent/CONTEXT.md': 'F00, R07B y R02, R03A. [Roadmap](../specs/mcp-roadmap/README.md) '
                                     '[unidad](../specs/otro/units/R07B-algo.md)\n',
            'docs/specs/otro/units/R07B-algo.md': '# R07B\n',
        })

    def test_undefined_id(self):
        self.assertFinds({'docs/agent/CONTEXT.md': 'Depende de R08.\n[Roadmap](../specs/mcp-roadmap/README.md)\n'},
                         ['docs/agent/CONTEXT.md:1: UNDEFINED_ID: R08 has no recognised definition'])

    def test_id_in_an_undeclared_table_defines_nothing(self):
        self.assertFinds({'docs/agent/CONTEXT.md': textwrap.dedent('''\
            [Roadmap](../specs/mcp-roadmap/README.md)

            | Unidad | Estado |
            |---|---|
            | R06 | inventada |
            ''')}, ['docs/agent/CONTEXT.md:5: UNDEFINED_ID: R06 has no recognised definition'])

    def test_only_the_declared_header_and_first_column_define(self):
        self.assertFinds({'docs/specs/mcp-roadmap/README.md': textwrap.dedent('''\
            | Unidad | Depende de |
            |---|---|
            | R02 | R11 |

            | Tema | Unidad |
            |---|---|
            | R12 | x |
            ''')}, ['docs/specs/mcp-roadmap/README.md:3: UNDEFINED_ID: R11 has no recognised definition',
                    'docs/specs/mcp-roadmap/README.md:7: UNDEFINED_ID: R12 has no recognised definition'])

    def test_json_id_must_match_the_pattern(self):
        self.assertFinds({'docs/agent/CONTEXT.md': 'X99 y R99.\n[Roadmap](../specs/mcp-roadmap/README.md)\n'},
                         ['docs/agent/CONTEXT.md:1: UNDEFINED_ID: R99 has no recognised definition'])

    def test_fenced_code_is_ignored_for_ids_but_inline_code_counts(self):
        self.assertFinds({'docs/agent/CONTEXT.md': textwrap.dedent('''\
            [Roadmap](../specs/mcp-roadmap/README.md)
            ````text
            R40 dentro de un bloque
            ```
            sigue dentro
            ````
            ~~~
            R41
            ~~~
            Fuera: `R42`.
            ''')}, ['docs/agent/CONTEXT.md:10: UNDEFINED_ID: R42 has no recognised definition'])

    def test_ids_outside_docs_are_not_checked(self):
        self.assertClean({'plugin/NOTES.md': 'R77 vive fuera de docs/.\n'})

    def test_utf8_with_bom_and_accents(self):
        context = '﻿# Contexto ñandú\n\n[Roadmap](../specs/mcp-roadmap/README.md) R02.\n'
        self.assertClean(raw={'docs/agent/CONTEXT.md': context.encode('utf-8')})
        self.assertFinds(None, ['docs/agent/CONTEXT.md:3: UNDEFINED_ID: R13 has no recognised definition'],
                         raw={'docs/agent/CONTEXT.md': context.replace('R02', 'R13').encode('utf-8')})

    def test_missing_definition_table_is_reported(self):
        code, lines, _ = self.run_guard({'docs/agent/CONTEXT.md': 'Nada.\n'},
                                        remove=('docs/specs/mcp-roadmap/README.md',))
        self.assertEqual(code, 1)
        self.assertEqual(lines, ['docs/specs/mcp-roadmap/README.md:1: MISSING_DEFINITION_TABLE: '
                                 'declared in DEFINITION_TABLES'])

    def test_invalid_utf8_and_bad_root_exit_2(self):
        code, _, err = self.run_guard(raw={'docs/agent/CONTEXT.md': b'\xff\xfe'})
        self.assertEqual(code, 2, err)
        result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--root', str(ROOT / 'no-such-dir')],
                                capture_output=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2)

    def test_repository_is_clean(self):
        result = subprocess.run([sys.executable, '-B', str(SCRIPT)], capture_output=True, encoding='utf-8')
        self.assertEqual((result.returncode, result.stdout), (0, ''), result.stderr)


if __name__ == '__main__':
    unittest.main()
