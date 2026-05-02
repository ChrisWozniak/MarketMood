import json
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlmodel import Session, select
from database import get_session
from models import SocialSnapshot

router = APIRouter()


class AnalyzeRequest(BaseModel):
    custom_tickers: list[str] | None = None
    theme: str = "dark"


@router.post("/analyze")
async def analyze(
    req: AnalyzeRequest = Body(default_factory=AnalyzeRequest),
    session: Session = Depends(get_session),
):
    """Trigger a fresh social analysis and return barometer scores per category."""
    from services.social.aggregator import run_social_analysis
    try:
        snapshot = await run_social_analysis(custom_tickers=req.custom_tickers, run_type="Manual", theme=req.theme)
        return {
            "status": "success",
            "captured_at": snapshot.captured_at.isoformat(),
            "mood_scores": json.loads(snapshot.mood_scores),
            "trending_topics": json.loads(snapshot.trending_topics),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/latest")
def get_latest(session: Session = Depends(get_session)):
    """Return the latest barometer scores for all categories."""
    snapshots = session.exec(
        select(SocialSnapshot).order_by(SocialSnapshot.id.desc()).limit(1)
    ).all()
    if not snapshots:
        raise HTTPException(status_code=404, detail="No data yet. Run /analyze first.")
    s = snapshots[0]
    return {
        "captured_at": s.captured_at.isoformat(),
        "mood_scores": json.loads(s.mood_scores),
        "trending_topics": json.loads(s.trending_topics),
        "trend_history": json.loads(s.trend_history),
    }


@router.get("/history")
def get_history(limit: int = 10, session: Session = Depends(get_session)):
    """Return recent snapshot history for momentum tracking."""
    snapshots = session.exec(
        select(SocialSnapshot).order_by(SocialSnapshot.id.desc()).limit(limit)
    ).all()
    return [
        {
            "id": s.id,
            "captured_at": s.captured_at.isoformat(),
            "mood_scores": json.loads(s.mood_scores),
        }
        for s in snapshots
    ]
