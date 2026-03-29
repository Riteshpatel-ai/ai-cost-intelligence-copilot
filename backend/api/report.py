from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from backend.services.report_service import load_latest_report, render_report_pdf

router = APIRouter(tags=['report'])


@router.get('/api/reports/latest')
@router.get('/reports/latest')
def latest_report():
    payload = load_latest_report()
    if not payload:
        return JSONResponse(status_code=404, content={'error': 'No generated report is available yet.'})
    return payload


@router.get('/api/reports/latest-pdf')
@router.get('/reports/latest-pdf')
def latest_report_pdf():
    payload = load_latest_report()
    if not payload:
        raise HTTPException(status_code=404, detail='No generated report is available yet.')

    pdf_bytes = render_report_pdf(payload)
    filename = f"cost-optimization-audit-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.pdf"
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    return StreamingResponse(iter([pdf_bytes]), media_type='application/pdf', headers=headers)
