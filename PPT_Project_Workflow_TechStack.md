# AI Cost Intelligence Copilot

## 1) One-line Project Definition
AI Cost Intelligence Copilot is an enterprise decision-support system that converts operational and financial data into actionable cost-saving recommendations with risk-based approval routing.

Core value chain:
Data -> Insight -> Impact (INR) -> Action -> Savings

---

## 2) Business Problem It Solves
Organizations lose money through hidden leakage across spend, SLA, resources, and finance operations.

Typical pain points:
- Duplicate or suspicious payments
- SLA breach penalties
- Underutilized resources and wasted capacity
- Reconciliation mismatches and unexplained variance
- Slow decision making due to fragmented data and non-explainable analytics

This project addresses these by combining:
- Conversational querying
- Multi-agent anomaly detection
- RAG-grounded context
- Graph-based relationship intelligence
- Governance-ready action and audit workflow

---

## 3) High-Level Architecture (Layered View)

### A. Presentation Layer (Frontend)
- Next.js app with command center dashboard
- Chat workspace for natural language investigation
- Graph risk analyzer panel
- Action and Approval desk
- Explainability timeline and KPI tiles

### B. API Orchestration Layer
- Next.js API routes act as proxy/failover between UI and backend
- FastAPI service provides business APIs

### C. Intelligence Layer
- LangGraph workflow orchestration
- Domain agents:
  - Spend Agent
  - SLA Agent
  - Resource Agent
  - Finance Agent
- Specialized analyzers for uploaded row-level data
- Pattern detection and duplicate-impact computation

### D. Knowledge Layer (RAG)
- Sentence Transformer embeddings
- FAISS vector similarity retrieval
- LLM-backed answer generation with fallback behavior

### E. Data + Governance Layer
- Intake event store (JSONL)
- Latest upload snapshot store
- Vector document store
- Gmail state tracking
- Auto-generated audit report artifact + PDF
- Role-based approval requirement by risk level

---

## 4) End-to-End Runtime Workflow (Chat Query)

1. User asks a question in UI chat.
2. Frontend stores the message and calls Next.js API route `/api/chat`.
3. Proxy selects backend origin with failover support (tries multiple candidates).
4. FastAPI `/api/chat` receives query and optional uploaded rows.
5. Backend decides route:
   - Uploaded data path (duplicate/spend/SLA/action/report style queries), or
   - LangGraph orchestration path.
6. LangGraph executes pipeline:
   - Ingestion node
   - RAG retrieval and context answer
   - Parallel domain agent analysis
   - Anomaly merge
   - Graph construction
   - Financial impact calculation
   - Risk and approval decision
   - Explainability timeline generation
7. Response payload returned with:
   - Summary text
   - Anomalies
   - Recommendations
   - Graph nodes/edges
   - Financial impact + breakdown
   - Risk and approval requirement
   - Actions
   - Explainability traces
8. Report service stores latest audit artifact and attaches report metadata in chat response.
9. Frontend hydrates KPI cards, insights, actions, graph, and chat transcript.
10. User can download latest audit PDF via `/api/reports/latest-pdf` (through frontend proxy).

---

## 5) Ingestion Workflows

### A. Manual File Upload Workflow
1. User uploads CSV/XLSX from UI.
2. FastAPI ingest endpoint validates file type and parses content.
3. Ingestion event is logged.
4. Latest upload snapshot is saved for subsequent chat analysis.
5. Chat requests can directly analyze uploaded rows without re-upload.

### B. Gmail-Driven Workflow
1. Gmail watch/webhook/manual fetch triggers pipeline.
2. Gmail client retrieves latest messages.
3. Project relevance filter keeps only finance/cost/SLA-related content.
4. Attachment extractor parses CSV/XLSX/PDF text.
5. Relevant content is stored into vector document store.
6. Workflow runs for anomaly/risk/impact recommendation generation.
7. Events and processing state are persisted for traceability.

---

## 6) LangGraph Workflow Details

Primary state includes:
- query
- docs/context_docs
- invoices/sla_logs/resources/transactions
- anomalies
- graph
- financial_impact_breakdown
- financial_impact
- risk_level
- approval_required
- recommendations
- actions
- explainability

Node sequence (conceptual):
- START -> ingestion -> rag -> parallel agents (spend/sla/resource/finance) -> merge_anomalies -> build_graph -> compute_impact -> decision -> explainability -> END

Risk policy:
- High risk: finance approval
- Medium risk: manager approval
- Low risk: auto-execute

---

## 7) Financial Impact Logic

The system uses quantified impact math to prioritize decisions:

impact = amount * confidence * recoveryProbability

Breakdown categories include:
- Duplicate payments
- SLA penalties
- Resource waste
- Variance risk
- Total impact

This supports:
- Prioritization by materiality
- Explainable ROI-based approvals
- Audit-ready decision reasoning

---

## 8) Graph Intelligence Model

Entity types in graph:
- Vendor
- Invoice
- SLA task
- Risk event
- Resource/Team context

Edge semantics:
- PAID_TO
- DUPLICATE_OF
- CAUSES_RISK
- Additional relationship edges from anomaly linkage

Graph output is consumed by frontend graph canvas for interactive risk visualization.

---

## 9) Explainability and Governance

Explainability artifacts:
- Confidence traces per signal category
- Action audit timeline with stage, actor, action, outcome

Governance controls:
- Role-based approval routing
- Action endpoint status (`executed` vs `pending_approval`)
- Persisted report artifact for management review
- PDF report generation for compliance communication

---

## 10) Professional Audit Report Pipeline

Generated report includes:
- Executive summary
- Audit scope and objective
- Data sources and methodology
- Key findings and severity
- Financial materiality
- Recommended action plan with ownership and TAT
- Compliance and controls evidence
- Auditor conclusion and review cycle

PDF characteristics:
- Structured sections
- Branded header/footer with pagination
- Summary cards and tabular findings
- Governance-ready language for leadership presentation

---

## 11) API Surface (Important Endpoints)

Core backend APIs:
- POST `/api/chat` -> main copilot inference + report metadata
- POST `/api/action` -> executes or queues action by risk
- GET `/api/graph` -> graph payload
- POST `/api/ingest/upload` -> CSV/XLSX ingestion
- GET `/api/ingest/events` -> ingestion activity log
- POST `/api/gmail/manual/fetch-latest` -> latest Gmail processing
- POST `/api/gmail/webhook` -> webhook-driven Gmail event processing
- GET `/api/reports/latest` -> latest report JSON
- GET `/api/reports/latest-pdf` -> latest report PDF download

Frontend API proxies:
- POST `/api/chat`
- GET `/api/reports/latest-pdf`

Both frontend proxies include backend failover behavior.

---

## 12) Tech Stack (Detailed)

### Frontend
- Next.js 16
- React 19
- Zustand (client state)
- React Flow (graph visualization)
- Tailwind CSS 4 + PostCSS + Autoprefixer

### Backend
- FastAPI
- Uvicorn
- Pydantic
- LangGraph / LangChain
- Custom domain agents and services

### AI / RAG
- sentence-transformers (all-MiniLM-L6-v2)
- FAISS (vector search)
- OpenAI-compatible client (with Groq-style endpoint support)

### Data Processing
- NumPy, SciPy
- openpyxl (Excel ingestion)
- pypdf (PDF extraction)
- python-multipart (file uploads)

### Integrations
- Gmail API client libraries:
  - google-api-python-client
  - google-auth-httplib2
  - google-auth-oauthlib

### Reporting
- reportlab (PDF generation)

### Testing and Quality
- pytest
- Structured logging + correlation IDs
- Rate limiting (slowapi)

---

## 13) Repository Module Map

- `frontend/`
  - UI pages, components, state store, API proxy routes
- `backend/`
  - API routers, agents, RAG, graph builder, services, schemas
- `langgraph/`
  - workflow compatibility wrapper and state module
- `data/`
  - ingestion snapshots, events, generated report artifacts
- `tests/`
  - backend behavior and contract tests

---

## 14) Security, Reliability, and Controls

Implemented controls:
- CORS policy configuration
- Request correlation IDs and structured logging
- API rate limiting
- Failover-capable frontend proxy to backend candidates
- Validation via Pydantic models and input constraints
- Event and state persistence for traceability

Operational notes:
- If multiple backend instances/ports exist, frontend proxy candidate order controls failover.
- Report generation depends on latest stored report payload.

---

## 15) Suggested PPT Slide Plan (Ready-to-Use)

1. Problem and Opportunity
2. Product Vision: Data -> Insight -> Impact -> Action -> Savings
3. System Architecture (layered)
4. Runtime Flow (chat query to decision)
5. Agentic Intelligence (4 domain agents + explainability)
6. RAG and Graph Intelligence
7. Ingestion Workflows (upload + Gmail)
8. Governance and Approval Model
9. Audit Report and Compliance Outputs
10. Tech Stack and Engineering Choices
11. Reliability and Operational Learnings
12. Roadmap and Next Steps

---

## 16) Roadmap Recommendations (For PPT Closing)

Short-term:
- Stabilize process management for backend/frontend startup consistency
- Expand contract tests around proxy failover and report versioning
- Add report version tags in file naming for easier stakeholder tracking

Mid-term:
- Move from local file stores to production-grade DB/object storage
- Add role-based authentication and tenant isolation
- Add monitoring dashboards (latency, error rate, anomaly precision)

Long-term:
- Policy-driven autonomous remediation with stricter approval gates
- Deeper graph analytics (multi-hop risk propagation)
- Continual learning loop from approved/rejected actions

---

## 17) Speaker Notes (Quick Narrative)

"This platform is not just a chatbot. It is an explainable decision engine combining RAG, agent orchestration, graph intelligence, and audit-grade governance. It ingests structured and unstructured enterprise data, detects financially material anomalies, quantifies impact in INR, routes actions through approvals based on risk, and generates professional audit reports for management and compliance."