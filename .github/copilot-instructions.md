# AI Cost Intelligence Copilot - Repository Instructions

You are assisting on an enterprise AI Cost Intelligence Copilot.
This system monitors spend, SLA performance, resource usage, and financial operations, detects anomalies and cost leakages, explains them via chat and graphs, and can trigger approval-based corrective actions.

Your job: write production-grade code, tests, and docs that align with the architecture and patterns described here.

---

## 1. Product Overview

The product is an agentic AI system that:

- Ingests enterprise data (ERP, procurement, invoices, SLAs, logs, infra usage, financial transactions).
- Runs multiple agents (Spend, SLA, Resource, FinOps) over this data.
- Uses RAG over enterprise documents and records.
- Builds a graph model (vendors, invoices, teams, resources, SLA tasks, risk events).
- Exposes a conversational Copilot UI plus a Graph Intelligence Studio.
- Calculates quantifiable financial impact for each issue:
  - Impact = Amount x Confidence x RecoveryProbability.
- Can propose and execute actions through an approval workflow.

When you generate code or explanations, always preserve:

- Data -> Insight -> Impact (INR/currency) -> Action -> Savings.

---

## 2. Tech Stack and Key Libraries

Frontend

- Next.js (App Router where possible).
- React, TypeScript where possible.
- Tailwind CSS + shadcn/ui + Radix primitives.
- React Query (TanStack Query) for server state.
- Zustand for local UI state.
- React Flow for graph visualizations.

Backend

- Python and FastAPI in this repository.
- Agents and orchestration via LangGraph (or similar graph-based agent framework).
- REST APIs via FastAPI.
- Vector DB for RAG.
- Relational DB for app data (Postgres preferred).

AI / Agents

- LLM(s) accessed via provider SDK.
- RAG pipeline: embeddings, vector search, context assembly.
- Agents: Spend, SLA, Resource, Finance.
- Orchestrator: LangGraph workflow with explicit state object.

Use idiomatic patterns for these tools and avoid ad-hoc one-off styles.

---

## 3. High-Level Architecture

### 3.1 Frontend Structure

Expected directory layout:

```bash
frontend/
  app/
    layout.tsx
    page.tsx                  # Command Center
    copilot/
      page.tsx                # Copilot Workspace
    graph/
      page.tsx                # Graph Intelligence Studio
    playbooks/
      page.tsx
    approvals/
      page.tsx
  components/
    layout/
      AppShell.tsx
      Sidebar.tsx
      Topbar.tsx
    copilot/
      ChatWindow.tsx
      MessageBubble.tsx
      ContextPanel.tsx
    graph/
      GraphCanvas.tsx
      NodeInspector.tsx
      GraphLegend.tsx
    insights/
      InsightCard.tsx
      ImpactChip.tsx
      KpiTile.tsx
    playbooks/
      PlaybookList.tsx
      PlaybookDetail.tsx
    approvals/
      ApprovalCard.tsx
  store/
    copilotStore.ts
    uiStore.ts
  lib/
    apiClient.ts
    formatters.ts
    featureFlags.ts
```

When adding new UI, respect this structure:

- Pages in app/.
- Reusable components in components/<domain>/.
- Client-side state in store/.
- Cross-cutting helpers in lib/.

### 3.2 Backend Structure

```bash
backend/
  api/
    chat/
      handler.(ts|py)
    actions/
      handler.(ts|py)
    graph/
      handler.(ts|py)
  agents/
    spend_agent.(ts|py)
    sla_agent.(ts|py)
    resource_agent.(ts|py)
    finance_agent.(ts|py)
  rag/
    embeddings.(ts|py)
    retriever.(ts|py)
  graph_builder/
    builder.(ts|py)
  models/
    entities.(ts|py)
  services/
    impact_calculator.(ts|py)
    approval_service.(ts|py)
  langgraph/
    workflow.(ts|py)
    state.(ts|py)
```

Use clear separation:

- APIs only coordinate HTTP concerns and delegate to services.
- Agents focus on domain logic (detect anomalies, classify risk, etc.).
- RAG components encapsulate embeddings/search.
- Graph builder converts findings to node-edge structures.

---

## 4. Domain Model and Core Concepts

### 4.1 Agents

Agents and roles:

- Spend Agent: detect duplicate payments, rate anomalies, off-contract spend, suspicious vendors.
- SLA Agent: predict breaches from operational signals; surface upcoming penalties.
- Resource Agent: find under-utilized or idle tools/infrastructure; suggest consolidation or shutdown.
- Finance Agent: reconcile transactions, flag discrepancies, perform variance analysis with root-cause hints.

Each agent should:

- Take a shared state object.
- Read from context_docs, structured data, and RAG results.
- Append to anomalies, recommendations, actions, financial_impact.

### 4.2 Agent State

Use a strongly typed state:

```ts
export interface AgentState {
  query: string;
  contextDocs: Array<unknown>;
  anomalies: Array<unknown>;
  graphData: Record<string, unknown>;
  recommendations: Array<unknown>;
  actions: Array<unknown>;
  financialImpact: number;
}
```

When extending, keep it additive and backward compatible.

### 4.3 Graph Model

Graph node types:

- Vendor
- Invoice
- Team
- Resource
- SlaTask
- RiskEvent

Edge types:

- PAID_TO
- ASSIGNED_TO
- USES_RESOURCE
- CAUSES_RISK
- DUPLICATE_OF

Graph JSON schema:

```json
{
  "nodes": [
    { "id": "vendor_1", "type": "vendor", "data": { "name": "Vendor A" } },
    { "id": "invoice_1", "type": "invoice", "data": { "amount": 50000 } }
  ],
  "edges": [
    { "id": "e1", "source": "vendor_1", "target": "invoice_1", "label": "PAID_TO" }
  ]
}
```

Frontend should map this directly to React Flow.

### 4.4 Financial Impact

Always compute and surface impact as:

```ts
impact = amount * confidence * recoveryProbability;
```

Include:

- Raw amount (for example, total duplicate spend).
- Confidence (0-1).
- Recovery probability (0-1).
- Derived impact.

When generating UI or APIs, make these fields explicit so we can show Show the math in the UI.

---

## 5. API Contracts

When implementing or consuming APIs, use these shapes.

### 5.1 /api/chat (POST)

Input:

```json
{
  "query": "Show duplicate vendor payments",
  "context": {
    "timeRange": "last_90_days",
    "filters": {
      "region": "APAC"
    }
  }
}
```

Output shape to preserve:

```json
{
  "messages": [
    {
      "type": "summary",
      "text": "We found 12 duplicate payments to Vendor A totaling INR 50,000."
    }
  ],
  "insights": [
    {
      "id": "ins_123",
      "domain": "spend",
      "title": "Duplicate payments to Vendor A",
      "description": "12 invoices appear to be duplicates in the last 90 days.",
      "impact": {
        "currency": "INR",
        "amount": 50000,
        "confidence": 0.9,
        "recoveryProbability": 0.8,
        "calculatedImpact": 36000
      },
      "entities": ["vendor:Vendor A", "invoice:INV-101", "invoice:INV-202"],
      "riskLevel": "high"
    }
  ],
  "graph": { "nodes": [], "edges": [] },
  "actions": [
    {
      "id": "act_block_vendor",
      "label": "Block further payments to Vendor A",
      "riskLevel": "high",
      "approvalRequired": true
    }
  ]
}
```

### 5.2 /api/action (POST)

- Used to execute actions (for example, block payment, reassign workload, shutdown resource, create ticket).
- Must record audit info and route through approval depending on risk level.

### 5.3 /api/graph (GET)

- Returns node-edge data for the Graph Intelligence Studio.
- Support filters: timeRange, domain, riskLevel, entityIds.

---

## 6. Frontend UX Rules for Copilot

When generating React/TSX:

- Always integrate with:
  - React Query for data fetching (useQuery, useMutation).
  - Zustand for UI state (filters, selected entities).
- Keep components small and composable. Container components should orchestrate data fetching and state; presentational components should stay dumb.

Key UI behavior for the Copilot workspace:

- Chat answer should come with:
  - A concise summary.
  - Key metrics (chips).
  - A Show math section for financial impact.
  - Links to underlying entities (vendor, invoice, team).
- Right-hand context panel should update based on the last answer:
  - Table of affected items.
  - Small chart or graph preview.
- Every insight should offer at least one next action (open in graph, open playbook, request approval, execute).

---

## 7. Coding Style and Quality

General guidelines:

- Use TypeScript types/interfaces generously at module boundaries.
- Prefer pure functions for business logic; keep side effects localized.
- For React:
  - Use functional components and hooks only.
  - Avoid unnecessary re-renders by memoizing where needed.
- Write meaningful names; avoid abbreviations that hide domain meaning.

Testing:

- For backend logic (agents, impact calculations), write unit tests.
- For frontend, at least test key components and hooks (especially Copilot chat logic and graph mapping).

---

## 8. How to Ask Copilot for Help (Prompting)

When asking for code changes or new features in this repo, follow these patterns:

- Be explicit about domain and flow.
  - Add a new Spend Agent rule that detects invoices where unit price is 20% higher than the median for that vendor in the last 6 months.

- Specify surface.
  - In the Copilot page, add a Show math expandable panel under each AI response using existing ImpactChip and a new ImpactDetails component.

- Reuse patterns.
  - Follow existing file patterns and naming conventions instead of inventing new ones.

---

## 9. Non-Goals / Things to Avoid

- Do not add new major dependencies without clear justification.
- Do not bypass the agent orchestration (LangGraph) with one-off LLM calls mixed directly in UI.
- Do not hardcode dummy credentials, secrets, or tenant-specific logic.
- Avoid implementing new business logic directly in React components; put it into services/agents.

---

If you are unsure about where to put a new piece of logic:

1. Prefer domain-specific modules (agents/, services/, graph_builder/).
2. Keep APIs thin, UI thinner, and business logic in domain layers.
3. Follow the patterns of the closest existing module.
