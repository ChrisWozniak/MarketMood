from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os

load_dotenv()

from database import create_db_and_tables, engine
from services.scheduler import scheduler, load_schedule_from_db, REPORTS_DIR
from routers import digest, config, social

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_db_and_tables()
    load_schedule_from_db()
    scheduler.start()
    yield
    # Shutdown
    scheduler.shutdown(wait=False)


app = FastAPI(title="News Digest API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(digest.router, prefix="/api/digest", tags=["digest"])
app.include_router(config.router, prefix="/api/settings", tags=["settings"])
app.include_router(social.router, prefix="/api/social", tags=["social"])

# Serve saved HTML report files
os.makedirs(REPORTS_DIR, exist_ok=True)
app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")


@app.get("/api/health")
def health():
    return {"status": "ok"}


FRONTEND_DIST = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
)
if os.path.exists(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
