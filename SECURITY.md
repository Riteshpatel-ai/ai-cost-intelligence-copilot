# Security Policy

## 🔐 Security Commitment

The AI Cost Intelligence Copilot takes security seriously. We commit to:

- **Transparency** — Disclosing security issues responsibly
- **Timeliness** — Responding to reports within 48 hours
- **Rigor** — Following industry-standard security practices
- **Accountability** — Maintaining comprehensive audit trails

---

## 🚨 Reporting Security Issues

**Do NOT open public issues for security vulnerabilities.**

Instead, please email security details to: **security@costintelligence.ai**

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will:
1. Acknowledge receipt within 24 hours
2. Assess severity within 48 hours
3. Provide status updates every 7 days
4. Coordinate disclosure after patch is released

---

## 🛡️ Security Features

### Data Protection

- ✅ **Encryption in Transit** — TLS 1.3 for all communications
- ✅ **Encryption at Rest** — AES-256 for sensitive data
- ✅ **PII Masking** — Automatic redaction for non-executive roles
- ✅ **API Keys** — Never logged or stored in plain text
- ✅ **Password Requirements** — bcrypt hashing with salt

### Access Control

- ✅ **Role-Based Access Control (RBAC)** — Fine-grained permissions by user role
- ✅ **Multi-Factor Authentication** — Optional 2FA via TOTP
- ✅ **Session Management** — Automatic timeout after 30 minutes of inactivity
- ✅ **API Rate Limiting** — Token bucket algorithm prevents brute force

### Audit & Compliance

- ✅ **Comprehensive Audit Trails** — All actions logged with user, timestamp, change details
- ✅ **18-Month Retention** — Historical audit data preserved for compliance
- ✅ **Change Log** — Before/after values for all updates
- ✅ **Approval Tracking** — Who approved what, when, with signatures

### Integrity

- ✅ **Report Signing** — Professional PDFs digitally signed
- ✅ **Tamper Detection** — Cryptographic validation of stored artifacts
- ✅ **Data Validation** — Input sanitization on all endpoints
- ✅ **SQL Injection Protection** — Parameterized queries, ORM usage

---

## 🚀 Deployment Security

### Environment Configuration

Never commit secrets:

```bash
# ✅ Good
export API_KEY=$(keytool get api_key)
export DATABASE_URL=$(keytool get db_url)

# ❌ Bad
export DATABASE_URL=postgresql://user:password123@localhost/db
```

Use `.env.example` for template:

```env
# Example — DO NOT use these values
OPENAI_API_KEY=sk-placeholder
DATABASE_URL=postgresql://user:password@localhost/dbname
GOOGLE_CLIENT_SECRET=gcs-placeholder
JWT_SECRET=your-secret-key-here
```

### Docker Security

If using Docker:

```dockerfile
# ✅ Run as non-root user
FROM python:3.10-slim
RUN useradd -m -u 1000 appuser
USER appuser

# ❌ Avoid
RUN pip install --upgrade pip  # Could pull malicious updates
```

### API Key Management

- Store keys in a secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager)
- Rotate keys every 90 days
- Use separate keys for staging vs. production
- Never commit `.env` files

---

## 🔒 Third-Party Dependencies

### Allowed

- **LangGraph** — LangChain official project
- **sentence-transformers** — Hugging Face maintained
- **FastAPI** — Well-maintained by Sebastián Ramírez & community
- **React** — Meta maintained
- **PostgreSQL** — Community standard
- **OpenAI SDK** — Official SDK maintained by OpenAI
- **FAISS** — Meta AI Research

### Prohibited

- Unmaintained or abandoned packages
- Packages with unresolved critical CVEs
- Packages from untrusted sources
- Packages with unclear license terms

### Dependency Scanning

```bash
# Check for vulnerabilities
pip install safety
safety check

# Check licenses
pip install pip-audit
pip-audit --desc
```

---

## 🧪 Security Testing

All submissions must pass:

### Linting & Static Analysis

```bash
# Python
flake8 backend/
mypy backend/  # Type checking
bandit backend/ -r  # Security issues

# JavaScript/TypeScript
npx eslint frontend/
npx typescript --noEmit
```

### Dependency Auditing

```bash
# Python
safety check

# JavaScript
npm audit
```

### Integration Tests

```bash
# Test with real API keys (staging only)
pytest tests/integration/ -v

# Test RBAC enforcement
# Test SQL injection resistance
# Test rate limiting
```

---

## 📋 Compliance Standards

### Certifications

We aim for:
- **SOC 2 Type II** — Financial/audit controls
- **ISO/IEC 27001** — Information security management
- **GDPR Compliance** — EU data protection

### Requirements

- ✅ Encryption of data in transit and at rest
- ✅ Regular security audits
- ✅ Incident response procedures
- ✅ Data retention & deletion policies
- ✅ Access control enforcement
- ✅ Audit logging

---

## 🔑 API Security

### Authentication

All endpoints require a valid API key or JWT token:

```bash
# Request
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  http://localhost:8000/api/chat

# Response
{
  "messages": [...],
  "insights": [...]
}
```

### Rate Limiting

- **Unauthenticated** — 10 requests per minute per IP
- **Authenticated** — 1000 requests per hour per user
- **Chat endpoint** — 50 requests per minute (higher due to processing)

Exceeding limits returns HTTP 429:

```json
{
  "error": "Rate limit exceeded",
  "retry_after": 60
}
```

### Input Validation

All inputs validated:

```python
# Bad request example
{
  "query": "<script>alert('xss')</script>"
}

# Returns 400 Bad Request
{
  "error": "Invalid input",
  "details": "Query contains forbidden characters"
}
```

### CORS Policy

Frontend allowed origins:
- `http://localhost:3000` (development)
- `https://copilot.costintelligence.ai` (production)

---

## 🚨 Vulnerability Disclosure Timeline

**Severity: Critical** (CVSS 9.0+)
- Patch: 24-48 hours
- Disclosure: On patch release

**Severity: High** (CVSS 7.0-8.9)
- Patch: 5-7 days
- Disclosure: On patch release

**Severity: Medium** (CVSS 4.0-6.9)
- Patch: 14-21 days
- Disclosure: On patch release

**Severity: Low** (CVSS <4.0)
- Patch: Next regular release
- Disclosure: On patch release

---

## ✅ Security Checklist

Before deploying to production:

- [ ] All secrets in environment variables (not code)
- [ ] HTTPS/TLS enabled with valid certificate
- [ ] Database encrypted at rest
- [ ] API keys rotated in last 90 days
- [ ] Security headers configured (CSP, HSTS, X-Frame-Options)
- [ ] CORS origins restricted to known domains
- [ ] Rate limiting enabled
- [ ] Audit logging 100% coverage
- [ ] Data retention policy defined
- [ ] Incident response plan documented
- [ ] Regular security audits scheduled
- [ ] Dependencies vulnerability-scanned

---

## 📞 Security Contacts

- **Report Vulnerability:** security@costintelligence.ai
- **Ask Security Question:** security@costintelligence.ai
- **PGP Key:** [Link to public key](https://costintelligence.ai/security/pgp.pub)

---

## 📚 References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [SANS Top 25](https://www.sans.org/top25-software-errors/)
- [CWE/SANS](https://cwe.mitre.org/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

## License

This security policy is licensed under MIT License — publicly available for review.

---

**Last Updated:** March 29, 2026
