import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from database import get_session
from models import SocialSnapshot, MarketSnapshot
from dependencies import limiter, require_admin_key

router = APIRouter()


@router.post("/analyze", dependencies=[Depends(require_admin_key)])
@limiter.limit("5/minute")
async def analyze(request: Request, session: Session = Depends(get_session)):
    """Trigger a fresh social media analysis."""
    from services.social.aggregator import run_social_analysis
    try:
        snapshot = await run_social_analysis()
        return {"status": "success", "captured_at": snapshot.captured_at.isoformat()}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/latest")
@limiter.limit("60/minute")
def get_latest(request: Request, session: Session = Depends(get_session)):
    """Return the most recent social snapshot."""
    snapshots = session.exec(
        select(SocialSnapshot).order_by(SocialSnapshot.id.desc()).limit(1)
    ).all()
    if not snapshots:
        raise HTTPException(status_code=404, detail="No social data yet. Run /analyze first.")
    s = snapshots[0]
    return {
        "captured_at": s.captured_at.isoformat(),
        "trending_topics": json.loads(s.trending_topics),
        "mood_scores": json.loads(s.mood_scores),
        "trend_history": json.loads(s.trend_history),
    }


@router.get("/trends/{topic}")
@limiter.limit("60/minute")
def get_trend(request: Request, topic: str, session: Session = Depends(get_session)):
    """Get 30-day trend history for a specific topic."""
    snapshots = session.exec(
        select(SocialSnapshot).order_by(SocialSnapshot.id.desc()).limit(30)
    ).all()
    if not snapshots:
        raise HTTPException(status_code=404, detail="No social data available.")

    trend_points = []
    for s in reversed(snapshots):
        history = json.loads(s.trend_history)
        volume = history.get(topic, 0)
        trend_points.append({"date": s.captured_at.date().isoformat(), "volume": volume})

    return {"topic": topic, "trend": trend_points}


@router.get("/mood")
@limiter.limit("60/minute")
def get_mood(request: Request, session: Session = Depends(get_session)):
    """Return current mood indicators."""
    snapshots = session.exec(
        select(SocialSnapshot).order_by(SocialSnapshot.id.desc()).limit(1)
    ).all()
    if not snapshots:
        raise HTTPException(status_code=404, detail="No social data yet.")
    return json.loads(snapshots[0].mood_scores)


@router.get("/markets")
@limiter.limit("60/minute")
def get_markets(request: Request, session: Session = Depends(get_session)):
    """Return the most recent prediction market snapshot."""
    snapshots = session.exec(
        select(MarketSnapshot).order_by(MarketSnapshot.id.desc()).limit(1)
    ).all()
    if not snapshots:
        return {"captured_at": None, "markets": []}
    s = snapshots[0]
    return {
        "captured_at": s.captured_at.isoformat(),
        "markets": json.loads(s.markets_json),
    }


@router.post("/markets/refresh", dependencies=[Depends(require_admin_key)])
@limiter.limit("10/minute")
async def refresh_markets(request: Request, session: Session = Depends(get_session)):
    """Fetch fresh market data from Kalshi + Polymarket only (fast, no social analysis)."""
    from datetime import datetime
    try:
        from services.social.markets_client import fetch_top_markets
        markets = await fetch_top_markets(12)
        snapshot = MarketSnapshot(
            captured_at=datetime.utcnow(),
            markets_json=json.dumps(markets),
        )
        session.add(snapshot)
        session.commit()
        session.refresh(snapshot)
        return {
            "status": "ok",
            "captured_at": snapshot.captured_at.isoformat(),
            "markets": markets,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e), "markets": []}


@router.get("/history")
@limiter.limit("60/minute")
def get_history(request: Request, limit: int = 10, session: Session = Depends(get_session)):
    snapshots = session.exec(
        select(SocialSnapshot).order_by(SocialSnapshot.id.desc()).limit(limit)
    ).all()
    return [
        {
            "id": s.id,
            "captured_at": s.captured_at.isoformat(),
            "topic_count": len(json.loads(s.trending_topics)),
        }
        for s in snapshots
    ]
