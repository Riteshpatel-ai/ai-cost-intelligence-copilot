from typing import Any, Dict, List

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.services.intake_store import append_event, recent_events, save_latest_upload
from backend.tools.file_read_tool import FileReadTool

router = APIRouter(prefix='/api/ingest', tags=['ingest'])

_SUPPORTED_UPLOAD_TYPES = {
    '.csv': 'text/csv',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}
_FILE_READ_TOOL = FileReadTool()


class EmailTriggerRequest(BaseModel):
    sender: str = Field(..., min_length=3)
    subject: str = Field(..., min_length=3)
    body: str = Field(default='')
    source: str = Field(default='manual-email-trigger')


@router.post('/email-event')
def trigger_email_event(payload: EmailTriggerRequest) -> Dict[str, Any]:
    event = append_event(
        'email_event',
        {
            'sender': payload.sender,
            'subject': payload.subject,
            'body': payload.body,
            'source': payload.source,
        },
    )

    return {
        'status': 'accepted',
        'message': 'Email event trigger recorded and queued for processing.',
        'event': event,
    }

@router.post('/upload')
async def upload_dataset(file: UploadFile = File(...)) -> Dict[str, Any]:
    filename = file.filename or 'uploaded_file'
    extension = '.' + filename.split('.')[-1].lower() if '.' in filename else ''

    if extension not in _SUPPORTED_UPLOAD_TYPES:
        raise HTTPException(status_code=400, detail='Only CSV and XLSX files are supported.')

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail='Uploaded file is empty.')

    try:
        rows = _FILE_READ_TOOL.parse_uploaded_content(filename, content)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    event = append_event(
        'manual_upload',
        {
            'filename': filename,
            'row_count': len(rows),
            'columns': list(rows[0].keys()) if rows else [],
        },
    )
    upload_snapshot = save_latest_upload(filename, rows, list(rows[0].keys()) if rows else [])

    return {
        'status': 'processed',
        'filename': filename,
        'row_count': len(rows),
        'columns': list(rows[0].keys()) if rows else [],
        'preview': rows[:10],
        'rows_for_analysis': rows[:500],
        'event': event,
        'latest_upload': upload_snapshot,
    }


@router.get('/events')
def get_recent_ingestion_events(limit: int = 20) -> Dict[str, Any]:
    safe_limit = max(1, min(limit, 100))
    return {
        'events': recent_events(safe_limit),
        'count': safe_limit,
    }
