from fastapi import APIRouter, HTTPException, Depends
from app.db.session import get_db
from app.services import triage_services
from app.services.triage.colonoscopy_triage_model import ColonoscopySummary, TriageRequest

from sqlalchemy.orm import Session



router = APIRouter(tags=["triage"])


@router.post("/triage")
async def triage_endpoint(request: TriageRequest, db: Session = Depends(get_db)):

    # if not request.report_text or request.report_text.strip():
    #     raise HTTPException(
    #         status_code=400,
    #         detail="Report text is required and cannot be empty."
    #     )

    report = request.report_text
    json_data = await triage_services.format_query_json(report)
    normalized_data = triage_services.normalize_data(json_data)
    preliminary_triage = triage_services.triage(normalized_data)
    final_triage = triage_services.triage_with_age_out(normalized_data, preliminary_triage)

    return final_triage


