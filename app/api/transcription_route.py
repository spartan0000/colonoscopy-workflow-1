from fastapi import Depends, APIRouter, HTTPException, UploadFile
from app.db.session import get_db
from app.services import transcription_services
from app.services.transcribe.colonoscopy_transcription_model import ColonoscopyReport
from sqlalchemy.orm import Session


router = APIRouter(tags=['transcription'])

