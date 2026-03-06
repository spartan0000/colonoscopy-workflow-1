from fastapi import APIRouter
from app.services.triage_services import final_triage
from app.services.parsing.triage.colonoscopy_triage_model import ColonoscopySummary, TriageRequest


router = APIRouter(tags=["triage"])


@router.post("/triage")
async def triage(request: TriageRequest):
    #load prompt
    report = request.report_text
    result = await final_triage(report)
    return result