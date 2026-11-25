"""Measure local authorization policy; do NOT substitute for host question counts."""
import importlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/design-tree/scripts'))


class ExperiencePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = importlib.import_module('assistance')
        cls.fixture = json.loads((ROOT / 'tests/fixtures/host-routing-cases.json').read_text(encoding='utf-8'))

    def test_twelve_reversible_nodes_and_one_reserved_node(self):
        spec = self.fixture['policy_budget']
        self.assertEqual(len(spec['reversible_node_ids']), 12)
        self.assertEqual([t['task_id'] for t in spec['tasks']], ['button-review', 'drawer-review'])
        self.assertTrue(all(t['node_ids'] == spec['reversible_node_ids'] for t in spec['tasks']))
        self.assertTrue(all(t['reserved_node_id'] == spec['reserved_node_id'] for t in spec['tasks']))
        self.assertEqual(spec['scope_change']['effect'], 'fresh_grant_required')
        self.assertTrue(spec['reserved_node_id'])
        ids = spec['reversible_node_ids'] + [spec['reserved_node_id']]
        for level in ('manual', 'guided', 'phase_auto'):
            state = {
                'assistance_level': level,
                'active_phase_id': 'design',
                'active_grant_id': 'grant' if level != 'manual' else None,
                'grants': {'grant': {'id': 'grant', 'level': level, 'status': 'ACTIVE',
                                      'reserved_decisions': [spec['reserved_node_id']],
                                      'allowed_actions': ['analyze', 'compare', 'draft', 'test']}},
                'phases': {'design': {'status': 'ACTIVE', 'node_instance_ids': ids}}
            }
            allowed = [self.policy.assistance_action(state, {'id': nid}, 'delegate')['allowed']
                       for nid in spec['reversible_node_ids']]
            self.assertEqual(sum(allowed), 0 if level == 'manual' else 12)
            self.assertFalse(self.policy.assistance_action(state,
                          {'id': spec['reserved_node_id']}, 'delegate')['allowed'])
            if level != 'manual':
                state['phases']['design']['status'] = 'AWAITING_HUMAN'
                self.assertEqual(self.policy.assistance_action(state, {'id': ids[0]}, 'delegate')['stop_reason'],
                                 'PHASE_GATE_REQUIRED')
        self.assertIsNone(spec['actual_question_count'])
        self.assertIsNone(spec['actual_avoidable_questions'])
        self.assertEqual(spec['host_result'], 'UNVERIFIED')

    def test_scorecard_distinguishes_user_observation_from_host_trace(self):
        t = (ROOT / 'skills/design-tree/references/PILOT.md').read_text(encoding='utf-8')
        for required in ('question_count', 'avoidable_questions', 'node_decisions_recorded',
                         'phase_gate_respected', 'USER_OBSERVED', 'TRACE_VERIFIED', 'UNVERIFIED',
                         'observed_at', 'scope', 'trace_refs'):
            self.assertIn(required, t)
        self.assertIn('12 decisiones reversibles', t)
        self.assertIn('no mide preguntas reales', t)


class ScopedGrantUXTests(unittest.TestCase):
    def test_change_of_scope_invalidates_before_new_grant(self):
        sys.path.insert(0, str(ROOT/'tests'))
        import test_runner as fixtures
        fixtures.RunnerTests.setUpClass()
        h=fixtures.RunnerTests(methodName='test_root_only_initially')
        h.setUp()
        self.addCleanup(h.doCleanups)
        router,state=h.router,h.state
        phase=router.default_phase_map()
        router.configure_phases(state,phase,h.receipt(h.r.digest(phase),'phase_map'))
        grant=router.grant_template(state,'foundations','guided')
        state['scope']='changed scope'
        with self.assertRaisesRegex(h.r.GateError, 'GRANT_SCOPE_MISMATCH'):
            router.grant_assistance(state,grant,h.receipt(router.grant_hash(state,grant),'delegation'))
        self.assertEqual(state['assistance_level'],'manual')
        self.assertIsNone(state['active_grant_id'])
