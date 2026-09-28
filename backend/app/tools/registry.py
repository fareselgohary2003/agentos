"""Agents call ToolRegistry.resolve('web_search'), never import a tool class
directly. This is the seam where an MCP-backed tool can later replace a local
one with zero changes to agent code (see app/tools/mcp_adapter.py).
"""
from app.tools.base import Tool


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def resolve(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered")
        return self._tools[name]

    def list_names(self) -> list[str]:
        return list(self._tools.keys())


_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _register_builtin_tools(_registry)
    return _registry


def _register_builtin_tools(registry: ToolRegistry) -> None:
    from app.tools.builtin import (
        DocumentSearchTool, PythonSandboxTool, SendEmailTool, SqlQueryTool, WebSearchTool,
    )

    registry.register(WebSearchTool())
    registry.register(SqlQueryTool())
    registry.register(PythonSandboxTool())
    registry.register(SendEmailTool())
    registry.register(DocumentSearchTool())