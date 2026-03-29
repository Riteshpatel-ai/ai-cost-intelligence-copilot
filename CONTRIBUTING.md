# Contributing to AI Cost Intelligence Copilot

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## 🤝 Code of Conduct

We are committed to providing a welcoming and inspiring community for all. Please read and adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## 📋 How to Contribute

### 1. Report Bugs

Found a bug? Please open an issue with:

- **Title:** Clear, concise description of the bug
- **Description:** What happened and what you expected
- **Steps to Reproduce:** Exact steps to reproduce the issue
- **Environment:** OS, Python/Node version, relevant dependencies
- **Screenshots:** If applicable

**Example:**
```
Title: Chat copilot returns 500 error on empty query

Description:
When submitting an empty query string, the chat endpoint returns 
HTTP 500 instead of a validation error.

Steps to Reproduce:
1. Open copilot UI at http://localhost:3000/copilot
2. Click Send without typing any text
3. See 500 Internal Server Error

Environment:
- OS: Windows 11
- Python: 3.10.5
- Node: 18.14.0
```

### 2. Suggest Features

Have an idea? Please open an issue with:

- **Title:** Feature description
- **Use Case:** Why this feature is needed
- **Proposed Solution:** How it should work
- **Alternatives Considered:** Other approaches

### 3. Submit Code Changes

#### Step 1: Fork & Clone

```bash
git clone https://github.com/YourUsername/ai-cost-intelligence-copilot.git
cd ai-cost-intelligence-copilot
git remote add upstream https://github.com/OriginalOwner/ai-cost-intelligence-copilot.git
```

#### Step 2: Create Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

**Branch Naming Convention:**
- Features: `feature/description` (e.g., `feature/add-email-notifications`)
- Bug fixes: `fix/description` (e.g., `fix/duplicate-detection-accuracy`)
- Documentation: `docs/description` (e.g., `docs/api-reference`)
- Tests: `test/description` (e.g., `test/agent-integration`)

#### Step 3: Make Changes

Follow code style guidelines below.

#### Step 4: Commit

```bash
git commit -m "type: description"
```

**Commit Message Format:**
```
feat: add SLA breach notifications
fix: correct duplicate detection algorithm
docs: update API documentation
test: add tests for spend agent
chore: update dependencies
refactor: simplify graph builder logic
perf: optimize FAISS index search
```

Follow [Conventional Commits](https://www.conventionalcommits.org/).

#### Step 5: Push & Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then open a Pull Request on GitHub with:
- Clear description of changes
- Link to related issue (if applicable)
- Screenshots or demo (if UI change)
- Not a breaking change? Remove the note.

---

## 📐 Code Style

### Python (Backend)

We use **Black**, **isort**, and **flake8**:

```bash
# Install tools
pip install black isort flake8 mypy

# Format code
black backend/
isort backend/

# Check for issues
flake8 backend/
mypy backend/
```

**Style Rules:**
- Line length: 100 characters
- String quotes: Double quotes
- Imports: Grouped (stdlib, third-party, local)
- Type hints: Required for public functions

**Example:**
```python
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException
from backend.services import report_service

def calculate_duplicate_impact(
    amount: float,
    confidence: float,
    recovery_prob: float,
) -> Dict[str, float]:
    """Calculate financial impact of duplicate detection.
    
    Args:
        amount: Total duplicate amount in INR
        confidence: Detection confidence (0-1)
        recovery_prob: Recovery probability (0-1)
    
    Returns:
        Dictionary with impact metrics
    """
    return {
        "gross_amount": amount,
        "confidence": confidence,
        "recoverable": amount * confidence * recovery_prob,
    }
```

### JavaScript/TypeScript (Frontend)

We use **ESLint**, **Prettier**, and **TypeScript**:

```bash
# Install tools
npm install --save-dev eslint prettier typescript

# Format code
npx prettier --write .
npx eslint . --fix

# Check for issues
npx eslint .
npx tsc --noEmit
```

**Style Rules:**
- Semicolons: Required
- Quote style: Double quotes
- Components: Use functional components + hooks
- Props: Type with TypeScript interfaces
- Files: camelCase for files, PascalCase for components

**Example:**
```typescript
import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";

interface ChatMessage {
  id: string;
  text: string;
  timestamp: Date;
  sender: "user" | "assistant";
}

export const ChatWindow: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const { mutate: sendMessage } = useMutation({
    mutationFn: async (text: string) => {
      const response = await fetch("/api/chat", {
        method: "POST",
        body: JSON.stringify({ query: text }),
      });
      return response.json();
    },
  });

  return (
    <div className="chat-container">
      {messages.map((msg) => (
        <div key={msg.id} className={`message ${msg.sender}`}>
          {msg.text}
        </div>
      ))}
    </div>
  );
};
```

---

## ✅ Testing Requirements

All contributions must include tests:

### Backend Tests

```bash
cd backend
pytest tests/ -v --cov=backend

# Run specific test
pytest tests/unit/test_spend_agent.py -v
```

**Test Structure:**
```
tests/
├── unit/
│   ├── test_spend_agent.py
│   ├── test_sla_agent.py
│   └── test_financial_impact.py
├── integration/
│   ├── test_chat_endpoint.py
│   └── test_agent_workflow.py
└── conftest.py  # Fixtures
```

**Example:**
```python
import pytest
from backend.agents.spend_agent import SpendAgent

@pytest.fixture
def sample_invoices():
    return [
        {"vendor": "Acme", "amount": 50000, "date": "2026-03-01"},
        {"vendor": "Acme", "amount": 50000, "date": "2026-03-01"},  # duplicate
    ]

def test_detect_duplicates(sample_invoices):
    agent = SpendAgent(sample_invoices)
    duplicates = agent.detect_duplicates()
    assert len(duplicates) == 1
    assert duplicates[0]["amount"] == 50000
```

### Frontend Tests

```bash
cd frontend
npm test
npm run test:e2e

# Run specific test
npm test -- ChatWindow.test.tsx
```

**Test Structure:**
```
frontend/__tests__/
├── unit/
│   ├── ChatWindow.test.tsx
│   └── GraphPanel.test.tsx
├── integration/
│   ├── chat-flow.test.tsx
│   └── approval-workflow.test.tsx
└── fixtures/
```

**Example:**
```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { ChatWindow } from "@/components/copilot/ChatWindow";

describe("ChatWindow", () => {
  it("sends message on button click", async () => {
    render(<ChatWindow />);

    const input = screen.getByPlaceholderText(/ask anything/i);
    fireEvent.change(input, { target: { value: "show duplicates" } });
    fireEvent.click(screen.getByText(/send/i));

    await screen.findByText(/analyzing/i);
  });
});
```

---

## 📝 Documentation

All features must be documented:

1. **Docstrings** — Every function/class must have docstring
2. **README** — Update README.md for new features
3. **API Docs** — Add Swagger/OpenAPI docs for new endpoints
4. **Comments** — Complex logic should have explanatory comments

**Docstring Format (Python):**
```python
def calculate_impact(amount: float, confidence: float, recovery: float) -> float:
    """Calculate risk-weighted financial impact.
    
    Uses the formula: Impact = Amount × Confidence × RecoveryProbability
    
    Args:
        amount: Total exposure amount in INR
        confidence: Detection confidence score (0.0-1.0)
        recovery: Likelihood of recovery (0.0-1.0)
    
    Returns:
        Calculated impact in INR
    
    Examples:
        >>> calculate_impact(100000, 0.9, 0.8)
        72000.0
    """
    return amount * confidence * recovery
```

---

## 🔄 Pull Request Process

1. **Before submitting:**
   - Run tests: `pytest` (backend) or `npm test` (frontend)
   - Run linter: `black`, `eslint`
   - Update docs if needed
   - Update CHANGELOG.md

2. **When submitting PR:**
   - Provide clear title and description
   - Link related issues
   - Add screenshots/demos (if UI change)
   - Request reviewers

3. **During review:**
   - Respond to feedback promptly
   - Don't force-push unless asked
   - Mark conversations as resolved when done

4. **After merge:**
   - Your changes will be deployed to staging
   - Great job! 🎉

---

## 🐢 Development Workflow

### Local Setup

```bash
# Clone
git clone https://github.com/YourUsername/ai-cost-intelligence-copilot.git
cd ai-cost-intelligence-copilot

# Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
cd backend && uvicorn main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Database (Optional)

```bash
# Using Docker Compose
docker-compose up -d postgres

# Using local installation
createdb cost_copilot
psql cost_copilot < schema.sql
```

### Common Tasks

```bash
# Run all tests
pytest tests/ && npm test

# Format all code
black backend/ && npx prettier --write .

# Generate API docs
# Navigate to http://localhost:8000/docs

# Build for production
npm run build
pip install -r requirements.txt
```

---

## 🆘 Need Help?

- **Questions?** Open a [GitHub Discussion](https://github.com/YourUsername/ai-cost-intelligence-copilot/discussions)
- **Issues?** Check [existing issues](https://github.com/YourUsername/ai-cost-intelligence-copilot/issues)
- **Security?** See [SECURITY.md](SECURITY.md)

---

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## 🎯 What We're Looking For

- **Bug fixes** — Any Severity
- **Performance improvements** — Especially in agent workflows
- **Documentation** — Always welcome!
- **Feature additions** — Aligned with roadmap
- **Test coverage** — Critical

---

**Thank you for contributing! 🚀**
