"""Behavioral checks against the canonical audit node and a temporary SQLite index."""
import asyncio
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import struct
import sys
import unittest
from unittest.mock import patch
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


def png(image_data=None, *, depth=8, color=2, chunks=None):
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))

    if chunks is None:
        if image_data is None:
            image_data = zlib.compress(b'\0\xff\xff\xff')
        chunks = [(b'IDAT', image_data)]
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, depth, color, 0, 0, 0))
            + b''.join(chunk(kind, body) for kind, body in chunks) + chunk(b'IEND', b''))


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
        capture = self.ledger.parent / 'evidence' / 'mobile.png'
        capture.parent.mkdir(exist_ok=True)
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

    def prepare_legacy_record(self, *, delegated=False):
        proposal = self.prepare_case()
        self.pin_test_sources()
        packet = self.router.open_context(self.state, NODE, self.index)
        self.attach_application(proposal, packet)
        self.router.propose(self.state, NODE, proposal)
        record = self.state['records'][NODE]
        record.pop('context_packet', None)
        old_packet = self.state['context_packets'][NODE]
        old_packet.pop('criteria_sections')
        record['proposal']['context_id'] = self.runtime.digest(old_packet)
        criterion = record['proposal']['criterion_reviews'][0]
        criterion.pop('section_ids')
        criterion['section_id'] = old_packet['sections'][LAYOUT_SKILL]['id']
        grant = self.state['grants'][self.state['active_grant_id']]
        record['authority'] = {'decided_by': 'agent_delegated', 'grant_id': grant['id'],
                               'grant_hash': grant['authorization_hash']}
        record['binding'] = self.router.binding(self.state, NODE, record['authority'])
        record['proposal_hash'] = self.runtime.digest({'binding': record['binding'], 'proposal': record['proposal']})
        if delegated:
            record['status'] = 'DECIDED_DELEGATED'
        return record

    def test_phase_routes_before_authorizing_context(self):
        self.assertEqual(self.router.context_next(self.state)['pending_nodes'], ['Q00'])
        root_packet = self.router.packet(self.state, 'Q00')
        self.assertNotIn('permissions', root_packet)
        self.assertNotIn('action', root_packet['assistance'])
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

    def test_packet_remains_auditable_after_the_phase_is_reopened(self):
        proposal = self.prepare_case()
        self.pin_test_sources()
        packet = self.router.open_context(self.state, NODE, self.index)
        self.attach_application(proposal, packet)
        proposal_hash = self.router.propose(self.state, NODE, proposal)
        self.router.confirm_decision(self.state, NODE, self.fixture.receipt(proposal_hash, 'project'))
        reason = 'Repeat the audit for a different viewport.'
        target = self.runtime.digest({'phase_id': PHASE, 'gate_packet_hash': None, 'reason': reason})
        self.router.reopen_phase(self.state, PHASE, reason, self.fixture.receipt(target, 'reopen'))
        self.grant()
        reopened = self.router.open_context(self.state, NODE, self.index)
        self.assertNotEqual(reopened['context_id'], packet['context_id'])
        self.runtime.save_state(self.ledger, self.state, None)
        resumed = self.runtime.load_state(self.ledger)
        retired = next(event['record'] for event in resumed['history']
                       if event['event'] == 'decision_retired_by_phase' and event['node_id'] == NODE)
        self.assertEqual(self.runtime.digest(retired['context_packet']), packet['context_id'])

    def test_g5_requires_human_confirmation_under_a_guided_grant(self):
        proposal = self.prepare_case()
        self.pin_test_sources()
        packet = self.router.open_context(self.state, NODE, self.index)
        self.attach_application(proposal, packet)
        proposal_hash = self.router.propose(self.state, NODE, proposal)
        with self.assertRaisesRegex(self.runtime.GateError, 'CONTEXT_HUMAN_CONFIRMATION_REQUIRED'):
            self.router.delegate_decision(self.state, NODE)
        self.assertFalse(packet['packet']['assistance']['allowed'])
        self.assertEqual(packet['packet']['assistance']['required_gate'], 'node')
        self.assertNotIn(f'{NODE}_2', self.router.frontier(self.state))
        self.router.confirm_decision(self.state, NODE, self.fixture.receipt(proposal_hash, 'project'))
        self.assertIn(f'{NODE}_2', self.router.frontier(self.state))

    def test_legacy_provisional_decision_waits_for_human_confirmation(self):
        original = self.prepare_legacy_record(delegated=True)
        self.runtime.save_state(self.ledger, self.state, None)
        state = self.runtime.load_state(self.ledger)
        self.assertIn(NODE, self.router.context_next(state)['awaiting_human'])
        self.assertEqual(self.router.packet(state, NODE)['project_status'], 'AWAITING_HUMAN')
        self.assertNotIn(f'{NODE}_2', self.router.frontier(state))
        with self.assertRaisesRegex(self.runtime.GateError, 'CONTEXT_NODE_AWAITING_HUMAN'):
            self.router.open_context(state, NODE, self.index)
        self.router.confirm_decision(state, NODE, self.fixture.receipt(original['proposal_hash'], 'project'))
        self.assertIn(f'{NODE}_2', self.router.frontier(state))

    def test_legacy_approved_record_retains_original_packet_when_reopened(self):
        original = self.prepare_legacy_record()
        self.router.confirm_decision(self.state, NODE, self.fixture.receipt(original['proposal_hash'], 'project'))
        original.pop('context_packet', None)
        self.assertTrue(self.router.record_current(self.state, NODE))
        reason = 'Repeat under a new authorization.'
        target = self.runtime.digest({'phase_id': PHASE, 'gate_packet_hash': None, 'reason': reason})
        self.router.reopen_phase(self.state, PHASE, reason, self.fixture.receipt(target, 'reopen'))
        self.grant()
        self.router.open_context(self.state, NODE, self.index)
        retired = next(event['record'] for event in self.state['history']
                       if event['event'] == 'decision_retired_by_phase' and event['node_id'] == NODE)
        self.assertEqual(self.runtime.digest(retired['context_packet']), original['proposal']['context_id'])

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

    def test_search_rebuilds_an_incomplete_index_with_the_same_packet(self):
        self.prepare_case()
        self.pin_test_sources()
        packet = self.router.open_context(self.state, NODE, self.index)
        hits = self.router.open_context(self.state, NODE, self.index, query='jerarquia')
        with sqlite3.connect(self.index) as db:
            db.execute('DROP TABLE sections')
        self.assertEqual(self.router.open_context(self.state, NODE, self.index, query='jerarquia'), hits)
        self.assertEqual(self.router.open_context(self.state, NODE, self.index), packet)

    def test_open_rebuilds_same_count_index_with_incorrect_required_rows(self):
        self.prepare_case()
        self.pin_test_sources()
        packet = self.router.open_context(self.state, NODE, self.index)
        section = packet['required_sections'][0]
        changes = {
            'missing-id': ('id', 'other section'),
            'changed-payload': ('payload', json.dumps({**section, 'body': 'Different fixture text.'})),
            'malformed-payload': ('payload', '{'),
        }
        for problem, (column, value) in changes.items():
            with self.subTest(problem=problem):
                index = self.index.with_name(f'{problem}.sqlite3')
                shutil.copyfile(self.index, index)
                with sqlite3.connect(index) as db:
                    db.execute(f'UPDATE sections SET {column} = ? WHERE id = ?', (value, section['id']))
                self.assertEqual(self.router.open_context(self.state, NODE, index), packet)

    def test_gate_validates_png_chunk_types_and_idat_order(self):
        proposal = self.prepare_case()
        self.pin_test_sources()
        packet = self.router.open_context(self.state, NODE, self.index)
        capture = self.attach_application(proposal, packet)
        compressed = zlib.compress(b'\0\xff\xff\xff')
        first, last = (b'IDAT', compressed[:4]), (b'IDAT', compressed[4:])
        empty = (b'IDAT', b'')
        ancillary = (b'vpAg', b'fixture metadata')
        invalid_images = {
            'unknown critical chunk': [(b'VpAg', b''), first, last],
            'interrupted data chunks': [first, ancillary, last],
            'interrupted after empty data chunk': [empty, ancillary, first, last],
            'interrupted before empty data chunk': [first, last, ancillary, empty],
        }
        for description, chunks in invalid_images.items():
            with self.subTest(description=description):
                raw = png(chunks=chunks)
                capture.write_bytes(raw)
                proposal['evidence'][0]['sha256'] = hashlib.sha256(raw).hexdigest()
                with self.assertRaisesRegex(self.runtime.GateError, 'CAPTURE_REQUIRED'):
                    self.router.propose(copy.deepcopy(self.state), NODE, proposal)

        raw = png(chunks=[ancillary, empty, first, empty, last, empty, ancillary])
        capture.write_bytes(raw)
        proposal['evidence'][0]['sha256'] = hashlib.sha256(raw).hexdigest()
        self.router.propose(self.state, NODE, proposal)
        self.assertEqual(self.state['records'][NODE]['status'], 'AWAITING_HUMAN')

    def test_gate_rejects_png_with_invalid_row_data(self):
        proposal = self.prepare_case()
        self.pin_test_sources()
        packet = self.router.open_context(self.state, NODE, self.index)
        capture = self.attach_application(proposal, packet)
        invalid_images = {
            'row filter': png(zlib.compress(b'\x05\xff\xff\xff')),
            'RGB pixel depth': png(zlib.compress(b'\0\xff'), depth=1),
            'missing palette': png(zlib.compress(b'\0\0'), color=3),
        }
        for description, raw in invalid_images.items():
            with self.subTest(description=description):
                capture.write_bytes(raw)
                proposal['evidence'][0]['sha256'] = hashlib.sha256(raw).hexdigest()
                with self.assertRaisesRegex(self.runtime.GateError, 'CAPTURE_REQUIRED'):
                    self.router.propose(copy.deepcopy(self.state), NODE, proposal)

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

    def test_stale_pending_proposal_requires_explicit_invalidation(self):
        proposal = self.prepare_case()
        self.pin_test_sources()
        packet = self.router.open_context(self.state, NODE, self.index)
        capture = self.attach_application(proposal, packet)
        original_hash = self.router.propose(self.state, NODE, proposal)
        capture.unlink()

        before = copy.deepcopy(self.state)
        next_step = self.router.context_next(self.state)
        self.assertNotIn(NODE, next_step['awaiting_human'])
        self.assertNotIn(NODE, next_step['context_nodes'])
        self.assertEqual(next_step['stale_nodes'], [NODE])
        self.assertEqual(self.router.packet(self.state, NODE)['project_status'], 'STALE')
        with self.assertRaisesRegex(self.runtime.GateError, 'CONTEXT_PROPOSAL_STALE_USE_INVALIDATE'):
            self.router.open_context(self.state, NODE, self.index)
        with self.assertRaisesRegex(self.runtime.GateError, 'CONTEXT_PROPOSAL_STALE_USE_INVALIDATE'):
            self.router.propose(self.state, NODE, proposal)
        with self.assertRaisesRegex(self.runtime.GateError, 'EVIDENCE_CHANGED_OR_MISSING'):
            self.router.confirm_decision(self.state, NODE, self.fixture.receipt(original_hash, 'project'))
        self.assertEqual(self.state, before)

        self.router.invalidate(self.state, NODE, 'Capture was removed')
        self.assertIn(NODE, self.router.context_next(self.state)['context_nodes'])
        packet = self.router.open_context(self.state, NODE, self.index)
        self.attach_application(proposal, packet)
        proposal['summary'] += ' Captured again.'
        replacement_hash = self.router.propose(self.state, NODE, proposal)
        self.assertNotEqual(original_hash, replacement_hash)
        self.assertIn(NODE, self.router.context_next(self.state)['awaiting_human'])
        retired = next(event['record'] for event in self.state['history']
                       if event['event'] == 'proposal_replaced' and event['node_id'] == NODE)
        self.assertEqual(retired['proposal_hash'], original_hash)
        self.assertEqual(self.runtime.digest(retired['context_packet']), packet['context_id'])

    def test_proposal_revalidates_only_applicable_known_facts(self):
        proposal = self.prepare_case()
        self.pin_test_sources()
        facts = {}
        for fact_id, status, node_id in [('present', 'PRESENT', NODE), ('absent', 'ABSENT', NODE),
                                         ('unknown', 'UNKNOWN', NODE), ('unrelated', 'PRESENT', 'ENV02')]:
            path = self.ledger.parent / (fact_id + '.txt')
            raw = fact_id.encode()
            path.write_bytes(raw)
            facts[fact_id] = (path, raw)
            evidence = [{'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'note': 'Fixture fact'}]
            self.router.set_fact(self.state, fact_id, {'state': status, 'scope': 'project', 'subject': fact_id,
                                                      'revision': 1, 'applies_to': [node_id], 'value': True,
                                                      'evidence': evidence})
        packet = self.router.open_context(self.state, NODE, self.index)
        self.attach_application(proposal, packet)

        for fact_id in ('present', 'absent'):
            with self.subTest(fact=fact_id):
                path, raw = facts[fact_id]
                path.write_bytes(b'changed')
                try:
                    with self.assertRaisesRegex(self.runtime.GateError, 'EVIDENCE_CHANGED_OR_MISSING'):
                        self.router.propose(copy.deepcopy(self.state), NODE, proposal)
                finally:
                    path.write_bytes(raw)
        for fact_id in ('unknown', 'unrelated'):
            facts[fact_id][0].unlink()
        proposal_hash = self.router.propose(self.state, NODE, proposal)
        self.router.confirm_decision(self.state, NODE, self.fixture.receipt(proposal_hash, 'project'))
        self.assertTrue(self.router.record_current(self.state, NODE))
        facts['present'][0].unlink()
        self.assertFalse(self.router.record_current(self.state, NODE))

    def test_proposal_hash_and_png_validation_use_one_file_read(self):
        proposal = self.prepare_case()
        self.pin_test_sources()
        packet = self.router.open_context(self.state, NODE, self.index)
        capture = self.attach_application(proposal, packet)

        with patch.object(io, 'open', wraps=io.open) as opened:
            self.router.propose(self.state, NODE, proposal)
        self.assertEqual(sum(call.args[0] == capture for call in opened.call_args_list), 1)

    @unittest.skipUnless(importlib.util.find_spec('mcp'), 'Install the optional MCP SDK for stdio checks')
    def test_stdio_reports_g5_permissions_and_enforces_submission_gates(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import get_default_environment, stdio_client

        proposal = self.prepare_case()
        self.pin_test_sources()
        self.grant(['analyze'])
        self.runtime.save_state(self.ledger, self.state, None)
        skill_dir = self.fixture.work / 'portable' / 'skills' / 'design-tree'
        shutil.copytree(fixtures.SCRIPTS.parent, skill_dir)
        (skill_dir / 'references' / 'contracts.json').write_text(json.dumps(self.router.contracts), encoding='utf-8')
        # Forward the encoding-warning settings past the SDK's minimal environment.
        server_env = {**get_default_environment(),
                      **{k: os.environ[k] for k in ('PYTHONWARNDEFAULTENCODING', 'PYTHONWARNINGS')
                         if k in os.environ}}
        server = StdioServerParameters(command=sys.executable,
                                       args=['-B', str(skill_dir / 'scripts' / 'mcp_server.py'), '--state', str(self.ledger)],
                                       env=server_env)

        async def run():
            async with stdio_client(server) as (read, write), ClientSession(read, write) as client:
                async def protocol_step(label, response):
                    try:
                        return await asyncio.wait_for(response, timeout=15)
                    except asyncio.TimeoutError:
                        self.fail(f'Timed out waiting for MCP {label}')

                async def call(tool, **arguments):
                    result = await protocol_step(tool, client.call_tool(tool, arguments))
                    self.assertFalse(result.isError, result.content)
                    return result.structuredContent

                async def blocked(tool, reason, **arguments):
                    result = await protocol_step(tool, client.call_tool(tool, arguments))
                    self.assertTrue(result.isError, result.content)
                    self.assertIn(reason, result.content[0].text)

                await protocol_step('initialize', client.initialize())
                tools = await protocol_step('list_tools', client.list_tools())
                self.assertEqual({tool.name for tool in tools.tools},
                                 {'next_node', 'open_node', 'search_context', 'submit_evidence'})
                self.assertEqual((await call('next_node'))['active_phase'], PHASE)
                await blocked('open_node', 'CONTEXT_NODE_OUTSIDE_PILOT', node_id='LAY01')

                packet = await call('open_node', node_id=NODE)
                assistance = packet['packet']['assistance']
                self.assertEqual(assistance.get('action'), 'delegate_decision')
                self.assertFalse(assistance['allowed'])
                self.assertEqual(assistance['stop_reason'], 'CONTEXT_HUMAN_CONFIRMATION_REQUIRED')
                allowed = {'allowed': True, 'stop_reason': None}
                confirmation = {'required': True, 'actor': 'human', 'after': 'submit_evidence'}
                self.assertEqual(packet['packet']['permissions'], {
                    'analyze': allowed,
                    'draft': {'allowed': False, 'stop_reason': 'ACTION_NOT_DELEGATED'},
                    'confirm': confirmation,
                })
                self.attach_application(proposal, packet)
                revision = packet['revision']
                ledger_before = self.ledger.read_bytes()
                await blocked('submit_evidence', 'CONTEXT_ACTION_FORBIDDEN:ACTION_NOT_DELEGATED', node_id=NODE,
                              expected_revision=revision, proposal=proposal)
                self.assertEqual(self.ledger.read_bytes(), ledger_before)

                self.state = self.runtime.load_state(self.ledger)
                self.grant(['analyze', 'draft'])
                self.runtime.save_state(self.ledger, self.state, revision)
                packet = await call('open_node', node_id=NODE)
                self.assertEqual(packet['packet']['permissions'], {
                    'analyze': allowed, 'draft': allowed, 'confirm': confirmation,
                })
                self.attach_application(proposal, packet)
                incomplete = copy.deepcopy(proposal)
                incomplete['criterion_reviews'][0]['section_ids'].pop()
                revision = packet['revision']
                ledger_before = self.ledger.read_bytes()
                await blocked('submit_evidence', 'STATE_REVISION_CONFLICT', node_id=NODE,
                              expected_revision=revision - 1, proposal=incomplete)
                await blocked('submit_evidence', 'CONTEXT_APPLICATION_REQUIRED:layout', node_id=NODE,
                              expected_revision=revision, proposal=incomplete)
                self.assertEqual(self.ledger.read_bytes(), ledger_before)
                submitted = await call('submit_evidence', node_id=NODE,
                                       expected_revision=revision, proposal=proposal)
                self.assertEqual(submitted['state'], 'AWAITING_HUMAN')
                self.assertIn(NODE, (await call('next_node'))['awaiting_human'])
                record = self.runtime.load_state(self.ledger)['records'][NODE]
                self.assertEqual(record['status'], 'AWAITING_HUMAN')
                self.assertEqual(record['authority']['decided_by'], 'human')
                self.assertNotIn('permissions', record['context_packet'])
                self.assertNotIn('assistance', record['context_packet'])
                await blocked('submit_evidence', 'CONTEXT_NODE_AWAITING_HUMAN', node_id=NODE,
                              expected_revision=submitted['revision'], proposal=incomplete)

        asyncio.run(run())
