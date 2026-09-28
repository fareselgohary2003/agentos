#!/usr/bin/env python3
"""Minimal MCP-style stdio server exposing one tool: search.

Unlike github/server.py and postgres/server.py, this one genuinely needs a
paid/keyed API (Bing Web Search, SerpAPI, Tavily, etc.) to return live
results — there's no free, keyless web search endpoint to call here the way
GitHub's search API allows unauthenticated use. Set SEARCH_API_KEY and
SEARCH_API_PROVIDER to wire a real one; until then this returns a clearly
labeled stub so it fails loudly rather than silently, unlike a fake success.
"""
import json
import os
import sys
import urllib.request


def handle_search(arguments: dict) -> dict:
    query = arguments.get("query", "")
    api_key = os.environ.get("SEARCH_API_KEY")
    provider = os.environ.get("SEARCH_API_PROVIDER", "tavily")

    if not api_key:
        return {
            "stub": True,
            "query": query,
            "results": [],
            "note": "No SEARCH_API_KEY configured. Set SEARCH_API_KEY (and SEARCH_API_PROVIDER) "
                    "to enable real web search via this MCP server.",
        }

    if provider == "tavily":
        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=json.dumps({"api_key": api_key, "query": query, "max_results": 5}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return {"results": [{"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content")}
                             for r in data.get("results", [])]}

    return {"error": f"Unsupported SEARCH_API_PROVIDER: {provider}"}


def main() -> None:
    line = sys.stdin.readline()
    try:
        request = json.loads(line)
    except json.JSONDecodeError:
        print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"message": "invalid JSON"}}))
        return

    request_id = request.get("id")
    params = request.get("params", {})

    if request.get("method") != "tools/call" or params.get("name") != "search":
        response = {"jsonrpc": "2.0", "id": request_id, "error": {"message": "Unsupported method/tool"}}
    else:
        result = handle_search(params.get("arguments", {}))
        response = {"jsonrpc": "2.0", "id": request_id, "result": result}

    print(json.dumps(response))


if __name__ == "__main__":
    main()
