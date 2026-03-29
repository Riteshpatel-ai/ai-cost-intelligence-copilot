# AI Cost Intelligence Copilot

![Version](https://img.shields.io/badge/Version-1.0.0-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Node](https://img.shields.io/badge/Node-18+-green.svg)

**Enterprise-Grade AI-Powered Cost Optimization Platform**

An intelligent, agentic system that monitors enterprise spending, detects anomalies, predicts SLA breaches, optimizes resource utilization, and surfaces actionable cost-saving opportunities through a conversational interface and advanced graph analytics.

## 🎯 Overview

The AI Cost Intelligence Copilot combines **multi-agent orchestration**, **Retrieval-Augmented Generation (RAG)**, **graph-based relationship analytics**, and **financial impact modeling** to help enterprises recover millions in cost leakage within weeks of deployment.

### Key Capabilities

- **Duplicate Payment Detection** — Identify 95%+ of duplicate invoices with ML-enhanced analysis
- **SLA Breach Prediction** — Forecast service disruptions before penalties occur
- **Resource Optimization** — Right-size infrastructure and eliminate idle capacity
- **Financial Anomaly Detection** — Surface off-contract spending, rate inflation, vendor discrepancies
- **Conversational Intelligence** — Chat-based copilot with conversational RAG; ask questions naturally
- **Graph Analytics** — Visualize complex cost relationships (vendor→invoice→team→resource) in interactive network
- **Approval Workflows** — High-risk actions route through governance with full audit trails

## 💰 Impact at a Glance

| Metric | Conservative | Likely | Optimistic |
|--------|--------------|--------|-----------|
| **Year 1 Recovery** | ₹4.17 Cr | ₹6.91 Cr | ₹9.42 Cr |
| **ROI** | 305% | 571% | 815% |
| **Payback Period** | 3 months | 1.8 months | 1.3 months |
| **5-Year NPV** | ₹24.5 Cr | ₹40.8 Cr | ₹56.2 Cr |

*Detailed business impact analysis available in [BUSINESS_IMPACT_MODEL_AUDIT.md](BUSINESS_IMPACT_MODEL_AUDIT.md)*

---

## 🏗️ Architecture

### Technology Stack

**Frontend**
- **Next.js 16.2.1** + **React 19.2.0** — Modern, responsive UI with server-side rendering
- **Tailwind CSS 4.1.12** — Utility-first styling with accessibility focus
- **React Flow 11.11.4** — Interactive graph visualization of cost relationships
- **React Query (TanStack Query)** — Server state management with smart caching
- **Zustand** — Lightweight client-side state management

**Backend**
- **FastAPI** — High-performance async REST API framework
- **Python 3.10+** — Type-safe, maintainable backend code
- **LangGraph** — Graph-based agentic workflow orchestration
- **sentence-transformers** — Efficient semantic embeddings (all-MiniLM-L6-v2)
- **FAISS** — Fast vector similarity search (in-memory, zero external deps)
- **PostgreSQL** (recommended) — Relational data store for transactional integrity
- **reportlab** — Professional audit-ready PDF generation

**Agents & AI**
- **Spend Agent** — Duplicate detection, rate anomaly detection, off-contract spend
- **SLA Agent** — Breach prediction, penalty forecasting, remediation recommendations
- **Resource Agent** — Idle resource detection, consolidation recommendations, TCO analysis
- **Finance Agent** — Transaction reconciliation, variance analysis, root-cause hints
- **OpenAI API** (optional) — GPT-4 for RAG enrichment & natural language explanations

---

## 📦 Project Structure

```
CostOptimization/
├── frontend/                    # Next.js React application
│   ├── app/                    # App Router pages
│   ├── components/             # Reusable React components
│   ├── store/                  # Zustand state management
│   └── lib/                    # Utility functions
├── backend/                     # FastAPI Python application
│   ├── api/                    # REST API endpoints
│   ├── agents/                 # Domain agents
│   ├── rag/                    # RAG pipeline
│   ├── graph_builder/          # Graph intelligence
│   ├── services/               # Business logic
│   └── main.py                 # FastAPI entrypoint
├── langgraph/                  # Workflow orchestration
├── tests/                      # Test suite
├── data/                       # Sample datasets
├── BUSINESS_IMPACT_MODEL_AUDIT.md
└── README.md
```

---

## ⚡ Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Git

### Installation

#### 1. Clone Repository

```bash
git clone https://github.com/YourUsername/ai-cost-intelligence-copilot.git
cd ai-cost-intelligence-copilot
```

#### 2. Backend Setup

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate      # macOS/Linux

pip install -r backend/requirements.txt

cd backend
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Backend: **http://127.0.0.1:8000**  
API Docs: **http://127.0.0.1:8000/docs**

#### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend: **http://localhost:3000**

---

## 🚀 Features

### 1. Conversational Cost Intelligence
Ask natural language questions about spending, SLA risks, and optimization opportunities.

### 2. Duplicate Payment Detection
Multi-algorithm approach identifies 95%+ of duplicate invoices with confidence scoring.

### 3. SLA Breach Prediction
ML-based forecasting predicts service disruptions and quantifies penalty exposure.

### 4. Resource Optimization
Infrastructure intelligence detects idle capacity and recommends consolidation.

### 5. Graph Intelligence
Visual relationship mapping shows cost drivers, ownership, and risk propagation.

### 6. Professional Reports
Audit-ready PDFs with executive summaries, findings, impact breakdown, and signatures.

---

## 📊 API Endpoints

### Chat Endpoint

**POST** `/api/chat`

```json
{
  "query": "Show duplicate vendor payments last 90 days",
  "context": {
    "timeRange": "last_90_days",
    "filters": { }
  }
}
```

### Action Execution

**POST** `/api/action` — Execute recommendations with approval routing

### Graph Intelligence

**GET** `/api/graph?timeRange=last_90_days&riskLevel=high` — Node-edge data

---

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests
cd frontend
npm test
```

---

## 🔐 Security

- ✅ TLS 1.3 encryption in transit
- ✅ Role-based access control (RBAC)
- ✅ PII masking for non-executives
- ✅ Full audit trails
- ✅ SOC 2 Type II ready

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
git checkout -b feature/your-feature
git commit -m "feat: description"
git push origin feature/your-feature
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

## 📚 Documentation

- **[BUSINESS_IMPACT_MODEL_AUDIT.md](BUSINESS_IMPACT_MODEL_AUDIT.md)** — Financial ROI analysis
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Development guidelines
- **[SECURITY.md](SECURITY.md)** — Security policy

---

## 📞 Contact

- 📧 Email: Ritesh9878patel@gmail.com
- 🌐 Website: https://riteshpatel-ai.github.io/profile

---

**⭐ If you find this project useful, please give it a star!**
