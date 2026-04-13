from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os

load_dotenv()

from database import create_db_and_tables
from services.scheduler import scheduler, start_social_schedule
from routers import sentiment, signals, social

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    start_social_schedule(refresh_hours=1)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="MoodMarket API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sentiment.router, prefix="/api/sentiment", tags=["sentiment"])
app.include_router(signals.router,   prefix="/api/signals",   tags=["signals"])
app.include_router(social.router,    prefix="/api/social",    tags=["social"])


@app.get("/api/health")
def health():
    return {"status": "ok"}


FRONTEND_DIST = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
)
if os.path.exists(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
