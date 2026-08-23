from fastapi import APIRouter, HTTPException, Depends
from app.db.session import get_db
from app.services import triage_services
from app.services.triage.colonoscopy_triage_model import ColonoscopySummary, TriageRequest
from app.db.models.case import SampleTestCase

from sqlalchemy.orm import Session

from pydantic import ValidationError



router = APIRouter(tags=["triage"])


@router.post("/triage")
async def triage_endpoint(request: TriageRequest, db: Session = Depends(get_db)):

    if not request.report_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Report text is required and cannot be empty."
        )

    report = request.report_text

    try:

        final_triage_result, triage_id = await triage_services.process_triage(report, db)
    except ValidationError:
        raise HTTPException(status_code=502, detail='Could not extract structured data from report text.')

    
    return {
        'final_result': final_triage_result,
        'triage_id': triage_id,
    }


