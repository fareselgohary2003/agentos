"""Seed a complete, self-consistent fictional small company into AgentOS.

Company: Brightleaf Home Goods — a small (38-employee) home décor e-commerce
retailer based in Austin, TX, founded 2019. Sells Lighting, Textiles,
Kitchenware, Decor, and Furniture across 4 regions.

The narrative baked into the data (so every table tells the same story,
which is what makes the demo scenario in spec §41 actually cohere):
Q3 2026 revenue dropped ~18% overall, concentrated almost entirely in the
Lighting category in the North America - East region, coinciding with a
competitor ("Lumina Living") launching aggressive price cuts there in July.

Run:
    export DATABASE_URL=postgresql+asyncpg://agentos:agentos@localhost:5432/agentos
    python -m scripts.seed_demo_company
"""
from __future__ import annotations

import asyncio
import random
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.models import Agent, Prompt, ToolCatalogEntry
from app.analytics.models import Customer, Product, ProductCategory, Region, SalesOrder
from app.approvals.models import ApprovalRequest
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.evaluation.models import Document, Evaluation, LLMUsage
from app.execution.models import Task, TaskExecution, Workflow, WorkflowExecution
from app.iam.models import AuditLog, Organization, Role, User
from app.iam.service import seed_roles_for_organization
from app.memory.models import Memory

random.seed(42)

ORG_NAME = "Brightleaf Home Goods"
ORG_SLUG = "brightleaf-home"

CATEGORIES = ["Lighting", "Textiles", "Kitchenware", "Decor", "Furniture"]
REGIONS = ["North America - East", "North America - West", "Europe", "APAC"]

USERS = [
    ("Sarah Chen", "sarah@brightleafhome.com", "OWNER"),
    ("Marcus Webb", "marcus@brightleafhome.com", "ADMIN"),
    ("Priya Nair", "priya@brightleafhome.com", "MANAGER"),
    ("Diego Alvarez", "diego@brightleafhome.com", "MANAGER"),
    ("Emily Zhou", "emily@brightleafhome.com", "MEMBER"),
    ("Tom Baker", "tom@brightleafhome.com", "MEMBER"),
    ("James Okafor", "james@brightleafhome.com", "VIEWER"),
]
DEMO_PASSWORD = "BrightleafDemo123"

PRODUCTS_BY_CATEGORY = {
    "Lighting": [
        ("Aria Pendant Lamp", 89.0, 34.0), ("Solstice Floor Lamp", 129.0, 52.0),
        ("Nomad Table Lamp", 59.0, 22.0), ("Halo LED Strip Kit", 39.0, 14.0),
        ("Ember Wall Sconce", 74.0, 29.0), ("Drift Chandelier", 249.0, 98.0),
    ],
    "Textiles": [
        ("Linen Weave Throw", 45.0, 16.0), ("Wool Kilim Rug 5x7", 189.0, 74.0),
        ("Waffle Knit Blanket", 39.0, 13.0), ("Velvet Cushion Cover Set", 29.0, 9.0),
    ],
    "Kitchenware": [
        ("Cast Iron Dutch Oven", 119.0, 48.0), ("Bamboo Utensil Set", 24.0, 8.0),
        ("Ceramic Pour-Over Set", 34.0, 12.0), ("Stoneware Dinner Set (16pc)", 89.0, 35.0),
    ],
    "Decor": [
        ("Terrazzo Vase", 32.0, 11.0), ("Rattan Wall Mirror", 68.0, 26.0),
        ("Botanical Print Set (3)", 42.0, 14.0), ("Ceramic Planter Trio", 36.0, 13.0),
    ],
    "Furniture": [
        ("Alder Accent Chair", 349.0, 142.0), ("Birchwood Side Table", 129.0, 51.0),
        ("Modular Bookshelf", 219.0, 88.0),
    ],
}

CUSTOMER_NAMES_BY_SEGMENT = {
    "retail": [
        "Ava Thompson", "Liam Patel", "Noah Kim", "Isabella Rossi", "Mia Johansson",
        "Ethan Wallace", "Sophia Muller", "Lucas Dubois", "Grace O'Connell", "Oliver Tanaka",
    ],
    "wholesale": [
        "Cedar & Stone Home Boutique", "Maple Row Interiors", "Urban Nest Collective",
        "The Hearth Trading Co.", "Willowmere Living",
    ],
}

PROMPT_TEMPLATES = [
    ("supervisor_v1", "Supervisor system prompt",
     "You are the Supervisor of an autonomous multi-agent system. Understand the user's goal, "
     "delegate to specialist agents, monitor progress, and decide when to replan or request "
     "human approval.", ["goal"]),
    ("planner_v1", "Planner system prompt",
     "Break the goal into a JSON plan of tasks assigned to specialist agents, marking "
     "dependencies only where genuinely required.", ["goal"]),
    ("research_v1", "Research agent system prompt",
     "Search for and summarize relevant external information with citations. Never present "
     "unsupported claims as fact.", ["task"]),
    ("verification_v1", "Verification agent system prompt",
     "Check agent outputs for unsupported claims, contradictions, and calculation errors "
     "against the source data.", ["output"]),
    ("report_v1", "Report agent system prompt",
     "Write a concise executive summary and structured sections from the findings provided.",
     ["findings"]),
]

AGENTS_SPEC = [
    ("Supervisor Agent", "Understands goals, plans, delegates, monitors, replans, finalizes.",
     "supervisor_v1", []),
    ("Planner Agent", "Creates structured execution plans from a goal.", "planner_v1", []),
    ("Research Agent", "Searches the web, retrieves and summarizes sources with citations.",
     "research_v1", ["web_search"]),
    ("Data Analyst Agent", "Queries internal data (read-only SQL) and computes statistics.",
     "planner_v1", ["sql_query"]),
    ("Code Agent", "Generates and executes Python in a sandboxed environment.",
     "planner_v1", ["python_sandbox"]),
    ("Verification Agent", "Checks factual consistency, groundedness, and calculations.",
     "verification_v1", []),
    ("Report Agent", "Generates executive summaries and structured reports.", "report_v1", []),
    ("Notification Agent", "Prepares and sends approved email/Slack/webhook notifications.",
     "report_v1", ["send_email"]),
]

TOOLS_SPEC = [
    ("web_search", "Search the web for external information.", "low", 20),
    ("sql_query", "Run a read-only SELECT against organization data.", "medium", 15),
    ("python_sandbox", "Execute Python in an isolated sandbox.", "high", 10),
    ("send_email", "Send an email notification (requires approval).", "high", 15),
]


async def get_or_create_org(db: AsyncSession) -> Organization:
    existing = await db.execute(select(Organization).where(Organization.slug == ORG_SLUG))
    org = existing.scalar_one_or_none()
    if org:
        return org
    org = Organization(name=ORG_NAME, slug=ORG_SLUG, plan="growth")
    db.add(org)
    await db.flush()
    await seed_roles_for_organization(db, org)
    await db.commit()
    return org


async def seed_users(db: AsyncSession, org: Organization) -> dict[str, User]:
    roles_result = await db.execute(select(Role).where(Role.organization_id == org.id))
    roles_by_name = {r.name: r for r in roles_result.scalars().all()}

    users: dict[str, User] = {}
    for full_name, email, role_name in USERS:
        existing = await db.execute(select(User).where(User.email == email))
        user = existing.scalar_one_or_none()
        if not user:
            user = User(
                organization_id=org.id,
                email=email,
                hashed_password=hash_password(DEMO_PASSWORD),
                full_name=full_name,
            )
            user.roles = [roles_by_name[role_name]]
            db.add(user)
            await db.flush()
        users[email] = user
    await db.commit()
    return users


async def seed_business_data(db: AsyncSession, org: Organization):
    existing = await db.execute(select(Region).where(Region.organization_id == org.id))
    if existing.scalars().first():
        regions = {r.name: r for r in (await db.execute(
            select(Region).where(Region.organization_id == org.id))).scalars().all()}
        categories = {c.name: c for c in (await db.execute(
            select(ProductCategory).where(ProductCategory.organization_id == org.id))).scalars().all()}
        products = list((await db.execute(
            select(Product).where(Product.organization_id == org.id))).scalars().all())
        customers = list((await db.execute(
            select(Customer).where(Customer.organization_id == org.id))).scalars().all())
        return regions, categories, products, customers

    regions = {}
    for name in REGIONS:
        r = Region(organization_id=org.id, name=name)
        db.add(r)
        regions[name] = r
    await db.flush()

    categories = {}
    for name in CATEGORIES:
        c = ProductCategory(organization_id=org.id, name=name)
        db.add(c)
        categories[name] = c
    await db.flush()

    products: list[Product] = []
    for cat_name, items in PRODUCTS_BY_CATEGORY.items():
        for i, (name, price, cost) in enumerate(items):
            sku = f"{cat_name[:3].upper()}-{i + 1:03d}"
            p = Product(
                organization_id=org.id, category_id=categories[cat_name].id,
                sku=sku, name=name, unit_price=price, unit_cost=cost,
            )
            db.add(p)
            products.append(p)
    await db.flush()

    customers: list[Customer] = []
    for segment, names in CUSTOMER_NAMES_BY_SEGMENT.items():
        for name in names:
            region = random.choice(list(regions.values()))
            c = Customer(organization_id=org.id, region_id=region.id, name=name, segment=segment)
            db.add(c)
            customers.append(c)
    await db.flush()
    await db.commit()
    return regions, categories, products, customers


async def seed_sales_orders(db: AsyncSession, org: Organization, regions, categories, products, customers):
    existing = await db.execute(select(SalesOrder).where(SalesOrder.organization_id == org.id).limit(1))
    if existing.scalar_one_or_none():
        return

    lighting_products = [p for p in products if p.category_id == categories["Lighting"].id]
    other_products = [p for p in products if p.category_id != categories["Lighting"].id]
    ne_region = regions["North America - East"]

    quarters = [
        ("2026-Q1", date(2026, 1, 1), date(2026, 3, 31), 1.0),
        ("2026-Q2", date(2026, 4, 1), date(2026, 6, 30), 1.08),
        ("2026-Q3", date(2026, 7, 1), date(2026, 9, 15), 0.95),
    ]

    orders = []
    for quarter_label, start, end, base_multiplier in quarters:
        days = (end - start).days
        is_q3 = quarter_label == "2026-Q3"

        for _ in range(140):
            order_date = start + timedelta(days=random.randint(0, days))
            customer = random.choice(customers)
            in_ne = customer.region_id == ne_region.id
            product = random.choice(lighting_products if random.random() < 0.4 else other_products)
            is_lighting = product in lighting_products

            multiplier = base_multiplier
            if is_q3 and is_lighting and in_ne:
                multiplier *= 0.35  # the actual crash: Lighting x NE x Q3
            elif is_q3 and is_lighting:
                multiplier *= 0.85  # lighting soft company-wide, not just NE
            elif is_q3:
                multiplier *= 0.95  # slight general softness elsewhere

            if random.random() > multiplier:
                continue

            quantity = random.randint(1, 6 if customer.segment == "wholesale" else 3)
            unit_price = product.unit_price * (0.95 if customer.segment == "wholesale" else 1.0)
            orders.append(SalesOrder(
                organization_id=org.id,
                order_date=order_date,
                customer_id=customer.id,
                region_id=customer.region_id,
                product_id=product.id,
                quantity=quantity,
                unit_price=round(unit_price, 2),
                total_amount=round(unit_price * quantity, 2),
                quarter=quarter_label,
            ))

    db.add_all(orders)
    await db.commit()
    print(f"  seeded {len(orders)} sales orders")


async def seed_prompts_agents_tools(db: AsyncSession, org: Organization):
    for name, description, template, variables in PROMPT_TEMPLATES:
        existing = await db.execute(select(Prompt).where(Prompt.name == name))
        if not existing.scalar_one_or_none():
            db.add(Prompt(name=name, version=1, description=description, template=template,
                           variables=variables))

    for name, description, prompt_ref, tools in AGENTS_SPEC:
        existing = await db.execute(
            select(Agent).where(Agent.organization_id == org.id, Agent.name == name)
        )
        if not existing.scalar_one_or_none():
            db.add(Agent(
                organization_id=org.id, name=name, description=description,
                system_prompt_ref=prompt_ref, model="gpt-4o-mini", temperature=0.2,
                max_iterations=8, allowed_tools=tools, status="active",
            ))

    for name, description, risk, timeout in TOOLS_SPEC:
        existing = await db.execute(select(ToolCatalogEntry).where(ToolCatalogEntry.name == name))
        if not existing.scalar_one_or_none():
            db.add(ToolCatalogEntry(
                organization_id=None, name=name, description=description,
                risk_level=risk, timeout_seconds=timeout, is_enabled=True,
            ))
    await db.commit()


async def seed_documents(db: AsyncSession, org: Organization, users: dict[str, User]):
    existing = await db.execute(select(Document).where(Document.organization_id == org.id))
    if existing.scalars().first():
        return

    analyst = users["emily@brightleafhome.com"]
    docs = [
        ("Lumina Living Q3 Pricing Snapshot", "web_capture",
         "Screenshot-derived notes: Lumina Living cut prices 30-40% on pendant and floor lamps "
         "in the North America - East region starting the first week of July 2026, running as a "
         "continuous 'Summer Lighting Sale' rather than a short flash sale."),
        ("Home Decor Market Outlook Q3 2026", "industry_report",
         "Third-party market note: overall home décor e-commerce demand was roughly flat "
         "quarter-over-quarter in Q3 2026, suggesting Brightleaf's Lighting-specific decline is "
         "competitive rather than macro-driven."),
        ("Q2 2026 Board Deck — Sales Summary", "internal",
         "Internal deck excerpt: Q2 2026 closed at $412K revenue, +8% QoQ, with Lighting as the "
         "fastest-growing category (+14% QoQ) prior to the Q3 reversal."),
    ]
    for title, source, preview in docs:
        db.add(Document(
            organization_id=org.id, title=title, source=source, owner_id=analyst.id,
            storage_key=f"documents/{uuid.uuid4()}.txt", content_preview=preview,
            permissions={"visibility": "organization"},
        ))
    await db.commit()


async def seed_memories(db: AsyncSession, org: Organization, users: dict[str, User]):
    existing = await db.execute(select(Memory).where(Memory.organization_id == org.id))
    if existing.scalars().first():
        return

    priya = users["priya@brightleafhome.com"]
    memories = [
        ("episodic", None,
         "In Q2 2026, a bundled-discount campaign (buy 2 textiles, get 10% off) run by the "
         "Notification Agent increased wholesale textile order size by ~22% without cutting "
         "per-unit price."),
        ("semantic", None,
         "Brightleaf's wholesale customers respond better to bundled/volume discounts than to "
         "straight price cuts, which erode margin without proportionally increasing volume."),
        ("organization", None,
         "Brightleaf Home Goods: founded 2019, Austin TX, 38 employees, primary channel is "
         "direct-to-consumer e-commerce plus a wholesale program for boutique retailers."),
        ("user", priya.id,
         "Priya (Sales Manager) prefers region-level breakdowns before category-level ones when "
         "reviewing revenue reports."),
    ]
    for scope, user_id, content in memories:
        db.add(Memory(organization_id=org.id, user_id=user_id, scope=scope, content=content))
    await db.commit()


async def seed_workflow_execution_trace(db: AsyncSession, org: Organization, users: dict[str, User]):
    owner = users["sarah@brightleafhome.com"]
    analyst = users["emily@brightleafhome.com"]

    existing = await db.execute(select(Workflow).where(Workflow.organization_id == org.id))
    if existing.scalar_one_or_none():
        return

    workflow = Workflow(
        organization_id=org.id,
        name="Quarterly Sales Decline Investigation",
        definition={
            "nodes": ["supervisor", "planner", "research", "data_agent", "verification",
                      "approval", "report", "notification"],
            "edges": [["supervisor", "planner"], ["planner", "research"], ["planner", "data_agent"],
                      ["research", "verification"], ["data_agent", "verification"],
                      ["verification", "report"], ["report", "approval"], ["approval", "notification"]],
        },
        created_by=owner.id,
    )
    db.add(workflow)
    await db.flush()

    started = datetime.now(timezone.utc) - timedelta(hours=3)
    execution = WorkflowExecution(
        organization_id=org.id,
        workflow_id=workflow.id,
        user_id=analyst.id,
        goal=("Analyze our Q3 2026 sales performance, identify the main reasons for the decline, "
              "research our competitors, compare findings with internal data, and prepare an "
              "executive report."),
        status="awaiting_approval",
        plan={
            "tasks": [
                {"id": "task_1", "agent": "research_agent",
                 "description": "Research competitor pricing/promo activity in Lighting, NA-East, Q3 2026",
                 "dependencies": []},
                {"id": "task_2", "agent": "data_agent",
                 "description": "Query Q1-Q3 2026 revenue by category and region",
                 "dependencies": []},
                {"id": "task_3", "agent": "verification_agent",
                 "description": "Cross-check research claims against internal sales data",
                 "dependencies": ["task_1", "task_2"]},
                {"id": "task_4", "agent": "report_agent",
                 "description": "Produce executive report with findings and recommendations",
                 "dependencies": ["task_3"]},
            ]
        },
        started_at=started,
        finished_at=None,
    )
    db.add(execution)
    await db.flush()

    task_defs = [
        ("task_1", "research_agent",
         "Research competitor pricing/promo activity in Lighting, NA-East, Q3 2026", [], "done",
         {"summary": "Lumina Living, a direct competitor, launched a 30-40% promotional price cut "
                     "across its pendant and floor lamp lines in the North America - East region "
                     "starting the first week of July 2026, run continuously through the quarter.",
          "sources": [{"title": "Lumina Living Summer Lighting Sale", "url": "https://example.com/lumina-sale"}]}),
        ("task_2", "data_agent",
         "Query Q1-Q3 2026 revenue by category and region", [], "done",
         {"finding": "Lighting revenue in North America - East fell approximately 61% from Q2 to Q3 "
                     "2026, while every other category/region combination declined 5-15% or held flat."}),
        ("task_3", "verification_agent",
         "Cross-check research claims against internal sales data", ["task_1", "task_2"], "done",
         {"passed": True,
          "note": "Timing of the internal revenue drop (starting early July) is consistent with the "
                  "competitor promotion start date found in research. No contradictions found."}),
        ("task_4", "report_agent",
         "Produce executive report", ["task_3"], "done",
         {"summary": "Q3 2026 revenue declined 18% company-wide, driven almost entirely by a 61% drop "
                     "in Lighting sales in North America - East, coinciding with Lumina Living's "
                     "aggressive summer price promotion in the same category and region.",
          "recommendation": "Consider a targeted, time-boxed promotional response in Lighting/NA-East "
                             "rather than a broad price cut, since other segments remain healthy."}),
    ]

    for external_id, agent, description, deps, status, output in task_defs:
        task = Task(
            workflow_execution_id=execution.id, external_id=external_id, agent=agent,
            description=description, dependencies=deps, required_tools=[], status=status,
        )
        db.add(task)
        await db.flush()
        tool_used = "web_search" if agent == "research_agent" else (
            "sql_query" if agent == "data_agent" else None)
        db.add(TaskExecution(
            task_id=task.id, agent_run_id=str(uuid.uuid4()),
            tool_calls=[{"tool": tool_used, "success": True}] if tool_used else [],
            output=output, status="completed",
            started_at=started, finished_at=started + timedelta(minutes=random.randint(2, 6)),
        ))

    # Cost tracking: one LLM call per agent step in this execution
    for provider, model, in_tok, out_tok in [
        ("openai", "gpt-4o-mini", 850, 320),   # planner
        ("openai", "gpt-4o-mini", 1650, 540),  # research
        ("openai", "gpt-4o-mini", 720, 180),   # data
        ("openai", "gpt-4o-mini", 980, 210),   # verification
        ("openai", "gpt-4o-mini", 1240, 680),  # report
    ]:
        cost = round(in_tok / 1_000_000 * 0.15 + out_tok / 1_000_000 * 0.60, 6)
        db.add(LLMUsage(
            organization_id=org.id, user_id=analyst.id, workflow_execution_id=execution.id,
            provider=provider, model=model, input_tokens=in_tok, output_tokens=out_tok,
            total_tokens=in_tok + out_tok, estimated_cost_usd=cost, latency_ms=random.uniform(600, 2200),
        ))

    # The report is done, but sending it to leadership is HIGH risk -> pending approval,
    # which is why the execution's own status above is "awaiting_approval".
    db.add(ApprovalRequest(
        organization_id=org.id,
        workflow_execution_id=str(execution.id),
        task_id="task_4",
        action="send_email",
        payload={
            "to": "sarah@brightleafhome.com, priya@brightleafhome.com",
            "subject": "Q3 2026 Sales Decline — Executive Report",
            "body": "Attached: analysis of the Q3 revenue decline, driven by Lighting/NA-East "
                    "competitive pressure from Lumina Living, with a recommended targeted response.",
        },
        risk_level="high",
        requested_by_agent="notification_agent",
    ))

    db.add(Evaluation(
        organization_id=org.id,
        dataset_name="research_agent_groundedness_v1",
        results={"cases_run": 12, "cases_passed": 11,
                 "notes": "One case flagged for an uncited numeric claim; groundedness prompt tightened."},
        score=0.917,
    ))

    await db.commit()
    return execution


async def seed_audit_logs(db: AsyncSession, org: Organization, users: dict[str, User]):
    existing = await db.execute(select(AuditLog).where(
        AuditLog.organization_id == org.id, AuditLog.action == "workflow.executed"
    ))
    if existing.scalars().first():
        return

    analyst = users["emily@brightleafhome.com"]
    owner = users["sarah@brightleafhome.com"]
    now = datetime.now(timezone.utc)
    entries = [
        (analyst.id, "auth.login", f"user:{analyst.id}", now - timedelta(hours=4)),
        (analyst.id, "workflow.executed", "workflow:quarterly-sales-decline-investigation",
         now - timedelta(hours=3)),
        (analyst.id, "tool.invoked", "tool:web_search", now - timedelta(hours=3, minutes=-2)),
        (analyst.id, "tool.invoked", "tool:sql_query", now - timedelta(hours=3, minutes=-3)),
        (analyst.id, "approval.requested", "approval:send_email", now - timedelta(hours=2, minutes=45)),
        (owner.id, "auth.login", f"user:{owner.id}", now - timedelta(hours=1)),
    ]
    for user_id, action, resource, ts in entries:
        log = AuditLog(organization_id=org.id, user_id=user_id, action=action, resource=resource,
                        log_metadata={}, created_at=ts)
        db.add(log)
    await db.commit()


async def main():
    async with AsyncSessionLocal() as db:
        org = await get_or_create_org(db)
        users = await seed_users(db, org)
        regions, categories, products, customers = await seed_business_data(db, org)
        await seed_sales_orders(db, org, regions, categories, products, customers)
        await seed_prompts_agents_tools(db, org)
        await seed_documents(db, org, users)
        await seed_memories(db, org, users)
        await seed_workflow_execution_trace(db, org, users)
        await seed_audit_logs(db, org, users)

        print(f"Seeded organization: {org.name} ({org.id})")
        print(f"Seeded {len(users)} users. Demo password for all: {DEMO_PASSWORD}")
        print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
