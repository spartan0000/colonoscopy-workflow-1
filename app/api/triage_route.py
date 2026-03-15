from fastapi import APIRouter, HTTPException, Depends
from app.db.session import get_db
from app.services import triage_services
from app.services.triage.colonoscopy_triage_model import ColonoscopySummary, TriageRequest
from app.db.models.case import SampleTestCase

from sqlalchemy.orm import Session



router = APIRouter(tags=["triage"])


@router.post("/triage")
async def triage_endpoint(request: TriageRequest, db: Session = Depends(get_db)):

    # if not request.report_text or not request.report_text.strip():
    #     raise HTTPException(
    #         status_code=400,
    #         detail="Report text is required and cannot be empty."
    #     )

    report = request.report_text
    
    final_triage_result = await triage_services.process_triage(report, db)

    
    return final_triage_result


