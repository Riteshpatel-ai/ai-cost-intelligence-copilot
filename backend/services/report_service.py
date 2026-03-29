from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Tuple


REPORTS_DIR = Path(__file__).resolve().parents[2] / 'data' / 'reports'
LATEST_REPORT_FILE = REPORTS_DIR / 'latest_report.json'


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return []


def _title_case(text: str) -> str:
    return str(text or '').replace('_', ' ').strip().title()


def _format_inr(value: float) -> str:
    return f"INR {float(value or 0.0):,.2f}"


def _severity_for_count(count: int) -> str:
    if count >= 10:
        return 'High'
    if count >= 3:
        return 'Medium'
    if count >= 1:
        return 'Low'
    return 'Informational'


def _build_key_findings(anomaly_counts: Dict[str, int]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    ordered = sorted(anomaly_counts.items(), key=lambda item: item[1], reverse=True)
    for domain, count in ordered:
        if count <= 0:
            continue
        findings.append(
            {
                'domain': _title_case(domain),
                'observation_count': count,
                'severity': _severity_for_count(count),
                'auditor_note': (
                    f"Detected {count} material observation(s) in {domain.replace('_', ' ')} requiring validation and control response."
                ),
            }
        )

    if findings:
        return findings

    return [
        {
            'domain': 'Overall Monitoring',
            'observation_count': 0,
            'severity': 'Informational',
            'auditor_note': 'No material anomalies were detected in the current evaluation window.',
        }
    ]


def build_audit_report_payload(query: str, chat_payload: Dict[str, Any]) -> Dict[str, Any]:
    anomalies = chat_payload.get('anomalies', {}) if isinstance(chat_payload.get('anomalies'), dict) else {}
    recommendations = _safe_list(chat_payload.get('recommendations'))
    actions = _safe_list(chat_payload.get('actions'))
    explainability = chat_payload.get('explainability', {}) if isinstance(chat_payload.get('explainability'), dict) else {}
    confidence_traces = _safe_list(explainability.get('confidence_traces'))
    action_timeline = _safe_list(explainability.get('action_audit_timeline'))

    anomaly_counts = {
        'duplicates': len(_safe_list(anomalies.get('duplicates'))),
        'cost_leakage': len(_safe_list(anomalies.get('cost_leakage'))),
        'sla_breaches': len(_safe_list(anomalies.get('sla_breaches'))),
        'underutilized': len(_safe_list(anomalies.get('underutilized'))),
        'overutilized': len(_safe_list(anomalies.get('overutilized'))),
        'unmatched': len(_safe_list(anomalies.get('unmatched'))),
        'variance': len(_safe_list(anomalies.get('variance'))),
    }
    financial_impact = float(chat_payload.get('financial_impact', 0.0) or 0.0)
    risk_level = str(chat_payload.get('risk_level', 'low'))
    approval_required = str(chat_payload.get('approval_required', 'auto'))
    key_findings = _build_key_findings(anomaly_counts)

    decision_log: List[Dict[str, Any]] = []
    for index, item in enumerate(recommendations, start=1):
        decision_log.append(
            {
                'id': f'rec_{index}',
                'recommendation': str(item),
                'justification': (
                    'Derived from anomaly signals, confidence traces, and financial impact scoring in the workflow.'
                ),
                'decision_criteria': {
                    'impact': financial_impact,
                    'risk_level': risk_level,
                    'approval_required': approval_required,
                },
            }
        )

    action_plan: List[Dict[str, Any]] = []
    for index, action in enumerate(actions, start=1):
        action_type = str(action.get('type') or action.get('label') or f'Action {index}')
        action_risk = str(action.get('risk') or action.get('riskLevel') or action.get('risk_level') or risk_level)
        action_approval = str(action.get('approval_required') or action.get('approvalRequired') or approval_required)
        action_plan.append(
            {
                'id': f'act_{index}',
                'action': action_type,
                'risk_level': action_risk,
                'approval_gate': action_approval,
                'owner': 'Finance Control Desk' if action_approval == 'finance' else 'Operations Manager',
                'target_tat': '3-5 business days',
            }
        )

    report_payload = {
        'report_id': f"rpt_{int(datetime.now(timezone.utc).timestamp())}",
        'generated_at': _utc_now_iso(),
        'title': 'Cost Optimization Decision Audit Report',
        'query': query,
        'currency': 'INR',
        'auditor_profile': {
            'persona': 'Independent Cost and Controls Auditor (15+ years equivalent methodology)',
            'framework': 'Risk-based financial controls assessment with evidence-driven recommendation mapping',
            'standard': 'Enterprise audit-style reporting for management review',
        },
        'summary': {
            'financial_impact': financial_impact,
            'risk_level': risk_level,
            'approval_required': approval_required,
            'recommendation_count': len(recommendations),
            'observation_count': int(sum(anomaly_counts.values())),
            'management_summary': (
                'This report evaluates control effectiveness across spend, SLA, resource, and finance domains; '
                'quantifies potential recoverable value; and proposes governance-backed corrective actions.'
            ),
        },
        'audit_scope': {
            'objective': 'Assess financial leakage, operational risk, and control gaps in current data window.',
            'query_context': query,
            'in_scope_domains': ['Spend', 'SLA', 'Resource', 'Finance'],
            'out_of_scope': ['Manual journal verification', 'External bank confirmation'],
        },
        'data_sources_and_methods': {
            'sources': [
                'Uploaded datasets and/or Gmail-ingested documents from vector store',
                'Agent outputs (Spend, SLA, Resource, Finance)',
                'RAG retrieved context documents',
            ],
            'methods': [
                'LangGraph orchestration across domain agents',
                'RAG semantic retrieval for contextual grounding',
                'Financial impact scoring using configured workflow rules',
            ],
            'anomaly_counts': anomaly_counts,
            'evidence_quality': 'Moderate to High, subject to source data completeness and field integrity.',
        },
        'key_findings': key_findings,
        'financial_materiality': {
            'currency': 'INR',
            'estimated_recoverable_impact': financial_impact,
            'materiality_band': (
                'High' if financial_impact >= 50000 else 'Medium' if financial_impact >= 10000 else 'Low'
            ),
            'formula': 'impact = amount x confidence x recoveryProbability',
        },
        'recommendation_justifications': decision_log,
        'risk_assessment_and_mitigation': {
            'overall_risk_level': risk_level,
            'mitigation_strategies': [
                'Require approval routing based on risk level before action execution.',
                'Preserve action audit timeline for post-implementation review.',
                'Monitor confidence traces and adjust thresholds for false positives.',
            ],
            'residual_risk_statement': (
                'Residual risk remains until recommended controls are executed, evidenced, and independently validated.'
            ),
        },
        'approval_workflow': {
            'required_role': approval_required,
            'decision_criteria': [
                'Calculated impact magnitude',
                'Risk level classification',
                'Confidence evidence and anomaly validation',
            ],
            'proposed_actions': actions,
            'action_plan': action_plan,
        },
        'compliance_documentation': {
            'financial_review_required': approval_required in {'manager', 'finance'},
            'audit_trail': action_timeline,
            'confidence_traces': confidence_traces,
            'controls': [
                'Documented recommendation rationale',
                'Approval traceability by role',
                'Reproducible analysis inputs and outputs',
            ],
            'documentation_status': 'Ready for internal management review and controller sign-off.',
        },
        'auditor_conclusion': {
            'opinion': (
                'Based on available evidence, the control environment is conditionally adequate but requires '
                'timely remediation of identified high-impact observations to reduce financial leakage risk.'
            ),
            'next_review_cycle': '30 days or post-remediation completion, whichever is earlier.',
        },
    }
    return report_payload


def save_latest_report(report_payload: Dict[str, Any]) -> Dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with LATEST_REPORT_FILE.open('w', encoding='utf-8') as f:
        json.dump(report_payload, f, ensure_ascii=True, indent=2)
    return report_payload


def load_latest_report() -> Dict[str, Any]:
    if not LATEST_REPORT_FILE.exists():
        return {}
    with LATEST_REPORT_FILE.open('r', encoding='utf-8') as f:
        return json.load(f)


def build_and_store_chat_report(query: str, chat_payload: Dict[str, Any]) -> Dict[str, Any]:
    report_payload = build_audit_report_payload(query=query, chat_payload=chat_payload)
    save_latest_report(report_payload)
    return {
        'report_id': report_payload['report_id'],
        'title': report_payload['title'],
        'generated_at': report_payload['generated_at'],
        'download_url': '/api/reports/latest-pdf',
        'currency': report_payload.get('currency', 'INR'),
    }


def render_report_pdf(report_payload: Dict[str, Any]) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise RuntimeError('reportlab is required to generate PDF reports.') from exc

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin_x = 16 * mm
    content_width = width - (2 * margin_x)
    top_y = height - 16 * mm
    bottom_y = 16 * mm
    page_no = 1

    def wrap_text(text: str, font_name: str, font_size: float, max_width: float) -> List[str]:
        words = str(text or '').split()
        if not words:
            return ['']
        lines: List[str] = []
        current = words[0]
        for word in words[1:]:
            probe = f"{current} {word}"
            if pdf.stringWidth(probe, font_name, font_size) <= max_width:
                current = probe
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def draw_header() -> None:
        pdf.setFillColor(colors.HexColor('#0F172A'))
        pdf.rect(0, height - 18 * mm, width, 18 * mm, stroke=0, fill=1)
        pdf.setFillColor(colors.white)
        pdf.setFont('Helvetica-Bold', 10)
        pdf.drawString(margin_x, height - 11.5 * mm, 'AI Cost Intelligence Copilot | Independent Audit Report')
        pdf.setFont('Helvetica', 8)
        pdf.drawRightString(width - margin_x, height - 11.5 * mm, f"Page {page_no}")

    def draw_footer() -> None:
        pdf.setStrokeColor(colors.HexColor('#CBD5E1'))
        pdf.setLineWidth(0.5)
        pdf.line(margin_x, bottom_y + 6 * mm, width - margin_x, bottom_y + 6 * mm)
        pdf.setFillColor(colors.HexColor('#475569'))
        pdf.setFont('Helvetica', 7.8)
        pdf.drawString(margin_x, bottom_y + 2.2 * mm, 'Confidential | Prepared for internal governance and audit review')

    def new_page() -> None:
        nonlocal page_no
        draw_footer()
        pdf.showPage()
        page_no += 1
        draw_header()

    def ensure_space(current_y: float, needed: float) -> float:
        if current_y - needed < bottom_y + 10 * mm:
            new_page()
            return top_y - 6 * mm
        return current_y

    def draw_section_title(text: str, y: float) -> float:
        y = ensure_space(y, 12 * mm)
        pdf.setFillColor(colors.HexColor('#0F172A'))
        pdf.setFont('Helvetica-Bold', 12)
        pdf.drawString(margin_x, y, text)
        y -= 2.5 * mm
        pdf.setStrokeColor(colors.HexColor('#94A3B8'))
        pdf.setLineWidth(0.8)
        pdf.line(margin_x, y, width - margin_x, y)
        return y - 4.5 * mm

    def draw_paragraph(text: str, y: float, font_size: float = 9.5, leading: float = 4.4 * mm) -> float:
        lines = wrap_text(text, 'Helvetica', font_size, content_width)
        y = ensure_space(y, max(leading, len(lines) * leading + 2 * mm))
        pdf.setFont('Helvetica', font_size)
        pdf.setFillColor(colors.HexColor('#0F172A'))
        for line in lines:
            y = ensure_space(y, leading + 2 * mm)
            pdf.drawString(margin_x, y, line)
            y -= leading
        return y - 1.5 * mm

    def draw_bullets(items: List[str], y: float) -> float:
        for item in items:
            bullet_lines = wrap_text(item, 'Helvetica', 9.2, content_width - 6 * mm)
            y = ensure_space(y, (len(bullet_lines) + 1) * 4.2 * mm)
            pdf.setFont('Helvetica', 9.2)
            pdf.setFillColor(colors.HexColor('#0F172A'))
            pdf.drawString(margin_x, y, '- ')
            line_y = y
            for idx, line in enumerate(bullet_lines):
                x = margin_x + 4.2 * mm if idx == 0 else margin_x + 4.2 * mm
                pdf.drawString(x, line_y, line)
                line_y -= 4.2 * mm
            y = line_y
        return y - 1.0 * mm

    def draw_summary_grid(rows: List[Tuple[str, str]], y: float) -> float:
        box_height = 17 * mm
        col_w = content_width / 2
        for idx, (label, value) in enumerate(rows):
            if idx % 2 == 0:
                y = ensure_space(y, box_height + 2 * mm)
            row_y = y
            x = margin_x + (idx % 2) * col_w
            pdf.setFillColor(colors.HexColor('#F8FAFC'))
            pdf.setStrokeColor(colors.HexColor('#CBD5E1'))
            pdf.rect(x, row_y - box_height, col_w - 2 * mm, box_height, stroke=1, fill=1)
            pdf.setFillColor(colors.HexColor('#334155'))
            pdf.setFont('Helvetica-Bold', 8.3)
            pdf.drawString(x + 2.2 * mm, row_y - 5.0 * mm, label)
            pdf.setFillColor(colors.HexColor('#0F172A'))
            pdf.setFont('Helvetica-Bold', 10)
            value_lines = wrap_text(value, 'Helvetica-Bold', 10, col_w - 7 * mm)
            draw_y = row_y - 10.5 * mm
            for vline in value_lines[:2]:
                pdf.drawString(x + 2.2 * mm, draw_y, vline)
                draw_y -= 3.8 * mm
            if idx % 2 == 1:
                y -= box_height + 2.4 * mm
        if len(rows) % 2 == 1:
            y -= box_height + 2.4 * mm
        return y

    def draw_table(headers: List[str], rows: List[List[str]], col_widths: List[float], y: float) -> float:
        row_min_h = 8 * mm

        def _draw_row(row_cells: List[str], row_y: float, is_header: bool = False) -> float:
            wrapped_cells: List[List[str]] = []
            max_lines = 1
            for idx, cell in enumerate(row_cells):
                lines = wrap_text(str(cell), 'Helvetica-Bold' if is_header else 'Helvetica', 8.5, col_widths[idx] - 2.8 * mm)
                wrapped_cells.append(lines)
                max_lines = max(max_lines, len(lines))
            row_h = max(row_min_h, max_lines * 3.8 * mm + 3 * mm)

            local_y = ensure_space(row_y, row_h + 2 * mm)
            x = margin_x
            for idx, lines in enumerate(wrapped_cells):
                pdf.setFillColor(colors.HexColor('#E2E8F0') if is_header else colors.white)
                pdf.setStrokeColor(colors.HexColor('#94A3B8'))
                pdf.rect(x, local_y - row_h, col_widths[idx], row_h, stroke=1, fill=1)
                pdf.setFillColor(colors.HexColor('#0F172A'))
                pdf.setFont('Helvetica-Bold' if is_header else 'Helvetica', 8.5)
                text_y = local_y - 4.3 * mm
                for line in lines:
                    pdf.drawString(x + 1.4 * mm, text_y, line)
                    text_y -= 3.8 * mm
                x += col_widths[idx]
            return local_y - row_h

        y = _draw_row(headers, y, is_header=True)
        for row in rows:
            y = _draw_row(row, y, is_header=False)
        return y - 2.5 * mm

    pdf.setTitle(str(report_payload.get('title', 'Cost Optimization Report')))
    draw_header()
    y = top_y - 8 * mm

    summary = report_payload.get('summary', {}) if isinstance(report_payload.get('summary'), dict) else {}
    scope = report_payload.get('audit_scope', {}) if isinstance(report_payload.get('audit_scope'), dict) else {}
    data_methods = report_payload.get('data_sources_and_methods', {}) if isinstance(report_payload.get('data_sources_and_methods'), dict) else {}
    risk = report_payload.get('risk_assessment_and_mitigation', {}) if isinstance(report_payload.get('risk_assessment_and_mitigation'), dict) else {}
    workflow = report_payload.get('approval_workflow', {}) if isinstance(report_payload.get('approval_workflow'), dict) else {}
    compliance = report_payload.get('compliance_documentation', {}) if isinstance(report_payload.get('compliance_documentation'), dict) else {}
    conclusion = report_payload.get('auditor_conclusion', {}) if isinstance(report_payload.get('auditor_conclusion'), dict) else {}
    financial = report_payload.get('financial_materiality', {}) if isinstance(report_payload.get('financial_materiality'), dict) else {}
    findings = _safe_list(report_payload.get('key_findings'))

    pdf.setFillColor(colors.HexColor('#0F172A'))
    pdf.setFont('Helvetica-Bold', 16)
    pdf.drawString(margin_x, y, str(report_payload.get('title', 'Cost Optimization Decision Audit Report')))
    y -= 6.2 * mm
    pdf.setFillColor(colors.HexColor('#334155'))
    pdf.setFont('Helvetica', 9.5)
    pdf.drawString(margin_x, y, f"Report ID: {report_payload.get('report_id', 'N/A')}")
    pdf.drawRightString(width - margin_x, y, f"Generated: {report_payload.get('generated_at', 'N/A')}")
    y -= 4.8 * mm
    y = draw_paragraph(
        str(summary.get('management_summary', 'Professional review of financial impact, risk posture, and governance controls.')),
        y,
    )

    y = draw_section_title('1. Executive Summary', y)
    summary_rows = [
        ('Estimated Financial Impact', _format_inr(float(summary.get('financial_impact', 0.0) or 0.0))),
        ('Overall Risk Rating', _title_case(str(summary.get('risk_level', 'low')))),
        ('Approval Authority', _title_case(str(summary.get('approval_required', 'auto')))),
        ('Total Recommendations', str(summary.get('recommendation_count', 0))),
    ]
    y = draw_summary_grid(summary_rows, y)

    y = draw_section_title('2. Scope and Objectives', y)
    y = draw_paragraph(
        f"Objective: {scope.get('objective', 'Assess enterprise cost-risk posture and identify corrective actions.')}",
        y,
    )
    y = draw_paragraph(f"Audit Trigger Query: {scope.get('query_context', report_payload.get('query', 'N/A'))}", y)
    in_scope = [str(item) for item in _safe_list(scope.get('in_scope_domains'))]
    if in_scope:
        y = draw_bullets([f"In scope domain: {item}" for item in in_scope], y)

    y = draw_section_title('3. Data Sources and Methodology', y)
    sources = [str(item) for item in _safe_list(data_methods.get('sources'))]
    methods = [str(item) for item in _safe_list(data_methods.get('methods'))]
    y = draw_paragraph(
        f"Evidence Quality Assessment: {data_methods.get('evidence_quality', 'Moderate to high quality evidence based on available datasets.')}",
        y,
    )
    if sources:
        y = draw_bullets([f"Data source: {item}" for item in sources], y)
    if methods:
        y = draw_bullets([f"Method: {item}" for item in methods], y)

    y = draw_section_title('4. Key Findings and Severity', y)
    finding_rows: List[List[str]] = []
    for finding in findings:
        finding_rows.append(
            [
                str(finding.get('domain', 'N/A')),
                str(finding.get('observation_count', 0)),
                str(finding.get('severity', 'Informational')),
                str(finding.get('auditor_note', '')),
            ]
        )
    y = draw_table(
        headers=['Domain', 'Count', 'Severity', 'Auditor Observation'],
        rows=finding_rows,
        col_widths=[30 * mm, 18 * mm, 24 * mm, content_width - (72 * mm)],
        y=y,
    )

    y = draw_section_title('5. Financial Materiality and Risk Position', y)
    y = draw_paragraph(
        f"Estimated Recoverable Value: {_format_inr(float(financial.get('estimated_recoverable_impact', 0.0) or 0.0))}",
        y,
    )
    y = draw_paragraph(
        f"Materiality Band: {financial.get('materiality_band', 'Low')} | Formula Applied: {financial.get('formula', 'impact = amount x confidence x recoveryProbability')}",
        y,
    )
    y = draw_paragraph(
        f"Residual Risk Statement: {risk.get('residual_risk_statement', 'Residual risk remains until control actions are fully implemented and validated.')}",
        y,
    )

    y = draw_section_title('6. Recommended Actions and Approval Gates', y)
    action_plan = _safe_list(workflow.get('action_plan'))
    if action_plan:
        action_rows: List[List[str]] = []
        for action in action_plan:
            action_rows.append(
                [
                    str(action.get('action', 'N/A')),
                    _title_case(str(action.get('risk_level', 'low'))),
                    _title_case(str(action.get('approval_gate', 'auto'))),
                    str(action.get('owner', 'Operations Manager')),
                    str(action.get('target_tat', '3-5 business days')),
                ]
            )
        y = draw_table(
            headers=['Action', 'Risk', 'Approval', 'Owner', 'Target TAT'],
            rows=action_rows,
            col_widths=[52 * mm, 18 * mm, 22 * mm, 40 * mm, content_width - (132 * mm)],
            y=y,
        )
    else:
        y = draw_paragraph('No execution actions were generated in this cycle. Continue monitoring and re-run analysis after new evidence.', y)

    y = draw_section_title('7. Compliance, Controls, and Traceability', y)
    controls = [str(item) for item in _safe_list(compliance.get('controls'))]
    if controls:
        y = draw_bullets([f"Control: {item}" for item in controls], y)
    y = draw_paragraph(
        f"Audit Trail Entries: {len(_safe_list(compliance.get('audit_trail')))} | Confidence Traces: {len(_safe_list(compliance.get('confidence_traces')))}",
        y,
    )
    y = draw_paragraph(str(compliance.get('documentation_status', 'Documentation prepared for reviewer sign-off.')), y)

    y = draw_section_title('8. Auditor Conclusion', y)
    y = draw_paragraph(
        str(
            conclusion.get(
                'opinion',
                'The evaluated controls are conditionally adequate; high-impact findings require expedited remediation and governance review.',
            )
        ),
        y,
    )
    y = draw_paragraph(
        f"Next Review Cycle: {conclusion.get('next_review_cycle', '30 days')}",
        y,
    )

    draw_footer()
    pdf.save()
    return buffer.getvalue()
