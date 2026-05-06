from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from services.email_sender import load_email_config, save_email_config
from dependencies import limiter, require_admin_key

router = APIRouter()


class EmailConfig(BaseModel):
    enabled: bool = False
    smtp_sender: str = ""
    smtp_password: str = ""
    recipients: list[str] = []
    email_theme: str = "dark"


@router.get("/email", dependencies=[Depends(require_admin_key)])
@limiter.limit("10/minute")
def get_email_config(request: Request):
    """Return email distribution config (password masked)."""
    cfg = load_email_config()
    masked = dict(cfg)
    if masked.get("smtp_password"):
        masked["smtp_password"] = "•" * 8
        masked["smtp_password_set"] = True
    else:
        masked["smtp_password_set"] = False
    return masked


@router.post("/email", dependencies=[Depends(require_admin_key)])
@limiter.limit("10/minute")
def save_email(request: Request, config: EmailConfig):
    """Save email distribution settings."""
    existing = load_email_config()
    password = config.smtp_password
    if password == "•" * 8:
        password = existing.get("smtp_password", "")
    recipients = [r.strip() for r in config.recipients if r.strip()]
    save_email_config({
        "enabled": config.enabled,
        "smtp_sender": config.smtp_sender.strip(),
        "smtp_password": password,
        "recipients": recipients,
        "email_theme": config.email_theme,
    })
    return {"status": "ok", "recipient_count": len(recipients)}


@router.post("/email/test", dependencies=[Depends(require_admin_key)])
@limiter.limit("5/minute")
async def test_email(request: Request):
    """Send a test email using current saved configuration."""
    from datetime import datetime
    from services.email_sender import send_report_email

    cfg = load_email_config()
    if not cfg.get("enabled"):
        raise HTTPException(status_code=400, detail="Email distribution is disabled. Enable it and save first.")
    recipients = [r for r in cfg.get("recipients", []) if r.strip()]
    if not recipients:
        raise HTTPException(status_code=400, detail="No recipients configured.")
    if not cfg.get("smtp_sender") or not cfg.get("smtp_password"):
        raise HTTPException(status_code=400, detail="Gmail sender or App Password not configured.")

    try:
        sent = await send_report_email(
            mood_scores={
                "Economy": {"score": 42, "label": "Positive"},
                "Technology & AI": {"score": -5, "label": "Neutral"},
            },
            trending_topics=[{
                "category": "Economy",
                "trend": "rising",
                "sub_topics": ["Fed holds rates steady at 4.25%", "Jobs growth beats forecast"],
            }],
            investment_signals=[{
                "category": "Economy",
                "signal": "bullish",
                "insight": "This is a test email from Market Mood. Real reports include full sentiment analysis, investment signals, and prediction market data.",
                "tickers": ["SPY", "QQQ"],
                "confidence": "medium",
            }],
            prediction_markets=[{
                "source": "Kalshi",
                "question": "Will Fed cut rates in June?",
                "yes_pct": 63.0,
                "no_pct": 37.0,
                "volume_usd": 450000,
                "category": "Economy",
            }],
            captured_at=datetime.utcnow(),
            run_type="Test",
            config=cfg,
        )
        if sent:
            return {"status": "ok", "message": f"Test email sent to {len(recipients)} recipient(s)."}
        raise HTTPException(status_code=500, detail="Email not sent — unknown error.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SMTP error: {e}")
