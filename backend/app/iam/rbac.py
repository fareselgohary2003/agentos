"""System role/permission catalog. Seeded per-organization on creation."""

PERMISSIONS = [
    ("org:manage", "Manage organization settings and billing"),
    ("users:manage", "Invite/remove users, change roles"),
    ("agents:manage", "Create/update/delete agents"),
    ("agents:execute", "Execute agent workflows"),
    ("tools:manage", "Register/update/enable tools"),
    ("workflows:execute", "Trigger workflow executions"),
    ("executions:view", "View execution history and traces"),
    ("approvals:decide", "Approve or reject pending approval requests"),
    ("billing:view", "View cost and usage dashboards"),
    ("audit:view", "View audit logs"),
]

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "OWNER": [code for code, _ in PERMISSIONS],
    "ADMIN": [
        "agents:manage", "agents:execute", "tools:manage", "workflows:execute",
        "executions:view", "approvals:decide", "audit:view",
    ],
    "MANAGER": ["agents:execute", "workflows:execute", "executions:view", "approvals:decide"],
    "MEMBER": ["agents:execute", "workflows:execute", "executions:view"],
    "VIEWER": ["executions:view"],
}

SYSTEM_ROLES = list(ROLE_PERMISSIONS.keys())
