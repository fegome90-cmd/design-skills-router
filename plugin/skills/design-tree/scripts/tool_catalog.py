"""Canonical agent operations and the operator-owned, deny-only tool policy.

Ported from OpenPencil 4ca4e03177a6aa39673c53793745b9dc1e9eb84a
(core tools/schema, registry; MCP tool/metadata, manifest, policy, registration).
Copyright (c) 2026 Danila Poyarkov and OpenPencil contributors.
MIT license: see the full notice in plugin/NOTICE.md.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import os
from typing import Literal


POLICY_ENV = 'DESIGN_ROUTER_DISABLED_TOOLS'
ToolCapability = Literal['ledger:read', 'ledger:write', 'source:read', 'index:read',
                         'index:write', 'evidence:read']
Mutation = Literal['context_packet', 'derived_index', 'pending_proposal']
Interface = Literal['cli', 'mcp']


@dataclass(frozen=True)
class ToolExecution:
    mutation: tuple[Mutation, ...] = ()

    @property
    def mutates(self) -> bool:
        return bool(self.mutation)


@dataclass(frozen=True)
class ToolDef:
    name: str
    description: str
    action: Literal['orientation', 'analyze', 'draft']
    command: str
    handler: str
    execution: ToolExecution
    capabilities: tuple[ToolCapability, ...]
    exposure: frozenset[Interface]
    availability: Literal['default'] = 'default'

    @property
    def effect(self) -> Literal['read', 'write']:
        return 'write' if self.execution.mutates else 'read'


def define_tool(*, name, description, action, command, handler, capabilities,
                mutation=()) -> ToolDef:
    # Unlike the upstream document tools, index rebuilds are writes too.
    return ToolDef(name, description, action, command, handler, ToolExecution(mutation),
                   capabilities, frozenset(('cli', 'mcp')))


ALL_TOOLS = (
    define_tool(name='next_node', description="Read the runner's current phase, revision and pending nodes.",
                action='orientation', command='next', handler='Router.context_next',
                capabilities=('ledger:read',)),
    define_tool(name='open_node', description='Return pinned sections, project context, and the permissions to analyze and draft.',
                action='analyze', command='open', handler='Router.open_context',
                capabilities=('ledger:read', 'ledger:write', 'source:read', 'index:read', 'index:write', 'evidence:read'),
                mutation=('context_packet', 'derived_index')),
    define_tool(name='search_context', description='Find optional source sections within the current pilot node.',
                action='analyze', command='search', handler='Router.open_context',
                capabilities=('ledger:read', 'source:read', 'index:read', 'index:write', 'evidence:read'),
                mutation=('derived_index',)),
    define_tool(name='submit_evidence', description='Submit a G5 draft with its context ID and local evidence for human confirmation.',
                action='draft', command='propose', handler='Router.propose',
                capabilities=('ledger:read', 'ledger:write', 'source:read', 'evidence:read'),
                mutation=('pending_proposal',)),
)
_BY_NAME = {definition.name: definition for definition in ALL_TOOLS}
_BY_COMMAND = {definition.command: definition for definition in ALL_TOOLS}


@dataclass(frozen=True)
class ToolDescriptor:
    definition: ToolDef
    enabled: bool = True


def create_tool_descriptors(interface: Interface) -> tuple[ToolDescriptor, ...]:
    return tuple(ToolDescriptor(definition) for definition in ALL_TOOLS
                 if interface in definition.exposure)


def parse_disabled_tools(value: str | None) -> frozenset[str]:
    # Upstream trims and deduplicates comma-separated names. Fail closed on
    # unknown or empty entries rather than silently accepting a typo.
    if value is None or value == '':
        return frozenset()
    if not isinstance(value, str):
        raise ValueError('INVALID_TOOL_POLICY')
    names = tuple(name.strip() for name in value.split(','))
    if any(name not in _BY_NAME for name in names):
        raise ValueError('INVALID_TOOL_POLICY: expected comma-separated canonical tool names')
    return frozenset(names)


def read_tool_policy() -> frozenset[str]:
    return parse_disabled_tools(os.environ.get(POLICY_ENV))


def is_tool_enabled(descriptor: ToolDescriptor, disabled: frozenset[str]) -> bool:
    return descriptor.definition.name not in disabled and descriptor.definition.availability == 'default'


def apply_tool_policy(descriptors: tuple[ToolDescriptor, ...],
                      disabled: frozenset[str]) -> tuple[ToolDescriptor, ...]:
    return tuple(replace(descriptor, enabled=is_tool_enabled(descriptor, disabled))
                 for descriptor in descriptors)


def operation_for_command(command: str) -> ToolDef:
    try:
        return _BY_COMMAND[command]
    except KeyError:
        raise ValueError('UNKNOWN_TOOL_COMMAND') from None


def require_enabled(name: str) -> ToolDef:
    definition = _BY_NAME.get(name)
    if definition is None:
        raise ValueError('UNKNOWN_TOOL_COMMAND')
    if not is_tool_enabled(ToolDescriptor(definition), read_tool_policy()):
        raise ValueError('TOOL_DISABLED:' + name)
    return definition
