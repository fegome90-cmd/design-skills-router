"""Check the installed CLI and MCP against the same synthetic G5 contract."""

import asyncio
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import design_skills_router

# This is a checkout-level integration test. The synthetic pinned-source
# fixtures belong to the existing plugin tests, not to the distribution.
PLUGIN_TESTS = Path(__file__).resolve().parents[3] / 'plugin' / 'tests'
sys.path.insert(0, str(PLUGIN_TESTS))
import test_node_context as context_fixture


@unittest.skipUnless(importlib.util.find_spec('mcp'), 'Install the optional MCP SDK')
class InstalledMcpParityTests(unittest.TestCase):
    def test_g5_contract_through_installed_cli_and_stdio(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        case = context_fixture.NodeContextTests('test_phase_routes_before_authorizing_context')
        case.setUpClass()
        case.setUp()
        self.addCleanup(case.doCleanups)
        node = context_fixture.NODE
        proposal = case.prepare_case()
        original_contracts = copy.deepcopy(case.router.contracts)
        case.pin_test_sources()
        case.grant(['analyze'])

        work = case.ledger.parent.resolve()
        cli_ledger = work / 'cli.json'
        mcp_ledger = work / 'mcp.json'
        for ledger in (cli_ledger, mcp_ledger):
            case.runtime.save_state(ledger, case.state, None)

        # Copy the installed package. Replace only the reviewed source pins in
        # the copy, using the existing synthetic fixture. Never edit the
        # installation or the canonical tree.
        installed = Path(design_skills_router.__file__).resolve().parent
        package = work / 'installed-copy' / installed.name
        shutil.copytree(installed, package)
        contracts = package / '_portable/skills/design-tree/references/contracts.json'
        installed_contracts = json.loads(contracts.read_text(encoding='utf-8'))
        self.assertEqual(installed_contracts, original_contracts,
                         'Installed contracts differ from the checkout before fixture adaptation')
        for skill in case.runtime.node_context.SKILL_SECTIONS:
            installed_contracts['source_reviews'][skill]['git_blob'] = (
                case.router.contracts['source_reviews'][skill]['git_blob']
            )
        self.assertEqual(installed_contracts, case.router.contracts)
        contracts.write_text(json.dumps(installed_contracts), encoding='utf-8')
        launch = [
            '-B', '-c',
            f'import sys; sys.path.insert(0, {str(package.parent)!r}); '
            'from design_skills_router.cli import app; app()',
        ]

        def ledger_bytes():
            return [p.read_bytes() for p in (cli_ledger, mcp_ledger)]

        def cli(*args, error=None):
            before_rejection = ledger_bytes() if error is not None else None
            result = subprocess.run(
                [sys.executable, *launch, '--state', str(cli_ledger), *args],
                cwd=work, capture_output=True, encoding='utf-8', timeout=30,
            )
            if error is not None:
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(result.stdout, '')
                self.assertIn(error, json.loads(result.stderr)['error'])
                self.assertEqual(ledger_bytes(), before_rejection)
                return
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stderr, '')
            return json.loads(result.stdout)

        def write_proposal(value):
            path = work / 'proposal.json'
            path.write_text(json.dumps(value), encoding='utf-8')
            return str(path)

        server = StdioServerParameters(
            command=sys.executable,
            args=[*launch, '--state', str(mcp_ledger), 'mcp'],
            cwd=str(work),
        )

        async def exercise():
            async with stdio_client(server) as (read, write), ClientSession(read, write) as client:
                async def call(name, error=None, **args):
                    before_rejection = ledger_bytes() if error is not None else None
                    result = await asyncio.wait_for(client.call_tool(name, args), timeout=30)
                    if error is not None:
                        self.assertTrue(result.isError, result.content)
                        self.assertIn(error, result.content[0].text)
                        self.assertEqual(ledger_bytes(), before_rejection)
                        return
                    self.assertFalse(result.isError, result.content)
                    return result.structuredContent

                await asyncio.wait_for(client.initialize(), timeout=30)
                listed = await asyncio.wait_for(client.list_tools(), timeout=30)
                expected = {
                    'next_node': {},
                    'open_node': {'node_id': 'string'},
                    'search_context': {'node_id': 'string', 'query': 'string'},
                    'submit_evidence': {'node_id': 'string', 'expected_revision': 'integer',
                                        'proposal': 'object'},
                }
                self.assertEqual({tool.name for tool in listed.tools}, set(expected))
                self.assertEqual(len(listed.tools), len(expected))
                for tool in listed.tools:
                    with self.subTest(tool=tool.name):
                        schema = tool.inputSchema
                        self.assertEqual(set(schema.get('required', [])), set(expected[tool.name]))
                        self.assertEqual(
                            {key: value.get('type') for key, value in schema.get('properties', {}).items()},
                            expected[tool.name],
                        )

                first = cli('context-next')
                self.assertEqual(first, await call('next_node'))
                self.assertIn(node, first['context_nodes'])
                self.assertEqual(first['active_phase'], context_fixture.PHASE)
                cli('context-open', 'LAY01', error='CONTEXT_NODE_OUTSIDE_PILOT')
                await call('open_node', node_id='LAY01', error='CONTEXT_NODE_OUTSIDE_PILOT')

                packet = cli('context-open', node)
                self.assertEqual(packet, await call('open_node', node_id=node))
                self.assertEqual(len(packet['required_sections']), 5)
                self.assertEqual(packet['revision'], first['revision'] + 1)
                before = [p.read_bytes() for p in (cli_ledger, mcp_ledger)]
                self.assertEqual(cli('context-open', node), await call('open_node', node_id=node))
                self.assertEqual([p.read_bytes() for p in (cli_ledger, mcp_ledger)], before)

                query = 'jerarquía'
                search = cli('context-search', node, '--query', query)
                self.assertEqual(len(search['matches']), 2)
                self.assertTrue(all(row['title'] == 'Example' for row in search['matches']))
                self.assertEqual(search, await call('search_context', node_id=node, query=query))
                indexes = [p.with_name(p.name + '.context.sqlite3') for p in (cli_ledger, mcp_ledger)]
                for index in indexes:
                    index.unlink()
                    self.assertFalse(index.exists())
                self.assertEqual(cli('context-search', node, '--query', query), search)
                self.assertTrue(indexes[0].is_file())
                self.assertEqual(await call('search_context', node_id=node, query=query), search)
                self.assertTrue(indexes[1].is_file())
                self.assertEqual([p.read_bytes() for p in (cli_ledger, mcp_ledger)], before)

                case.ledger = work / 'fixture.json'
                case.attach_application(proposal, packet)
                denied = 'CONTEXT_ACTION_FORBIDDEN:ACTION_NOT_DELEGATED'
                cli('propose', node, '--file', write_proposal(proposal), error=denied)
                await call('submit_evidence', node_id=node, expected_revision=packet['revision'],
                           proposal=proposal, error=denied)
                self.assertEqual([p.read_bytes() for p in (cli_ledger, mcp_ledger)], before)

                # Install the same new mandate only after verifying parity.
                self.assertEqual(cli_ledger.read_bytes(), mcp_ledger.read_bytes())
                case.state = case.runtime.load_state(cli_ledger)
                case.grant(['analyze', 'draft'])
                for ledger in (cli_ledger, mcp_ledger):
                    case.runtime.save_state(ledger, case.state, packet['revision'])
                packet = cli('context-open', node)
                self.assertEqual(packet, await call('open_node', node_id=node))
                case.attach_application(proposal, packet)
                revision = packet['revision']
                before = [p.read_bytes() for p in (cli_ledger, mcp_ledger)]
                incomplete = copy.deepcopy(proposal)
                incomplete['criterion_reviews'][0]['section_ids'].pop()
                missing = 'CONTEXT_APPLICATION_REQUIRED:layout'
                cli('propose', node, '--file', write_proposal(incomplete), error=missing)
                await call('submit_evidence', node_id=node, expected_revision=revision,
                           proposal=incomplete, error=missing)

                # These are deliberate MCP-specific boundary restrictions.
                await call('submit_evidence', node_id='LAY01', expected_revision=revision,
                           proposal=proposal, error='CONTEXT_NODE_OUTSIDE_PILOT')
                await call('submit_evidence', node_id=node, expected_revision=revision - 1,
                           proposal=proposal, error='STATE_REVISION_CONFLICT')
                outside = copy.deepcopy(proposal)
                outside['evidence'][0]['path'] = str(work / 'outside.png')
                await call('submit_evidence', node_id=node, expected_revision=revision,
                           proposal=outside, error='MCP_EVIDENCE_OUTSIDE_PROJECT')
                self.assertEqual([p.read_bytes() for p in (cli_ledger, mcp_ledger)], before)

                cli_result = cli('propose', node, '--file', write_proposal(proposal))
                mcp_result = await call('submit_evidence', node_id=node, expected_revision=revision,
                                        proposal=proposal)
                self.assertEqual(cli_result, mcp_result)
                self.assertEqual(cli_result['state'], 'AWAITING_HUMAN')
                self.assertEqual(cli_result['revision'], revision + 1)
                self.assertEqual(cli('context-next'), await call('next_node'))
                final_states = []
                for ledger in (cli_ledger, mcp_ledger):
                    state = case.runtime.load_state(ledger)
                    record = state['records'][node]
                    self.assertEqual(record['status'], 'AWAITING_HUMAN')
                    self.assertEqual(record['authority']['decided_by'], 'human')
                    # Only the timestamps generated by the two independent submissions differ.
                    record.pop('submitted_at')
                    event = state['history'][-1]
                    self.assertEqual((event['event'], event['node_id']), ('proposal', node))
                    event.pop('at')
                    final_states.append(state)
                self.assertEqual(*final_states)

        asyncio.run(exercise())
