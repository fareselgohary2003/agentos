#!/usr/bin/env python3
"""Minimal MCP-style stdio server exposing one tool: run_readonly_query.
Connects to the real Postgres instance via DATABASE_URL_SYNC (a plain
psycopg2-style DSN, since this script has no async runtime of its own) and
enforces the same SELECT-only rule as app.tools.builtin.validate_readonly_select,
duplicated here deliberately: an MCP server must not trust its caller's
validation, since a different agent or a future caller could invoke it
directly.
"""
import json
import os
import re
import sys

BLOCKED_KEYWORDS = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b", re.IGNORECASE
)


def validate_readonly(sql: str) -> str | None:
    cleaned = sql.strip().rstrip(";")
    if ";" in cleaned:
        return "Multiple statements are not allowed"
    if not re.match(r"^\s*SELECT\b", cleaned, re.IGNORECASE):
        return "Only SELECT statements are permitted"
    if BLOCKED_KEYWORDS.search(cleaned):
        return "Query contains a disallowed mutating keyword"
    return None


def handle_run_readonly_query(arguments: dict) -> dict:
    sql = arguments.get("sql", "")
    error = validate_readonly(sql)
    if error:
        return {"error": error}

    try:
        import psycopg2
    except ImportError:
        return {"error": "psycopg2 is not installed in this MCP server's environment"}

    dsn = os.environ.get("DATABASE_URL_SYNC", "postgresql://agentos:agentos@localhost:5432/agentos")
    try:
        conn = psycopg2.connect(dsn)
        with conn.cursor() as cur:
            cur.execute(sql)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchmany(100)
        conn.close()
    except Exception as exc:
        return {"error": str(exc)}

    return {"columns": columns, "rows": [list(r) for r in rows], "row_count": len(rows)}


def main() -> None:
    line = sys.stdin.readline()
    try:
        request = json.loads(line)
    except json.JSONDecodeError:
        print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"message": "invalid JSON"}}))
        return

    request_id = request.get("id")
    params = request.get("params", {})

    if request.get("method") != "tools/call" or params.get("name") != "run_readonly_query":
        response = {"jsonrpc": "2.0", "id": request_id, "error": {"message": "Unsupported method/tool"}}
    else:
        result = handle_run_readonly_query(params.get("arguments", {}))
        response = {"jsonrpc": "2.0", "id": request_id, "result": result}

    print(json.dumps(response))


if __name__ == "__main__":
    main()
