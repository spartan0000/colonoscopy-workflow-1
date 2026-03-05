from fastapi import APIRouter
from app.services.triage_services import final_triage
from app.services.parsing.triage.colonoscopy_triage_model import ColonoscopySummary, UserInput


router = APIRouter(prefix="/triage", tags=["triage"])


@router.post("/")
async def triage(request: UserInput):
    #load prompt
    result = await final_triage(request)
    return result