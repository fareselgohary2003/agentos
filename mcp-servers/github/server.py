#!/usr/bin/env python3
"""Minimal MCP-style stdio server exposing one tool: search_issues.
Uses the real GitHub REST API (no auth required for public repo search,
rate-limited). Set GITHUB_TOKEN in the environment for higher limits.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def handle_search_issues(arguments: dict) -> dict:
    query = arguments.get("query", "")
    repo = arguments.get("repo")  # e.g. "anthropics/anthropic-sdk-python"
    full_query = f"{query} repo:{repo}" if repo else query
    url = f"https://api.github.com/search/issues?q={urllib.parse.quote(full_query)}&per_page=5"

    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except urllib.error.URLError as exc:
        return {"error": str(exc)}

    return {
        "total_count": data.get("total_count", 0),
        "items": [
            {"title": item["title"], "url": item["html_url"], "state": item["state"]}
            for item in data.get("items", [])
        ],
    }


def main() -> None:
    line = sys.stdin.readline()
    try:
        request = json.loads(line)
    except json.JSONDecodeError:
        print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"message": "invalid JSON"}}))
        return

    request_id = request.get("id")
    params = request.get("params", {})

    if request.get("method") != "tools/call" or params.get("name") != "search_issues":
        response = {"jsonrpc": "2.0", "id": request_id,
                     "error": {"message": "Unsupported method/tool"}}
    else:
        result = handle_search_issues(params.get("arguments", {}))
        response = {"jsonrpc": "2.0", "id": request_id, "result": result}

    print(json.dumps(response))


if __name__ == "__main__":
    main()
