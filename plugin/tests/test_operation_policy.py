"""Observable policy checks on the common runner path (R02A)."""
import os
import unittest
from unittest.mock import patch

import test_node_context as fixture


ENV = 'DESIGN_ROUTER_DISABLED_TOOLS'


class OperationPolicyTests(unittest.TestCase):
    def setUp(self):
        case = fixture.NodeContextTests('test_phase_routes_before_authorizing_context')
        case.setUpClass()
        case.setUp()
        self.addCleanup(case.doCleanups)
        self.case = case
        case.prepare_case()
        case.grant(['analyze'])
        case.runtime.save_state(case.ledger, case.state, None)

    def test_disabled_search_rejected_before_ledger_or_index_changes(self):
        c = self.case
        before = c.ledger.read_bytes()
        index = c.ledger.with_name(c.ledger.name + '.context.sqlite3')
        with patch.dict(os.environ, {ENV: 'search_context'}):
            with self.assertRaisesRegex(c.runtime.GateError, 'TOOL_DISABLED:search_context'):
                c.runtime.context_command(c.ledger, 'search', node_id=fixture.NODE, query='jerarquía')
        self.assertEqual(c.ledger.read_bytes(), before)
        self.assertFalse(index.exists())

    def test_invalid_policy_fails_closed_on_orientation(self):
        c = self.case
        before = c.ledger.read_bytes()
        for value in ('unknown_operation', 'search_context,,open_node', '*', 'SEARCH_CONTEXT'):
            with self.subTest(value=value), patch.dict(os.environ, {ENV: value}):
                with self.assertRaisesRegex(c.runtime.GateError, 'INVALID_TOOL_POLICY'):
                    c.runtime.context_command(c.ledger, 'next')
        self.assertEqual(c.ledger.read_bytes(), before)

    def test_unknown_runner_context_command_is_rejected(self):
        c = self.case
        with self.assertRaisesRegex(c.runtime.GateError, 'UNKNOWN_TOOL_COMMAND'):
            c.runtime.context_command(c.ledger, 'unregistered', node_id=fixture.NODE)

    def test_policy_parser_normalizes_deduplicates_and_projects(self):
        from tool_catalog import create_tool_descriptors, parse_disabled_tools, apply_tool_policy
        policy = parse_disabled_tools(' search_context , search_context ')
        self.assertEqual(policy, frozenset({'search_context'}))
        descriptors = apply_tool_policy(create_tool_descriptors('mcp'), policy)
        self.assertEqual({d.definition.name for d in descriptors if d.enabled},
                         {'next_node', 'open_node', 'submit_evidence'})
        self.assertEqual({d.definition.name: d.definition.effect for d in descriptors}, {
            'next_node': 'read', 'open_node': 'write', 'search_context': 'write',
            'submit_evidence': 'write',
        })

    def test_scope_policy_does_not_grant_other_operations_or_actions(self):
        # Adapted from OpenPencil packages/mcp/tests/tool/scope.test.ts:
        # one tool can remain enabled while another is explicitly denied.
        # Domain assistance remains a separate requirement.
        from tool_catalog import create_tool_descriptors, apply_tool_policy, parse_disabled_tools
        for interface in ('cli', 'mcp'):
            for name in ('next_node', 'open_node', 'search_context', 'submit_evidence'):
                with self.subTest(interface=interface, name=name):
                    allowed = {d.definition.name for d in
                               apply_tool_policy(create_tool_descriptors(interface), parse_disabled_tools(name))
                               if d.enabled}
                    self.assertEqual(allowed, {'next_node', 'open_node', 'search_context', 'submit_evidence'} - {name})

    def test_direct_runner_methods_cannot_bypass_policy(self):
        c = self.case
        c.pin_test_sources()
        index = c.index
        from copy import deepcopy
        before = deepcopy(c.state)
        for name, call in (
            ('next_node', lambda: c.router.context_next(c.state)),
            ('open_node', lambda: c.router.open_context(c.state, fixture.NODE, index)),
            ('search_context', lambda: c.router.open_context(c.state, fixture.NODE, index, query='jerarquía')),
            ('submit_evidence', lambda: c.router.propose(c.state, fixture.NODE, {})),
        ):
            with self.subTest(name=name), patch.dict(os.environ, {ENV: name}):
                with self.assertRaisesRegex(c.runtime.GateError, 'TOOL_DISABLED:' + name):
                    call()
                self.assertEqual(c.state, before)
                self.assertFalse(index.exists())
