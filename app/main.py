from contextlib import asynccontextmanager
from app.db.session import engine, Base
from fastapi import FastAPI
from app.api.triage_route import router as triage_router
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173"
]



app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_credentials = True,
    allow_headers = ["*"],
    allow_methods = ["*"],
)



app.include_router(triage_router) 

#app.include_router(transcription_router)


