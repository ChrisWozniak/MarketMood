import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select
from database import get_session
from models import SocialSnapshot
from dependencies import limiter, require_admin_key

router = APIRouter()


@router.get("/latest")
@limiter.limit("60/minute")
def get_latest_signals(request: Request, session: Session = Depends(get_session)):
    """Return the latest AI-generated investment signals based on current mood scores."""
    snapshots = session.exec(
        select(SocialSnapshot).order_by(SocialSnapshot.id.desc()).limit(1)
    ).all()
    if not snapshots:
        raise HTTPException(status_code=404, detail="No data yet. Run /api/sentiment/analyze first.")
    s = snapshots[0]
    platform_data = json.loads(s.platform_data)

    return {
        "captured_at": s.captured_at.isoformat(),
        "investment_signals": platform_data.get("investment_signals", []),
        "tech_momentum": platform_data.get("tech_momentum", []),
    }


@router.post("/generate", dependencies=[Depends(require_admin_key)])
@limiter.limit("5/minute")
async def generate_signals(request: Request, session: Session = Depends(get_session)):
    """
    Re-run Gemini investment signal and tech momentum analysis
    on the most recent snapshot without re-fetching social data.
    """
    snapshots = session.exec(
        select(SocialSnapshot).order_by(SocialSnapshot.id.desc()).limit(1)
    ).all()
    if not snapshots:
        raise HTTPException(status_code=404, detail="No social data available.")

    s = snapshots[0]
    mood_scores     = json.loads(s.mood_scores)
    trending_topics = json.loads(s.trending_topics)
    platform_data   = json.loads(s.platform_data)

    from sqlmodel import select as sql_select
    from models import MarketSnapshot
    try:
        market_snapshots = session.exec(
            sql_select(MarketSnapshot).order_by(MarketSnapshot.id.desc()).limit(1)
        ).all()
        prediction_markets = json.loads(market_snapshots[0].markets_json) if market_snapshots else []
    except Exception:
        prediction_markets = []

    housing_data = {
        "fred":   platform_data.get("fred_indicators", {}),
        "redfin": platform_data.get("redfin_stats", {}),
    }

    from services.investment_signals import generate_investment_signals
    from services.tech_momentum import generate_tech_momentum

    signals  = await generate_investment_signals(
        mood_scores, trending_topics,
        prediction_markets=prediction_markets,
        housing_data=housing_data,
    )
    momentum = await generate_tech_momentum(trending_topics)

    platform_data["investment_signals"] = signals
    platform_data["tech_momentum"] = momentum
    s.platform_data = json.dumps(platform_data)
    session.add(s)
    session.commit()

    return {
        "status": "ok",
        "investment_signals": signals,
        "tech_momentum": momentum,
    }
