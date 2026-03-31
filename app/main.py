from fastapi import FastAPI
from app.api.triage_route import router as triage_router

app = FastAPI()

app.include_router(triage_router) 
