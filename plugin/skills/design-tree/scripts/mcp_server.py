"""Local stdio adapter for the G5 context pilot."""
import argparse
from pathlib import Path

from runner import context_command, require
from tool_catalog import apply_tool_policy, create_tool_descriptors, read_tool_policy


def server_for(state_path):
    from mcp.server.fastmcp import FastMCP
    from mcp.types import ToolAnnotations

    state_path = Path(state_path).absolute()
    evidence_root = state_path.resolve().parent / 'evidence'
    server = FastMCP('Design Skills Router')
    descriptors = {item.definition.name: item for item in
                   apply_tool_policy(create_tool_descriptors('mcp'), read_tool_policy())}

    def register(handler):
        descriptor = descriptors[handler.__name__]
        definition = descriptor.definition
        if descriptor.enabled:
            server.add_tool(
                handler, name=definition.name, description=definition.description,
                annotations=ToolAnnotations(readOnlyHint=definition.effect == 'read',
                                            destructiveHint=definition.effect == 'write'),
                meta={'design-router/capabilities': list(definition.capabilities),
                      'design-router/action': definition.action,
                      'design-router/mutation': list(definition.execution.mutation)},
            )
        return handler

    @register
    def next_node() -> dict[str, object]:
        return context_command(state_path, 'next')

    @register
    def open_node(node_id: str) -> dict[str, object]:
        return context_command(state_path, 'open', node_id=node_id)

    @register
    def search_context(node_id: str, query: str) -> dict[str, object]:
        return context_command(state_path, 'search', node_id=node_id, query=query)

    @register
    def submit_evidence(node_id: str, expected_revision: int, proposal: dict[str, object]) -> dict[str, object]:
        evidence = proposal.get('evidence')
        require(isinstance(evidence, list) and bool(evidence), 'EVIDENCE_REQUIRED')
        require(not evidence_root.is_symlink(), 'MCP_EVIDENCE_ROOT_SYMLINK')
        for entry in evidence:
            path = entry.get('path') if isinstance(entry, dict) else None
            require(isinstance(path, str), 'MCP_EVIDENCE_PATH_REQUIRED')
            artifact = Path(path)
            require(artifact.is_absolute() and artifact == artifact.resolve()
                    and artifact.is_relative_to(evidence_root), 'MCP_EVIDENCE_OUTSIDE_PROJECT')
        return context_command(state_path, 'propose', node_id=node_id, proposal=proposal,
                               expected_revision=expected_revision)

    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    args = parser.parse_args()
    try:
        server = server_for(args.state)
    except ModuleNotFoundError as error:
        if error.name != 'mcp':
            raise
        parser.exit(2, 'Install design-skills-router[mcp] to start the MCP server.\n')
    except ValueError as error:
        parser.exit(2, str(error) + '\n')
    server.run(transport='stdio')
