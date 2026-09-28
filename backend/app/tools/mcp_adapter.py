"""Wraps a real MCP server as a Tool so agents call it exactly like a local
tool via ToolRegistry.resolve(). This is the seam described in
docs/architecture/00-design.md §6: agents never know whether 'github.search_issues'
is local Python or a remote MCP process.

This adapter speaks MCP's JSON-RPC-over-stdio framing to a subprocess. It is
kept minimal — enough to prove the seam works end-to-end against
mcp-servers/filesystem (the simplest server to run with zero external deps) —
rather than a full MCP client implementation. Swap in the official `mcp`
Python SDK client here for production use.
"""
from __future__ import annotations

import asyncio
import json
import uuid

from pydantic import BaseModel, create_model

from app.tools.base import RetryPolicy, Tool, ToolContext, ToolRiskLevel


class MCPConnectionError(Exception):
    pass


class MCPToolAdapter(Tool):
    """A Tool backed by a single tool exposed on a remote MCP server process."""

    def __init__(
        self,
        server_command: list[str],
        tool_name: str,
        description: str,
        risk_level: ToolRiskLevel = ToolRiskLevel.MEDIUM,
        timeout_seconds: int = 30,
    ):
        self.name = tool_name
        self.description = description
        self.risk_level = risk_level
        self.timeout_seconds = timeout_seconds
        self.retry_policy = RetryPolicy(max_retries=1)
        # MCP tools accept/return arbitrary JSON; wrap it in a permissive model
        # rather than forcing a rigid schema the server doesn't declare to us here.
        self.input_schema: type[BaseModel] = create_model(
            f"{tool_name}_Input", __base__=BaseModel, params=(dict, {})
        )
        self.output_schema: type[BaseModel] = create_model(
            f"{tool_name}_Output", __base__=BaseModel, result=(dict, {})
        )
        self._server_command = server_command

    async def _run(self, input: BaseModel, ctx: ToolContext):
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": self.name, "arguments": input.model_dump().get("params", {})},
        }

        proc = await asyncio.create_subprocess_exec(
            *self._server_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            payload = (json.dumps(request) + "\n").encode()
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(payload), timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError as exc:
            proc.kill()
            raise MCPConnectionError(f"MCP server '{self.name}' timed out") from exc

        if proc.returncode != 0:
            raise MCPConnectionError(f"MCP server exited {proc.returncode}: {stderr.decode()}")

        try:
            response = json.loads(stdout.decode().strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError) as exc:
            raise MCPConnectionError(f"Malformed MCP response: {stdout!r}") from exc

        if "error" in response:
            raise MCPConnectionError(response["error"].get("message", "MCP tool call failed"))

        return self.output_schema.model_validate({"result": response.get("result", {})})
