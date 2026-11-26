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

    def test_link_destination_forms(self):
        self.assertClean({
            'docs/agent/CONTEXT.md': textwrap.dedent('''\
                [Roadmap](../specs/mcp-roadmap/README.md)
                [espacios](<../mi plan.md>) [paréntesis](../a(1).md)
                [título simple](../t1.md 'Título') [título paréntesis](../t2.md (Título))
                [referencia completa][ref] y [atajo].

                [ref]: ../r1.md
                [Atajo]: <../r 2.md> "t"
                '''),
            'docs/mi plan.md': '#\n', 'docs/a(1).md': '#\n', 'docs/t1.md': '#\n',
            'docs/t2.md': '#\n', 'docs/r1.md': '#\n', 'docs/r 2.md': '#\n',
        })

    def test_comments_escapes_and_unused_definitions_do_not_reach(self):
        orphan = 'not reachable from README.md, AGENTS.md or docs/agent/*.md'
        self.assertFinds({
            'AGENTS.md': textwrap.dedent('''\
                <!-- [a](docs/a.md) -->
                <!--
                [b](docs/b.md)
                -->
                \\[c](docs/c.md)
                [sin uso]: docs/d.md
                '''),
            **{f'docs/{n}.md': '#\n' for n in 'abcd'},
        }, [f'docs/{n}.md:1: ORPHAN: {orphan}' for n in 'abcd'])

    def test_links_may_span_line_endings_within_a_paragraph(self):
        self.assertClean({'docs/agent/CONTEXT.md': textwrap.dedent('''\
            [Roadmap](
              ../specs/mcp-roadmap/README.md)
            [texto en
            dos líneas](../b.md "título
            en dos líneas")
            '''), 'docs/b.md': '#\n'})
        self.assertFinds({'docs/agent/CONTEXT.md': '[Roadmap](../specs/mcp-roadmap/README.md)\n[b](\n```\nx\n```\n../b.md)\n',
                          'docs/b.md': '#\n'},
                         ['docs/b.md:1: ORPHAN: not reachable from README.md, AGENTS.md or docs/agent/*.md'])
        self.assertFinds({'docs/agent/CONTEXT.md': '[Roadmap](../specs/mcp-roadmap/README.md)\n[b](\n\n../b.md)\n',
                          'docs/b.md': '#\n'},
                         ['docs/b.md:1: ORPHAN: not reachable from README.md, AGENTS.md or docs/agent/*.md'])

    def test_only_html_tag_attributes_create_html_links(self):
        orphan = 'not reachable from README.md, AGENTS.md or docs/agent/*.md'
        self.assertFinds({
            'AGENTS.md': (
                'Ejemplo: href="docs/a.md" src="docs/b.md"\n'
                '<a data-href="docs/c.md" href="docs/d.md">D</a>\n'
                '<img src="docs/e.md" alt="E">\n'
                '<a\n href="docs/f.md">F</a>\n'
            ),
            **{f'docs/{n}.md': '#\n' for n in 'abcdef'},
        }, [f'docs/{n}.md:1: ORPHAN: {orphan}' for n in 'abc'])

    def test_reference_definition_destination_may_be_on_next_line(self):
        self.assertClean({
            'AGENTS.md': '[Guía][ref] y [atajo].\n\n'
                         '[ref]:\n  docs/a.md\n'
                         '[atajo]:\n  <docs/mi plan.md> "título"\n',
            'docs/a.md': '#\n', 'docs/mi plan.md': '#\n',
        })

    def test_unused_and_blank_separated_reference_definitions_do_not_reach(self):
        orphan = 'not reachable from README.md, AGENTS.md or docs/agent/*.md'
        self.assertFinds({
            'AGENTS.md': '[separada]\n\n[sin uso]:\n  docs/a.md\n'
                         '[separada]:\n\n  docs/b.md\n',
            'docs/a.md': '#\n', 'docs/b.md': '#\n',
        }, [f'docs/{n}.md:1: ORPHAN: {orphan}' for n in 'ab'])

    def test_incomplete_reference_does_not_hide_html_link(self):
        self.assertClean({
            'AGENTS.md': '[x]:\n<a href="docs/a.md">A</a>\n',
            'docs/a.md': '#\n',
        })

    def test_multiline_reference_cannot_interrupt_paragraph_or_have_trailing_junk(self):
        orphan = 'not reachable from README.md, AGENTS.md or docs/agent/*.md'
        self.assertFinds({
            'AGENTS.md': 'Véase [x].\n[x]:\n  docs/a.md\n\n'
                         '[y]\n\n[y]:\n  docs/b.md texto\n',
            'docs/a.md': '#\n', 'docs/b.md': '#\n',
        }, [f'docs/{n}.md:1: ORPHAN: {orphan}' for n in 'ab'])

    def test_multiline_reference_after_heading_with_title(self):
        self.assertClean({
            'AGENTS.md': '[x] [y]\n\n# Heading\n[x]:\n  docs/a.md "title"\n'
                         '\nSection\n-------\n[y]:\n  <docs/b.md> (title)\n',
            'docs/a.md': '#\n', 'docs/b.md': '#\n',
        })

    def test_multiline_code_span_does_not_create_links(self):
        self.assertFinds({
            'AGENTS.md': 'Ejemplo: \x60[x](\ndocs/x.md)\x60\n\n'
                         '[real](\ndocs/real.md)\n',
            'docs/x.md': '# X\n', 'docs/real.md': '# Real\n',
        }, ['docs/x.md:1: ORPHAN: not reachable from README.md, AGENTS.md or docs/agent/*.md'])

    def test_fence_inside_html_comment_does_not_hide_visible_links_and_table(self):
        self.assertClean({
            'AGENTS.md': '<!--\n\x60\x60\x60\n-->\n\n[real](docs/real.md)\n',
            'docs/real.md': '# Real\n',
            'docs/agent/CONTEXT.md': '[Roadmap](../specs/mcp-roadmap/README.md) R17\n',
            'docs/specs/mcp-roadmap/README.md': '<!--\n\x60\x60\x60\n-->\n\n'
                                                '| Unidad | Estado |\n|---|---|\n| R17 | x |\n',
        })

    def test_backticks_do_not_protect_closing_marker_inside_active_comment(self):
        self.assertClean({
            'AGENTS.md': '<!--\n\x60-->\x60\n\n[real](docs/real.md)\n',
            'docs/real.md': '# Real\n',
            'docs/agent/CONTEXT.md': '[Roadmap](../specs/mcp-roadmap/README.md) R17\n',
            'docs/specs/mcp-roadmap/README.md': '<!--\n\x60-->\x60\n\n'
                                                '| Unidad | Estado |\n|---|---|\n| R17 | x |\n',
        })

    def test_comment_marker_inside_inline_code_is_not_a_comment(self):
        self.assertClean({'docs/agent/CONTEXT.md': 'Usa `<!--` para comentar. [Roadmap](../specs/mcp-roadmap/README.md)\n'})

    def test_only_files_directly_in_docs_agent_are_entry_points(self):
        self.assertFinds({
            'plugin/docs/agent/X.md': '[h](../../../docs/h.md)\n',
            'docs/agent/sub/Y.md': '[h](../../h.md)\n',
            'docs/h.md': '#\n',
        }, ['docs/agent/sub/Y.md:1: ORPHAN: not reachable from README.md, AGENTS.md or docs/agent/*.md',
            'docs/h.md:1: ORPHAN: not reachable from README.md, AGENTS.md or docs/agent/*.md'])

    def test_untracked_documents_are_checked_in_a_git_checkout(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, text in {**BASE, 'docs/nuevo.md': 'Depende de R98.\n'}.items():
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text(text, encoding='utf-8')
            (root / '.gitignore').write_text('ignorado.md\n', encoding='utf-8')
            (root / 'ignorado.md').write_text('[x](docs/nuevo.md)\n', encoding='utf-8')
            git = lambda *a: subprocess.run(['git', *a], cwd=root, capture_output=True, check=True)
            git('init', '-q')
            git('add', 'README.md')
            result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--root', str(root)],
                                    capture_output=True, encoding='utf-8')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            'docs/nuevo.md:1: ORPHAN: not reachable from README.md, AGENTS.md or docs/agent/*.md',
            'docs/nuevo.md:1: UNDEFINED_ID: R98 has no recognised definition'])

    def test_gfm_table_variants_define_ids(self):
        self.assertClean({
            'docs/agent/CONTEXT.md': '[Roadmap](../specs/mcp-roadmap/README.md) R14 R15 R16\n',
            'docs/specs/mcp-roadmap/README.md': textwrap.dedent('''\
                | Unidad | Estado |
                |-|-|
                | R14 | x \\| y |

                Unidad | Estado
                :--|--:
                R15 | x
                | R16 | sin barra final
                '''),
        })

    def test_a_fence_ends_a_definition_table(self):
        self.assertFinds({
            'docs/agent/CONTEXT.md': '[Roadmap](../specs/mcp-roadmap/README.md) R17\n',
            'docs/specs/mcp-roadmap/README.md': textwrap.dedent('''\
                | Unidad | Estado |
                |---|---|
                | R02 | x |
                ```
                código
                ```
                | R17 | después del bloque |
                '''),
        }, ['docs/agent/CONTEXT.md:1: UNDEFINED_ID: R17 has no recognised definition',
            'docs/specs/mcp-roadmap/README.md:7: UNDEFINED_ID: R17 has no recognised definition'])

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

    def test_escapes_empty_destinations_and_label_normalisation(self):
        self.assertClean({
            'docs/agent/CONTEXT.md': textwrap.dedent('''\
                [Roadmap](../specs/mcp-roadmap/README.md)
                [escapado](../a\\(1\\).md) [guía][Plan  MCP] [vacío][self]
                [corchetes](../b\\[1\\].md) [ref corchetes][c]
                \\\\[barra doble](../d.md) \\\\[ref doble][e]

                [plan mcp]: ../plan.md
                [self]: <>
                [c]: ../c\\[2\\].md
                [e]: ../e.md
                '''),
            'docs/a(1).md': '#\n', 'docs/plan.md': '#\n', 'docs/b[1].md': '#\n', 'docs/c[2].md': '#\n',
            'docs/d.md': '#\n', 'docs/e.md': '#\n',
        })

    def test_an_odd_run_of_backslashes_escapes_the_bracket(self):
        orphan = 'not reachable from README.md, AGENTS.md or docs/agent/*.md'
        self.assertFinds({
            'docs/agent/CONTEXT.md': '[Roadmap](../specs/mcp-roadmap/README.md)\n'
                                     '\\\\\\[x](../x.md) \\[y] fin\n\n[y]: ../y.md\n',
            'docs/x.md': '#\n', 'docs/y.md': '#\n',
        }, [f'docs/x.md:1: ORPHAN: {orphan}', f'docs/y.md:1: ORPHAN: {orphan}'])

    def test_an_unclosed_inline_link_is_not_a_link(self):
        orphan = 'not reachable from README.md, AGENTS.md or docs/agent/*.md'
        self.assertFinds({
            'docs/agent/CONTEXT.md': '[Roadmap](../specs/mcp-roadmap/README.md)\n'
                                     '[a](../a.md\n\n[b](../b.md "sin cerrar\n',
            'docs/a.md': '#\n', 'docs/b.md': '#\n',
        }, [f'docs/a.md:1: ORPHAN: {orphan}', f'docs/b.md:1: ORPHAN: {orphan}'])

    def test_a_table_inside_an_html_comment_defines_nothing(self):
        self.assertFinds({
            'docs/agent/CONTEXT.md': '[Roadmap](../specs/mcp-roadmap/README.md) R18 R19 R20 R21\n',
            'docs/specs/mcp-roadmap/README.md': textwrap.dedent('''\
                | Unidad | Estado |
                |---|---|
                | R19 | visible <!-- nota --> |
                | `R20` | usa `<!--` como código |
                | R21 | después del código |

                <!--
                | Unidad | Estado |
                |---|---|
                | R18 | comentada |
                -->
                '''),
        }, ['docs/agent/CONTEXT.md:1: UNDEFINED_ID: R18 has no recognised definition',
            'docs/specs/mcp-roadmap/README.md:10: UNDEFINED_ID: R18 has no recognised definition'])

    def test_definition_table_accepts_delimited_multi_ids_and_rejects_prose(self):
        err = self.assertClean({
            'docs/agent/CONTEXT.md': (
                '[Roadmap](../specs/mcp-roadmap/README.md)\n'
                'R84 R85 R86 R87 R88 R89 R90 R91 R96 R97\n'
            ),
            'docs/specs/mcp-roadmap/README.md': textwrap.dedent('''\
                | Unidad | Estado |
                |---|---|
                | R84, R85 | Planeadas |
                | R86 / R87 | Planeadas |
                | [R88](r88.md), [R89](r89.md) | Planeadas |
                | `R90`, **R91** | Planeadas |
                | **R96, R97** | Planeadas |
                '''),
            'docs/specs/mcp-roadmap/r88.md': '#\n',
            'docs/specs/mcp-roadmap/r89.md': '#\n',
        })
        self.assertIn('defined_by_table=10', err)

        code, lines, err = self.run_guard({
            'docs/agent/CONTEXT.md': (
                '[Roadmap](../specs/mcp-roadmap/README.md)\n'
                'R80 R81 R92 R93 R94 R98\n'
            ),
            'docs/specs/mcp-roadmap/README.md': textwrap.dedent('''\
                | Unidad | Estado |
                |---|---|
                | Reemplaza a R92 | Prosa |
                | R93, nota | Parcial |
                | R98, | Delimitador final |
                | [R80 / R81](r80.md) | Delimitador en texto |
                | [R94](R95-x.md) | URL con otro ID |
                '''),
            'docs/specs/mcp-roadmap/r80.md': '#\n',
            'docs/specs/mcp-roadmap/R95-x.md': '#\n',
        })
        self.assertEqual(code, 1, err)
        self.assertEqual(lines, [
            'docs/agent/CONTEXT.md:2: UNDEFINED_ID: R80 has no recognised definition',
            'docs/agent/CONTEXT.md:2: UNDEFINED_ID: R81 has no recognised definition',
            'docs/agent/CONTEXT.md:2: UNDEFINED_ID: R92 has no recognised definition',
            'docs/agent/CONTEXT.md:2: UNDEFINED_ID: R93 has no recognised definition',
            'docs/agent/CONTEXT.md:2: UNDEFINED_ID: R98 has no recognised definition',
            'docs/specs/mcp-roadmap/README.md:3: UNDEFINED_ID: R92 has no recognised definition',
            'docs/specs/mcp-roadmap/README.md:4: UNDEFINED_ID: R93 has no recognised definition',
            'docs/specs/mcp-roadmap/README.md:5: UNDEFINED_ID: R98 has no recognised definition',
            'docs/specs/mcp-roadmap/README.md:6: UNDEFINED_ID: R80 has no recognised definition',
            'docs/specs/mcp-roadmap/README.md:6: UNDEFINED_ID: R81 has no recognised definition',
            'docs/specs/mcp-roadmap/README.md:7: UNDEFINED_ID: R95 has no recognised definition',
        ])
        self.assertIn('defined_by_table=1', err)

    def test_definition_table_edge_cases_links_titles_and_tabs(self):
        err = self.assertClean({
            'docs/agent/CONTEXT.md': (
                '[Roadmap](../specs/mcp-roadmap/README.md)\n'
                'R84 R85 R86 R87 R88 R89 R90 R91 R92\n'
            ),
            'docs/specs/mcp-roadmap/README.md': (
                '| Unidad | Estado |\n'
                '|---|---|\n'
                '| [R84](https://example.org/a[b), R85 | Destino con corchete |\n'
                '| [R86](r86.md "phase (") | Título con paréntesis |\n'
                '| [R87](r87.md "phase ("), R88 | Multi-ID con título |\n'
                '| [R89](<r89.md>), R90 | Destino en ángulos |\n'
                '| R91,\tR92 | Tab después de coma |\n'
            ),
            'docs/specs/mcp-roadmap/r86.md': '#\n',
            'docs/specs/mcp-roadmap/r87.md': '#\n',
            'docs/specs/mcp-roadmap/r89.md': '#\n',
        })
        self.assertIn('defined_by_table=9', err)

        code, lines, err = self.run_guard({
            'docs/agent/CONTEXT.md': (
                '[Roadmap](../specs/mcp-roadmap/README.md)\n'
                'R93 R94 R95 R96 R97 R98 R99\n'
            ),
            'docs/specs/mcp-roadmap/README.md': (
                '| Unidad | Estado |\n'
                '|---|---|\n'
                '| R93,\t, R94 | Ítem vacío con tab interior |\n'
                '| R95,\t* | Ítem vacío con tab y énfasis |\n'
                '| [R96](https://example.org/x "unclosed) | Título sin cerrar |\n'
                '| [R97](https://example.org/x (phase (1)) | Paréntesis sin escapar en título |\n'
                '| [R98](https://example.org/x) extra | Texto extra tras enlace |\n'
                '| [R99](<https://example.org/x>"title") | Título sin espacio tras destino |\n'
            ),
        })
        self.assertEqual(code, 1, err)
        self.assertEqual(lines, [
            'docs/agent/CONTEXT.md:2: UNDEFINED_ID: R93 has no recognised definition',
            'docs/agent/CONTEXT.md:2: UNDEFINED_ID: R94 has no recognised definition',
            'docs/agent/CONTEXT.md:2: UNDEFINED_ID: R95 has no recognised definition',
            'docs/agent/CONTEXT.md:2: UNDEFINED_ID: R96 has no recognised definition',
            'docs/agent/CONTEXT.md:2: UNDEFINED_ID: R97 has no recognised definition',
            'docs/agent/CONTEXT.md:2: UNDEFINED_ID: R98 has no recognised definition',
            'docs/agent/CONTEXT.md:2: UNDEFINED_ID: R99 has no recognised definition',
            'docs/specs/mcp-roadmap/README.md:3: UNDEFINED_ID: R93 has no recognised definition',
            'docs/specs/mcp-roadmap/README.md:3: UNDEFINED_ID: R94 has no recognised definition',
            'docs/specs/mcp-roadmap/README.md:4: UNDEFINED_ID: R95 has no recognised definition',
            'docs/specs/mcp-roadmap/README.md:5: UNDEFINED_ID: R96 has no recognised definition',
            'docs/specs/mcp-roadmap/README.md:6: UNDEFINED_ID: R97 has no recognised definition',
            'docs/specs/mcp-roadmap/README.md:7: UNDEFINED_ID: R98 has no recognised definition',
            'docs/specs/mcp-roadmap/README.md:8: UNDEFINED_ID: R99 has no recognised definition',
        ])
        self.assertIn('defined_by_table=0', err)

    def test_invalid_datos_json_exits_2(self):
        for payload in (b'{', b'\xff\xfe'):
            with self.subTest(payload=payload):
                code, _, err = self.run_guard({
                    'docs/agent/CONTEXT.md': '# OK\n',
                    'docs/specs/mcp-roadmap/README.md': '| Unidad |\n|---|\n',
                }, raw={'board/src/demo/datos.json': payload})
                self.assertEqual(code, 2, err)
                self.assertIn('cannot read ID sources:', err)


if __name__ == '__main__':
    unittest.main()
