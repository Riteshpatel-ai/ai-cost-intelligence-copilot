import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.services.gmail_pipeline import GmailPipeline
from backend.services.intake_store import append_event

router = APIRouter(tags=['gmail'])
_PIPELINE = GmailPipeline()


class StartWatchRequest(BaseModel):
    topic_name: Optional[str] = Field(default=None)
    label_ids: List[str] = Field(default_factory=lambda: ['INBOX'])


class ManualMessageRequest(BaseModel):
    message_id: str = Field(..., min_length=3)
    history_id: Optional[str] = Field(default=None)


class ManualEmailRequest(BaseModel):
    sender: str = Field(..., min_length=3)
    subject: str = Field(..., min_length=1)
    body: str = Field(default='')
    message_id: Optional[str] = Field(default=None)


class ManualFetchLatestRequest(BaseModel):
    limit: int = Field(default=1, ge=1, le=20)


@router.get('/api/gmail/health')
@router.get('/gmail/health')
def gmail_health() -> Dict[str, Any]:
    credentials_file = os.getenv('GMAIL_CREDENTIALS_FILE', '').strip()
    client_id = os.getenv('GMAIL_CLIENT_ID', '').strip()
    client_secret = os.getenv('GMAIL_CLIENT_SECRET', '').strip()
    token_file = os.getenv(
        'GMAIL_TOKEN_FILE',
        str(Path(__file__).resolve().parents[2] / 'data' / 'gmail_token.json'),
    )
    webhook_secret = os.getenv('GMAIL_WEBHOOK_SHARED_SECRET', '').strip()

    status = _PIPELINE.state_store.status_snapshot()
    status.update(
        {
            'webhook_secret_configured': bool(webhook_secret),
            'credentials_file_configured': bool(credentials_file),
            'credentials_file_exists': bool(credentials_file and Path(credentials_file).exists()),
            'client_id_configured': bool(client_id),
            'client_secret_configured': bool(client_secret),
            'oauth_env_configured': bool(client_id and client_secret),
            'token_file_path': token_file,
            'token_file_exists': Path(token_file).exists(),
            'auto_webhook_ready': bool(webhook_secret)
            and (bool(credentials_file and Path(credentials_file).exists()) or bool(client_id and client_secret)),
        }
    )

    return {
        'status': 'ok',
        'gmail': status,
    }


def _decode_pubsub_json(data: str) -> Dict[str, Any]:
    padded = data + '=' * ((4 - len(data) % 4) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode('utf-8')).decode('utf-8', errors='replace')
        payload = json.loads(decoded)
        if isinstance(payload, dict):
            return payload
        return {}
    except (ValueError, json.JSONDecodeError):
        return {}


def _extract_webhook_event(payload: Dict[str, Any]) -> Dict[str, str]:
    history_id = str(payload.get('historyId', '') or '').strip()
    message_id = str(payload.get('messageId', '') or '').strip()

    message_wrapper = payload.get('message', {})
    if isinstance(message_wrapper, dict):
        message_id = message_id or str(message_wrapper.get('messageId', '')).strip()
        data = message_wrapper.get('data')
        if isinstance(data, str) and data.strip():
            decoded = _decode_pubsub_json(data)
            history_id = history_id or str(decoded.get('historyId', '')).strip()
            message_id = message_id or str(decoded.get('messageId', '')).strip()

    return {
        'history_id': history_id,
        'message_id': message_id,
    }


def _enforce_webhook_secret(request: Request) -> None:
    configured_secret = os.getenv('GMAIL_WEBHOOK_SHARED_SECRET', '').strip()
    if not configured_secret:
        return

    incoming = request.headers.get('x-webhook-token', '').strip()
    if incoming != configured_secret:
        raise HTTPException(status_code=401, detail='Invalid webhook token.')


@router.post('/api/gmail/watch/start')
@router.post('/gmail/watch/start')
def start_watch(payload: StartWatchRequest) -> Dict[str, Any]:
    topic_name = (payload.topic_name or os.getenv('GMAIL_PUBSUB_TOPIC', '')).strip()
    if not topic_name:
        raise HTTPException(
            status_code=400,
            detail='Provide topic_name in request or set GMAIL_PUBSUB_TOPIC in .env',
        )

    try:
        watch_response = _PIPELINE.gmail_client.start_watch(
            topic_name=topic_name,
            label_ids=payload.label_ids,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    event = append_event(
        'gmail_watch_started',
        {
            'topic_name': topic_name,
            'label_ids': payload.label_ids,
            'response': watch_response,
        },
    )

    return {
        'status': 'started',
        'watch': watch_response,
        'event': event,
    }


@router.post('/api/gmail/manual/process-message')
@router.post('/gmail/manual/process-message')
def process_manual_message(payload: ManualMessageRequest) -> Dict[str, Any]:
    result = _PIPELINE.process_message(message_id=payload.message_id, history_id=payload.history_id)
    append_event(
        'gmail_manual_message_processed',
        {
            'message_id': payload.message_id,
            'history_id': payload.history_id,
            'status': result.get('status', 'unknown'),
        },
    )
    return {
        'status': 'accepted',
        'mode': 'manual_message_fetch',
        'result': result,
    }


@router.post('/api/gmail/manual/process-email')
@router.post('/gmail/manual/process-email')
def process_manual_email(payload: ManualEmailRequest) -> Dict[str, Any]:
    result = _PIPELINE.process_manual_email(
        sender=payload.sender,
        subject=payload.subject,
        body=payload.body,
        message_id=payload.message_id,
    )
    append_event(
        'gmail_manual_email_processed',
        {
            'sender': payload.sender,
            'subject': payload.subject,
            'message_id': payload.message_id,
            'status': result.get('status', 'unknown'),
        },
    )
    return {
        'status': 'accepted',
        'mode': 'manual_raw_email',
        'result': result,
    }


@router.post('/api/gmail/manual/fetch-latest')
@router.post('/gmail/manual/fetch-latest')
def process_latest_messages(payload: ManualFetchLatestRequest) -> Dict[str, Any]:
    result = _PIPELINE.process_latest_messages(limit=payload.limit)
    append_event(
        'gmail_manual_latest_fetch_processed',
        {
            'limit': payload.limit,
            'status': result.get('status', 'unknown'),
            'fetched_count': result.get('fetched_count', 0),
            'processed_count': result.get('processed_count', 0),
            'ignored_count': result.get('ignored_count', 0),
        },
    )
    return {
        'status': 'accepted',
        'mode': 'manual_latest_fetch',
        'result': result,
    }


@router.post('/api/gmail/webhook')
@router.post('/gmail/webhook')
async def gmail_webhook(request: Request) -> Dict[str, Any]:
    _enforce_webhook_secret(request)

    try:
        body = await request.json()
    except Exception:
        body = {}

    if not isinstance(body, dict):
        body = {}

    event = _extract_webhook_event(body)
    history_id = event.get('history_id', '')
    message_id = event.get('message_id', '')

    append_event(
        'gmail_webhook_received',
        {
            'history_id': history_id,
            'message_id': message_id,
            'has_pubsub_message': isinstance(body.get('message', None), dict),
        },
    )

    if message_id:
        result = _PIPELINE.process_message(message_id=message_id, history_id=history_id or None)
    elif history_id:
        result = _PIPELINE.process_history(history_id=history_id)
    else:
        result = {
            'status': 'ignored',
            'reason': 'No historyId or messageId found in webhook payload.',
        }

    return {
        'status': 'accepted',
        'event': {
            'history_id': history_id,
            'message_id': message_id,
        },
        'result': result,
    }
