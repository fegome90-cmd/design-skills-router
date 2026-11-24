"""R02A behavior through the built CLI and a real MCP stdio client."""
import asyncio
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import design_skills_router

# The synthetic G5 source pins are checkout fixtures, not distribution data.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'plugin' / 'tests'))
import test_node_context as fixture

ENV = 'DESIGN_ROUTER_DISABLED_TOOLS'
NAMES = {'next_node', 'open_node', 'search_context', 'submit_evidence'}


@unittest.skipUnless(importlib.util.find_spec('mcp'), 'Install the MCP extra')
class InstalledOperationPolicyTests(unittest.TestCase):
    def setUp(self):
        case = fixture.NodeContextTests('test_phase_routes_before_authorizing_context')
        case.setUpClass()
        case.setUp()
        self.addCleanup(case.doCleanups)
        self.case = case
        self.proposal = case.prepare_case()
        case.pin_test_sources()
        case.grant(['analyze', 'draft'])
        self.work = case.ledger.parent.resolve()
        case.ledger = self.work / 'fixture.json'
        self.cli_state = self.work / 'cli.json'
        self.mcp_state = self.work / 'mcp.json'
        for state in (self.cli_state, self.mcp_state):
            case.runtime.save_state(state, case.state, None)

        # Exercise the installed implementation in a disposable copy. The
        # only changed bytes are the synthetic fixture's source-pin contract.
        installed = Path(design_skills_router.__file__).resolve().parent
        package = self.work / 'installed-copy' / installed.name
        shutil.copytree(installed, package)
        (package / '_portable/skills/design-tree/references/contracts.json').write_text(
            json.dumps(case.router.contracts), encoding='utf-8')
        self.launch = ['-B', '-c', f'import sys; sys.path.insert(0, {str(package.parent)!r}); '
                       'from design_skills_router.cli import app; app()']

    def cli(self, *args, policy='', error=None, raw=False):
        env = {**os.environ, ENV: policy}
        proc = subprocess.run([sys.executable, *self.launch, '--state', str(self.cli_state), *args],
                              cwd=self.work, capture_output=True, encoding='utf-8', env=env,
                              stdin=subprocess.DEVNULL, timeout=30)
        if error:
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            self.assertEqual(proc.stdout, '')
            self.assertIn(error, proc.stderr)
            return
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stderr, '')
        return proc.stdout if raw else json.loads(proc.stdout)

    def server(self, policy=''):
        from mcp import StdioServerParameters
        return StdioServerParameters(command=sys.executable,
                                     args=[*self.launch, '--state', str(self.mcp_state), 'mcp'],
                                     env={ENV: policy}, cwd=str(self.work))

    @staticmethod
    def snapshots(*ledgers):
        paths = [p for ledger in ledgers for p in
                 (ledger, ledger.with_name(ledger.name + '.context.sqlite3'))]
        return tuple(p.read_bytes() if p.exists() else None for p in paths)

    async def call(self, client, name, *, error=None, **args):
        result = await asyncio.wait_for(client.call_tool(name, args), timeout=30)
        if error:
            self.assertTrue(result.isError, result.content)
            self.assertIn(error, result.content[0].text)
        else:
            self.assertFalse(result.isError, result.content)
            return result.structuredContent

    def test_search_denied_without_index_or_ledger_mutation(self):
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client
        policy = 'search_context'
        node = fixture.NODE

        async def exercise():
            async with stdio_client(self.server(policy)) as (read, write), ClientSession(read, write) as client:
                await asyncio.wait_for(client.initialize(), timeout=30)
                listed = await asyncio.wait_for(client.list_tools(), timeout=30)
                self.assertEqual({tool.name for tool in listed.tools}, NAMES - {policy})
                next_step = self.cli('context-next', policy=policy)
                self.assertEqual(next_step, await self.call(client, 'next_node'))
                self.assertIn(node, next_step['context_nodes'])

                async def assert_denied():
                    before = self.snapshots(self.cli_state, self.mcp_state)
                    self.cli('context-search', node, '--query', 'jerarquía',
                             policy=policy, error='TOOL_DISABLED:search_context')
                    await self.call(client, 'search_context', node_id=node,
                                    query='jerarquía', error='search_context')
                    self.assertEqual(self.snapshots(self.cli_state, self.mcp_state), before)

                await assert_denied()
                packet = self.cli('context-open', node, policy=policy)
                self.assertEqual(packet, await self.call(client, 'open_node', node_id=node))
                self.assertEqual(len(packet['required_sections']), 5)
                self.assertTrue(all(s is not None for s in self.snapshots(self.cli_state, self.mcp_state)))
                await assert_denied()

        asyncio.run(exercise())

    def test_unrestricted_catalog_metadata_and_four_operations(self):
        from mcp import ClientSession
        from mcp.client.stdio import stdio_client
        node = fixture.NODE

        async def exercise():
            async with stdio_client(self.server()) as (read, write), ClientSession(read, write) as client:
                await asyncio.wait_for(client.initialize(), timeout=30)
                listed = await asyncio.wait_for(client.list_tools(), timeout=30)
                tools = {tool.name: tool for tool in listed.tools}
                self.assertEqual(set(tools), NAMES)
                expected = {
                    'next_node': ({}, 'orientation', []),
                    'open_node': ({'node_id': 'string'}, 'analyze', ['context_packet', 'derived_index']),
                    'search_context': ({'node_id': 'string', 'query': 'string'}, 'analyze', ['derived_index']),
                    'submit_evidence': ({'node_id': 'string', 'expected_revision': 'integer',
                                         'proposal': 'object'}, 'draft', ['pending_proposal']),
                }
                for name, (fields, action, mutation) in expected.items():
                    tool = tools[name]
                    self.assertEqual(set(tool.inputSchema.get('required', [])), set(fields))
                    self.assertEqual({k: v.get('type') for k, v in tool.inputSchema.get('properties', {}).items()}, fields)
                    self.assertEqual(tool.annotations.readOnlyHint, not mutation)
                    self.assertEqual(tool.meta['design-router/action'], action)
                    self.assertEqual(tool.meta['design-router/mutation'], mutation)
                    self.assertIn('ledger:read', tool.meta['design-router/capabilities'])

                self.assertEqual(self.cli('context-next'), await self.call(client, 'next_node'))
                packet = self.cli('context-open', node)
                self.assertEqual(packet, await self.call(client, 'open_node', node_id=node))
                self.assertEqual(len(packet['required_sections']), 5)
                search = self.cli('context-search', node, '--query', 'jerarquía')
                self.assertEqual(search, await self.call(client, 'search_context', node_id=node, query='jerarquía'))
                self.assertTrue(search['matches'])
                self.case.attach_application(self.proposal, packet)
                proposal = self.work / 'proposal.json'
                proposal.write_text(json.dumps(self.proposal), encoding='utf-8')
                before = self.snapshots(self.cli_state, self.mcp_state)
                self.cli('propose', node, '--file', str(proposal), policy='submit_evidence',
                         error='TOOL_DISABLED:submit_evidence')
                self.assertEqual(self.snapshots(self.cli_state, self.mcp_state), before)
                submitted = self.cli('propose', node, '--file', str(proposal))
                self.assertEqual(submitted, await self.call(client, 'submit_evidence', node_id=node,
                                 expected_revision=packet['revision'], proposal=self.proposal))
                self.assertEqual(submitted['state'], 'AWAITING_HUMAN')
                for ledger in (self.cli_state, self.mcp_state):
                    self.assertEqual(self.case.runtime.load_state(ledger)['records'][node]['status'], 'AWAITING_HUMAN')

        asyncio.run(exercise())

    def test_invalid_policy_rejected_by_both_entrypoints(self):
        before = self.snapshots(self.cli_state, self.mcp_state)
        for policy in ('missing_tool', 'search_context,,open_node', '*'):
            with self.subTest(policy=policy):
                self.cli('context-next', policy=policy, error='INVALID_TOOL_POLICY')
                self.cli('mcp', policy=policy, error='INVALID_TOOL_POLICY')
        self.assertEqual(self.snapshots(self.cli_state, self.mcp_state), before)
