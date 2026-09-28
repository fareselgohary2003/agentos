#!/usr/bin/env python3
"""Minimal MCP-style stdio server exposing one tool: send_notification.

Slack: if SLACK_WEBHOOK_URL is set, this makes a real HTTP POST to it (Slack
incoming webhooks need no other auth, so this path is fully real once a
webhook URL is configured — nothing else to stub). Email: genuinely needs an
SMTP/SES/SendGrid credential this environment doesn't have, so it stays a
clearly labeled stub, matching app/tools/builtin.py's SendEmailTool.
"""
import json
import os
import sys
import urllib.error
import urllib.request


def handle_send_notification(arguments: dict) -> dict:
    channel = arguments.get("channel")  # "slack" | "email"
    message = arguments.get("message", "")

    if channel == "slack":
        webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
        if not webhook_url:
            return {"sent": False, "note": "SLACK_WEBHOOK_URL is not configured."}
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps({"text": message}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return {"sent": resp.status == 200}
        except urllib.error.URLError as exc:
            return {"sent": False, "error": str(exc)}

    if channel == "email":
        return {"sent": False, "note": "Email requires an SMTP/SES/SendGrid credential — "
                                        "not configured in this environment. See "
                                        "app/tools/builtin.py SendEmailTool for the same stub."}

    return {"error": f"Unsupported channel: {channel}"}


def main() -> None:
    line = sys.stdin.readline()
    try:
        request = json.loads(line)
    except json.JSONDecodeError:
        print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"message": "invalid JSON"}}))
        return

    request_id = request.get("id")
    params = request.get("params", {})

    if request.get("method") != "tools/call" or params.get("name") != "send_notification":
        response = {"jsonrpc": "2.0", "id": request_id, "error": {"message": "Unsupported method/tool"}}
    else:
        result = handle_send_notification(params.get("arguments", {}))
        response = {"jsonrpc": "2.0", "id": request_id, "result": result}

    print(json.dumps(response))


if __name__ == "__main__":
    main()
