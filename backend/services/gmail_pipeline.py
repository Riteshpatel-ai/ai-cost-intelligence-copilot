from typing import Any, Dict, List, Optional, Tuple

from backend.langgraph_execution import run_langgraph_workflow
from backend.services.gmail_client import GmailClient
from backend.services.gmail_state_store import GmailStateStore
from backend.services.intake_store import append_event
from backend.services.vector_store import VectorDocumentStore


class GmailPipeline:
    """End-to-end processor from Gmail event to RAG storage and agent trigger."""

    PROJECT_RELEVANCE_KEYWORDS = {
        # Core Finance Keywords (specific, not marketing terms)
        'invoice',
        'billing',
        'bill',
        'payment',
        'vendor',
        'procurement',
        'purchase order',
        'po number',
        
        # Cost Keywords
        'cost',
        'spend',
        'expenditure',
        'budget',
        'allocated',
        'unused',
        'idle',
        'surplus',
        
        # SLA Keywords
        'sla',
        'penalty',
        'breach',
        'uptime',
        'downtime',
        'performance',
        'availability',
        
        # Reconciliation Keywords
        'reconcile',
        'reconciliation',
        'variance',
        'discrepancy',
        'mismatch',
        'duplicate',
        'anomaly',
        
        # Optimization Keywords
        'leakage',
        'savings',
        'optimization',
        'consolidate',
        'consolidation',
        'underutilized',
        'rightsizing',
    }

    PROJECT_RELEVANT_ATTACHMENT_SUFFIXES = ('.csv', '.xlsx', '.xls', '.pdf')

    def __init__(
        self,
        gmail_client: Optional[GmailClient] = None,
        state_store: Optional[GmailStateStore] = None,
        vector_store: Optional[VectorDocumentStore] = None,
    ):
        self.gmail_client = gmail_client or GmailClient()
        self.state_store = state_store or GmailStateStore()
        self.vector_store = vector_store or VectorDocumentStore()

    def classify_email(self, email: Dict[str, Any]) -> str:
        subject = str(email.get('subject', '')).lower()
        body = str(email.get('body', '')).lower()
        text = f"{subject} {body}"

        if 'invoice' in text or 'payment' in text or 'vendor' in text:
            return 'finance'
        if 'sla' in text or 'breach' in text or 'penalty' in text:
            return 'sla'
        if 'utilization' in text or 'resource' in text or 'idle' in text:
            return 'resource'
        return 'general'

    def process_email(self, email: Dict[str, Any]) -> Dict[str, Any]:
        classification = self.classify_email(email)
        subject = str(email.get('subject', '')).strip()
        sender = str(email.get('sender', '')).strip()
        body = str(email.get('body', '')).strip()
        snippet = str(email.get('snippet', '')).strip()
        attachments = email.get('attachments', []) or []
        attachment_names = [str(item.get('filename', '')).strip() for item in attachments if isinstance(item, dict)]
        attachment_text = str(email.get('attachment_text', '')).strip()

        is_project_relevant, relevance_signals = self._is_project_relevant(
            classification=classification,
            subject=subject,
            sender=sender,
            body=body,
            snippet=snippet,
            attachment_names=attachment_names,
            attachment_text=attachment_text,
        )

        text_parts = [
            f"Subject: {subject}",
            f"From: {sender}",
            f"Body: {body}",
        ]
        if attachment_names:
            text_parts.append(f"Attachments: {', '.join(attachment_names)}")
        if attachment_text:
            text_parts.append(f"Attachment Content: {attachment_text}")

        return {
            'text': '\n'.join(part for part in text_parts if part.strip()).strip(),
            'metadata': {
                'sender': sender,
                'subject': subject,
                'message_id': email.get('message_id', ''),
                'history_id': email.get('history_id', ''),
                'type': classification,
                'source': 'gmail_live_api',
                'attachment_count': len(attachment_names),
                'attachment_names': attachment_names,
                'is_project_relevant': is_project_relevant,
                'relevance_signals': relevance_signals,
            },
        }

    def _is_project_relevant(
        self,
        classification: str,
        subject: str,
        sender: str,
        body: str,
        snippet: str,
        attachment_names: List[str],
        attachment_text: str,
    ) -> Tuple[bool, List[str]]:
        if classification in {'finance', 'sla', 'resource'}:
            return True, [f'classified:{classification}']

        corpus = ' '.join(
            [subject, sender, body, snippet, attachment_text, ' '.join(attachment_names)]
        ).lower()
        matched_keywords = sorted(
            keyword for keyword in self.PROJECT_RELEVANCE_KEYWORDS if keyword in corpus
        )

        relevant_attachment = any(
            name.lower().endswith(self.PROJECT_RELEVANT_ATTACHMENT_SUFFIXES)
            for name in attachment_names
        )

        signals = [f'keyword:{keyword}' for keyword in matched_keywords[:10]]
        if relevant_attachment:
            signals.append('attachment:structured_finance_doc')

        return (bool(matched_keywords) or relevant_attachment), signals

    def process_manual_email(
        self,
        sender: str,
        subject: str,
        body: str,
        message_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        manual_message_id = (message_id or '').strip() or f"manual_{abs(hash((sender, subject, body))) % 10**10}"
        if self.state_store.is_duplicate(message_id=manual_message_id, history_id=None):
            return {
                'status': 'duplicate',
                'message_id': manual_message_id,
                'history_id': None,
            }

        email = {
            'message_id': manual_message_id,
            'history_id': '',
            'sender': sender,
            'subject': subject,
            'body': body,
        }

        return self._process_email_record(email=email, history_id=None)

    def process_message(self, message_id: str, history_id: Optional[str] = None) -> Dict[str, Any]:
        if self.state_store.is_duplicate(message_id=message_id, history_id=history_id):
            return {
                'status': 'duplicate',
                'message_id': message_id,
                'history_id': history_id,
            }

        email = self.gmail_client.get_email(message_id)
        return self._process_email_record(email=email, history_id=history_id)

    def _process_email_record(self, email: Dict[str, Any], history_id: Optional[str]) -> Dict[str, Any]:
        doc = self.process_email(email)
        effective_message_id = str(email.get('message_id', '') or '').strip()
        effective_history_id = str(email.get('history_id') or history_id or '')

        if not doc['metadata'].get('is_project_relevant', True):
            self.state_store.mark_processed(message_id=effective_message_id, history_id=effective_history_id)
            event = append_event(
                'gmail_email_ignored',
                {
                    'message_id': effective_message_id,
                    'history_id': effective_history_id,
                    'classification': doc['metadata'].get('type', 'general'),
                    'reason': 'non_project_relevant',
                    'relevance_signals': doc['metadata'].get('relevance_signals', []),
                },
            )
            return {
                'status': 'ignored',
                'reason': 'non_project_relevant',
                'message_id': effective_message_id,
                'history_id': effective_history_id,
                'classification': doc['metadata'].get('type', 'general'),
                'relevance_signals': doc['metadata'].get('relevance_signals', []),
                'event': event,
            }

        vector_record = self.vector_store.add_document(doc['text'], doc['metadata'])
        docs_context = self.vector_store.recent_document_texts(limit=50)

        workflow_result = run_langgraph_workflow(
            {
                'query': doc['text'],
                'docs': docs_context,
                'invoices': [],
                'sla_logs': [],
                'resources': [],
                'transactions': [],
            }
        )

        self.state_store.mark_processed(message_id=effective_message_id, history_id=effective_history_id)

        event = append_event(
            'gmail_email_processed',
            {
                'message_id': effective_message_id,
                'history_id': effective_history_id,
                'classification': doc['metadata'].get('type', 'general'),
                'vector_doc_id': vector_record.get('id', ''),
                'financial_impact': workflow_result.get('financial_impact', 0.0),
                'risk_level': workflow_result.get('risk_level', 'low'),
            },
        )

        return {
            'status': 'processed',
            'message_id': effective_message_id,
            'history_id': effective_history_id,
            'classification': doc['metadata'].get('type', 'general'),
            'attachment_count': doc['metadata'].get('attachment_count', 0),
            'attachment_names': doc['metadata'].get('attachment_names', []),
            'relevance_signals': doc['metadata'].get('relevance_signals', []),
            'vector_doc_id': vector_record.get('id', ''),
            'workflow': {
                'financial_impact': workflow_result.get('financial_impact', 0.0),
                'risk_level': workflow_result.get('risk_level', 'low'),
                'approval_required': workflow_result.get('approval_required', 'auto'),
                'recommendations': workflow_result.get('recommendations', []),
            },
            'event': event,
        }

    def process_history(self, history_id: str) -> Dict[str, Any]:
        message_ids = self.gmail_client.list_new_message_ids(history_id)
        if not message_ids:
            return {
                'status': 'no_messages',
                'history_id': history_id,
                'processed_count': 0,
                'results': [],
            }

        results: List[Dict[str, Any]] = []
        for message_id in message_ids:
            results.append(self.process_message(message_id=message_id, history_id=history_id))

        return {
            'status': 'processed',
            'history_id': history_id,
            'processed_count': len(results),
            'results': results,
        }

    def process_latest_messages(self, limit: int = 1) -> Dict[str, Any]:
        effective_limit = max(1, int(limit))
        scan_window = min(max(effective_limit * 10, 25), 100)
        message_ids = self.gmail_client.list_recent_message_ids(
            max_results=scan_window,
            prefer_unread=True,
        )
        if not message_ids:
            return {
                'status': 'no_messages',
                'source': 'gmail_live_api',
                'scan_window': scan_window,
                'fetched_count': 0,
                'checked_message_ids': 0,
                'processed_count': 0,
                'duplicates_skipped': 0,
                'results': [],
            }

        results: List[Dict[str, Any]] = []
        processed_count = 0
        duplicates_skipped = 0
        ignored_count = 0
        for message_id in message_ids:
            result = self.process_message(message_id=message_id, history_id=None)
            results.append(result)
            if result.get('status') == 'processed':
                processed_count += 1
                if processed_count >= effective_limit:
                    break
            elif result.get('status') == 'duplicate':
                duplicates_skipped += 1
            elif result.get('status') == 'ignored':
                ignored_count += 1

        if processed_count > 0:
            status = 'processed'
            message = 'Processed latest project-relevant unprocessed Gmail message(s).'
        elif ignored_count > 0:
            status = 'no_project_relevant_messages'
            message = 'Fetched unread emails were ignored because they are not relevant to cost/SLA/resource/finance workflows.'
        else:
            status = 'no_new_messages'
            message = 'No unprocessed unread Gmail messages found in the current scan window.'

        return {
            'status': status,
            'source': 'gmail_live_api',
            'scan_window': scan_window,
            'message': message,
            'fetched_count': len(results),
            'checked_message_ids': len(message_ids),
            'processed_count': processed_count,
            'duplicates_skipped': duplicates_skipped,
            'ignored_count': ignored_count,
            'results': results,
        }
