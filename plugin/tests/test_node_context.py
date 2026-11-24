"""Behavioral checks against the canonical audit node and a temporary SQLite index."""
import asyncio
import copy
import hashlib
import importlib.util
from pathlib import Path
import struct
import sys
import unittest
import zlib

import test_runner as fixtures


NODE = 'E05__LAY01'
PHASE = 'mobile-layout'
LAYOUT_SKILL = 'jakubkrehel/skills/better-layout'
LAYOUT_TITLES = (
    'Group with space, not lines',
    'Hold structure until it breaks',
    'Plan for growth and clipping',
    'Reporting',
)


def png(image_data=None):
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))

    if image_data is None:
        image_data = zlib.compress(b'\0\xff\xff\xff')
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', image_data) + chunk(b'IEND', b''))


class NodeContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.RunnerTests.setUpClass()

    def setUp(self):
        self.fixture = fixtures.RunnerTests(methodName='test_root_only_initially')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.runtime = self.fixture.r
        self.router = self.runtime.Router()
        self.fixture.router = self.router
        self.state = self.router.new_state('finanzas-fixture', 'web', 'audit', 'Resumen móvil', context_pilot=True)
        self.fixture.state = self.state
        self.index = self.fixture.work / 'context.sqlite3'
        self.ledger = self.fixture.work / 'ledger.json'

    def prepare_case(self):
        path = ['Q00', 'E01', 'E02', 'E05', 'E05__F00', 'E05__D00', 'E05__D10', 'E05__L00']
        for current, following in zip(path, path[1:] + [NODE]):
            chosen = following if self.router.node(current)['kind'] == 'decision' else None
            self.fixture.complete(current, chosen)
        config = {'schema': 'design-tree-phases/1', 'project_kind': 'bounded', 'phases': [{
            'id': PHASE, 'family': 'visual', 'revision': 1, 'dependency_ids': [],
            'node_instance_ids': [NODE, *(f'{NODE}_{i}' for i in range(1, 4))],
            'deliverables': ['Anotaciones de jerarquía'],
        }]}
        self.router.configure_phases(self.state, config, self.fixture.receipt(self.runtime.digest(config), 'phase_map'))
        self.grant()
        self.fixture.approve_structure(NODE)
        proposal = self.fixture.proposal(NODE, f'{NODE}_2')
        return proposal

    def grant(self, actions=None):
        grant = self.router.grant_template(self.state, PHASE, 'guided')
        if actions is not None:
            grant['allowed_actions'] = actions
        self.router.grant_assistance(self.state, grant,
                                    self.fixture.receipt(self.router.grant_hash(self.state, grant), 'delegation'))

    def pin_test_sources(self, *, metadata_only=False, omitted_title=None):
        for skill, title in self.runtime.node_context.SKILL_SECTIONS.items():
            source = self.state['sources'][skill]
            path = Path(source['path'])
            head = f'---\ndescription: {title}\n---\n'
            titles = LAYOUT_TITLES if skill == LAYOUT_SKILL else (title,)
            body = ''.join(f'## {name}\n\nObserva la jerarquía y el orden en móvil.\n\n'
                           for name in titles if name != omitted_title)
            body += '## Example\n\nAjusta la jerarquía.\n'
            raw = (head if metadata_only else head + body).encode()
            path.write_bytes(raw)
            blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            self.router.contracts['source_reviews'][skill]['git_blob'] = blob
            self.router.register_source(self.state, skill, path, source['commit'], blob, source['source_ref'])

    def attach_application(self, proposal, packet):
        capture = self.fixture.work / 'mobile.png'
        capture.write_bytes(png())
        proposal['context_id'] = packet['context_id']
        proposal['evidence'] = [{'path': str(capture), 'sha256': hashlib.sha256(capture.read_bytes()).hexdigest(),
                                 'note': 'Fixture capture for explicit application'}]
        section_ids = packet['section_ids']
        for review in proposal['skill_reviews'] + proposal['criterion_reviews']:
            review.update(observation='The filter dominates the total.', evidence_refs=[str(capture)])
            if 'skill_id' in review:
                review['section_id'] = section_ids['skills'][review['skill_id']]
            else:
                review['section_ids'] = list(section_ids['criteria'][review['rule_id']])
        return capture

    def test_phase_routes_before_authorizing_context(self):
        self.assertEqual(self.router.context_next(self.state)['pending_nodes'], ['Q00'])
        with self.assertRaisesRegex(self.runtime.GateError, 'NODE_NOT_ACTIVE'):
            self.router.open_context(self.state, NODE, self.index)
        self.prepare_case()
        result = self.router.context_next(self.state)
        self.assertEqual(result['active_phase'], PHASE)
        self.assertEqual(result['context_nodes'], [NODE])
        with self.assertRaisesRegex(self.runtime.GateError, 'OUTSIDE_PILOT'):
            self.router.open_context(self.state, 'LAY01', self.index)

    def test_wrong_blob_and_frontmatter_are_blocked(self):
        self.prepare_case()
        with self.assertRaisesRegex(self.runtime.GateError, 'SOURCE_PIN_MISMATCH'):
            self.router.open_context(self.state, NODE, self.index)
        self.pin_test_sources(metadata_only=True)
        with self.assertRaisesRegex(self.runtime.GateError, 'SECTION_MISSING'):
            self.router.open_context(self.state, NODE, self.index)
        self.assertFalse(self.index.exists())

    def test_packet_covers_exactly_the_sections_declared_for_layout(self):
        self.prepare_case()
        self.pin_test_sources()
        packet = self.router.open_context(self.state, NODE, self.index)
        expected = [f'{LAYOUT_SKILL}#{title}' for title in LAYOUT_TITLES]
        self.assertEqual(packet['section_ids']['criteria']['layout'], expected)
        bodies = {section['id']: section['body'] for section in packet['required_sections']}
        self.assertEqual(len(bodies), 5)
        self.assertTrue(all(bodies[section_id].startswith('Observa') for section_id in expected))

    def test_omitting_a_rule_section_blocks_open(self):
        self.prepare_case()
        self.pin_test_sources(omitted_title='Reporting')
        with self.assertRaisesRegex(self.runtime.GateError, 'SECTION_MISSING_OR_AMBIGUOUS:.*#Reporting'):
            self.router.open_context(self.state, NODE, self.index)
        self.assertEqual(self.state['context_packets'], {})

    def test_old_packet_must_be_reopened_to_submit(self):
        proposal = self.prepare_case()
        self.pin_test_sources()
        packet = self.router.open_context(self.state, NODE, self.index)
        self.attach_application(proposal, packet)
        old_binding = self.state['context_packets'][NODE]
        old_binding.pop('criteria_sections')
        proposal['context_id'] = self.runtime.digest(old_binding)
        with self.assertRaisesRegex(self.runtime.GateError, 'PACKET_REOPEN_REQUIRED'):
            self.router.propose(self.state, NODE, proposal)
        reopened = self.router.open_context(self.state, NODE, self.index)
        self.assertEqual(reopened, packet)

    def test_phase_authorization_applies_to_analysis_and_drafting(self):
        proposal = self.prepare_case()
        self.pin_test_sources()
        self.grant(['test'])
        self.assertEqual(self.router.context_next(self.state)['context_nodes'], [])
        with self.assertRaisesRegex(self.runtime.GateError, 'ACTION_NOT_DELEGATED'):
            self.router.open_context(self.state, NODE, self.index)
        self.grant(['analyze'])
        packet = self.router.open_context(self.state, NODE, self.index)
        self.attach_application(proposal, packet)
        with self.assertRaisesRegex(self.runtime.GateError, 'ACTION_NOT_DELEGATED'):
            self.router.propose(self.state, NODE, proposal)

    def test_updated_reviewed_pin_invalidates_the_packet(self):
        proposal = self.prepare_case()
        self.pin_test_sources()
        packet = self.router.open_context(self.state, NODE, self.index)
        self.attach_application(proposal, packet)
        skill = next(iter(self.runtime.node_context.SKILL_SECTIONS))
        self.router.contracts['source_reviews'][skill]['git_blob'] = 'f' * 40
        with self.assertRaisesRegex(self.runtime.GateError, 'PACKET_STALE'):
            self.router.validate_proposal(self.state, NODE, proposal)

    def test_search_is_repeatable_and_cannot_prepare_a_packet(self):
        self.prepare_case()
        self.pin_test_sources()
        hits = self.router.open_context(self.state, NODE, self.index, query='jerarquia')
        self.assertEqual(len(hits['matches']), 2)
        self.assertTrue(all(row['title'] == 'Example' for row in hits['matches']))
        self.assertEqual(self.state['context_packets'], {})
        packet = self.router.open_context(self.state, NODE, self.index)
        self.assertEqual(hits['context_id'], packet['context_id'])
        self.assertEqual(self.router.open_context(self.state, NODE, self.index), packet)
        self.assertEqual(len(packet['required_sections']), 5)
        self.assertTrue(all(row['body'].startswith('Observa') for row in packet['required_sections']))

    def test_gate_binds_application_to_project_evidence_and_persists_without_index(self):
        proposal = self.prepare_case()
        self.pin_test_sources()
        with self.assertRaisesRegex(self.runtime.GateError, 'PACKET_REQUIRED'):
            self.router.propose(self.state, NODE, proposal)
        packet = self.router.open_context(self.state, NODE, self.index)
        proposal['context_id'] = packet['context_id']
        with self.assertRaisesRegex(self.runtime.GateError, 'CAPTURE_REQUIRED'):
            self.router.propose(self.state, NODE, proposal)
        capture = self.attach_application(proposal, packet)
        for incomplete in [png()[:33], png(b'corrupt compressed stream')]:
            capture.write_bytes(incomplete)
            proposal['evidence'][0]['sha256'] = hashlib.sha256(incomplete).hexdigest()
            with self.assertRaisesRegex(self.runtime.GateError, 'CAPTURE_REQUIRED'):
                self.router.propose(self.state, NODE, proposal)
        self.attach_application(proposal, packet)
        incorrect = copy.deepcopy(proposal)
        incorrect['criterion_reviews'][0]['section_ids'].pop()
        with self.assertRaisesRegex(self.runtime.GateError, 'APPLICATION_REQUIRED'):
            self.router.propose(self.state, NODE, incorrect)
        proposal_hash = self.router.propose(self.state, NODE, proposal)
        self.assertIn(NODE, self.router.context_next(self.state)['awaiting_human'])
        with self.assertRaisesRegex(self.runtime.GateError, 'AWAITING_HUMAN'):
            self.router.open_context(self.state, NODE, self.index)
        with self.assertRaisesRegex(self.runtime.GateError, 'AWAITING_HUMAN'):
            self.router.propose(self.state, NODE, proposal)
        self.router.confirm_decision(self.state, NODE, self.fixture.receipt(proposal_hash, 'project'))
        with self.assertRaisesRegex(self.runtime.GateError, 'ALREADY_DECIDED'):
            self.router.propose(self.state, NODE, proposal)
        self.assertIn(f'{NODE}_2', self.router.frontier(self.state))
        self.runtime.save_state(self.ledger, self.state, None)
        self.index.unlink()
        resumed = self.runtime.load_state(self.ledger)
        self.assertTrue(self.router.record_current(resumed, NODE))
        capture.write_bytes(b'changed project evidence')
        self.assertFalse(self.router.record_current(resumed, NODE))

    def test_reopened_or_changed_context_rejects_old_package(self):
        proposal = self.prepare_case()
        self.pin_test_sources()
        packet = self.router.open_context(self.state, NODE, self.index)
        self.attach_application(proposal, packet)
        self.grant()
        with self.assertRaisesRegex(self.runtime.GateError, 'GRANT_STALE'):
            self.router.propose(self.state, NODE, proposal)
        self.state['scope'] = 'Different screen'
        with self.assertRaisesRegex(self.runtime.GateError, 'PACKET_STALE'):
            self.router.validate_proposal(self.state, NODE, proposal)

    @unittest.skipUnless(importlib.util.find_spec('mcp'), 'Install the optional MCP SDK for stdio checks')
    def test_stdio_returns_current_phase_and_reports_wrong_node(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        self.prepare_case()
        self.runtime.save_state(self.ledger, self.state, None)
        server = StdioServerParameters(command=sys.executable,
                                       args=['-B', str(fixtures.SCRIPTS / 'mcp_server.py'), '--state', str(self.ledger)])

        async def run():
            async with stdio_client(server) as (read, write), ClientSession(read, write) as client:
                await client.initialize()
                tools = await client.list_tools()
                self.assertEqual({tool.name for tool in tools.tools},
                                 {'next_node', 'open_node', 'search_context', 'submit_evidence'})
                result = await client.call_tool('next_node', {})
                self.assertFalse(result.isError)
                self.assertEqual(result.structuredContent['active_phase'], PHASE)
                result = await client.call_tool('open_node', {'node_id': 'LAY01'})
                self.assertTrue(result.isError)
                self.assertIn('OUTSIDE_PILOT', result.content[0].text)

        asyncio.run(run())
