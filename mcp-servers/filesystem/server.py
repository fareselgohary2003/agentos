#!/usr/bin/env python3
"""Minimal MCP-style stdio server exposing one tool: list_files.

This is intentionally tiny — it exists to prove the ToolRegistry -> MCPToolAdapter
-> subprocess -> JSON-RPC seam described in docs/architecture/00-design.md §6
actually works end to end, not to be a spec-complete MCP implementation. Swap
in the official `mcp` SDK server scaffolding here for production.

Protocol: reads one line of JSON-RPC request from stdin, writes one line of
JSON-RPC response to stdout, then exits. (A long-lived server would loop; kept
single-shot here to match how MCPToolAdapter spawns it per call.)
"""
import json
import os
import sys


def handle_list_files(arguments: dict) -> dict:
    path = arguments.get("path", ".")
    if not os.path.isdir(path):
        return {"error": f"Not a directory: {path}"}
    entries = sorted(os.listdir(path))
    return {"path": path, "entries": entries}


def main() -> None:
    line = sys.stdin.readline()
    try:
        request = json.loads(line)
    except json.JSONDecodeError:
        print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"message": "invalid JSON"}}))
        return

    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    if method != "tools/call" or params.get("name") != "list_files":
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"message": f"Unsupported method/tool: {method}/{params.get('name')}"},
        }
    else:
        result = handle_list_files(params.get("arguments", {}))
        response = {"jsonrpc": "2.0", "id": request_id, "result": result}

    print(json.dumps(response))


if __name__ == "__main__":
    main()
