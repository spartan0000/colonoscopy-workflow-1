from fastapi import FastAPI
from app.api.triage_route import router as triage_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins = [*],
    allow_headers = [*],
    allow_methods = [*],
)

app.include_router(triage_router) 

#app.include_router(transcription_router)


