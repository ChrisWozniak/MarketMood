import asyncio
import json
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel import Session, select

scheduler = AsyncIOScheduler()
DIGEST_JOB_ID = "digest_job"
SOCIAL_JOB_ID = "social_job"

REPORTS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "digest_reports")
)


def _save_report_file(html: str, run_at: datetime) -> str | None:
    """Save digest HTML to digest_reports/. Returns filename or None on failure."""
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        filename = f"digest_{run_at.strftime('%Y-%m-%d_%H-%M-%S')}.html"
        path = os.path.join(REPORTS_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[scheduler] Report saved: {filename}")
        return filename
    except Exception as e:
        print(f"[scheduler] Failed to save report file: {e}")
        return None


async def run_digest_job(trigger: str = "scheduled"):
    """Core job: fetch news, summarize, email, save to DB."""
    from database import engine
    from models import Settings, DigestRun
    from services.news_fetcher import fetch_all_categories
    from services.summarizer import summarize_all, build_html_report, build_json_report
    from services.email_sender import send_digest

    print(f"[scheduler] Running digest job ({trigger})")
    run_at = datetime.utcnow()

    with Session(engine) as session:
        settings = session.get(Settings, 1)
        if not settings:
            print("[scheduler] No settings found — skipping.")
            return

        categories = json.loads(settings.categories)
        email = settings.email

    try:
        import json as _json
        from services.social.markets_client import fetch_top_markets
        tickers = _json.loads(settings.market_tickers or "[]")
        local_locations = _json.loads(settings.local_locations or "[]")
        world_countries = _json.loads(settings.world_countries or "[]")
        category_data = await fetch_all_categories(
            categories,
            max_per_category=settings.articles_per_category,
            market_tickers=tickers or None,
            local_locations=local_locations or None,
            world_countries=world_countries or None,
        )
        summaries, market_data = await asyncio.gather(
            summarize_all(category_data),
            fetch_top_markets(10),
        )

        html = build_html_report(summaries, run_at, trigger, markets=market_data, timezone=settings.timezone)
        report_json = json.dumps(build_json_report(summaries, run_at, trigger))

        subject = f"Your News Digest — {run_at.strftime('%B %d, %Y')}"
        if email:
            send_digest(email, html, subject)

        # Save HTML report file to digest_reports/
        _save_report_file(html, run_at)

        digest_run = DigestRun(
            run_at=run_at,
            trigger=trigger,
            status="success",
            summary_html=html,
            summary_json=report_json,
        )
    except Exception as e:
        print(f"[scheduler] Digest failed: {e}")
        digest_run = DigestRun(
            run_at=run_at,
            trigger=trigger,
            status="failed",
            error_message=str(e),
        )

    with Session(engine) as session:
        session.add(digest_run)
        session.commit()


async def run_social_job():
    """Core job: collect social data and save snapshot."""
    from services.social.aggregator import run_social_analysis
    print("[scheduler] Running social analysis job")
    try:
        await run_social_analysis()
    except Exception as e:
        print(f"[scheduler] Social analysis failed: {e}")


def _build_digest_trigger(settings):
    """Build APScheduler trigger from Settings. Returns None if disabled."""
    tz = settings.timezone or "America/New_York"
    stype = settings.schedule_type
    svalue = settings.schedule_value

    if stype == "disabled":
        return None
    elif stype == "daily":
        hour, minute = (svalue.split(":") + ["0"])[:2]
        return CronTrigger(hour=int(hour), minute=int(minute), timezone=tz)
    elif stype == "hourly":
        hours = int(svalue) if svalue.isdigit() else 1
        return IntervalTrigger(hours=hours)
    elif stype == "custom":
        # svalue is a cron expression: "0 9 * * mon,tue,wed,thu,fri"
        parts = svalue.split()
        if len(parts) == 5:
            minute, hour, day, month, day_of_week = parts
            return CronTrigger(
                minute=minute, hour=hour, day=day,
                month=month, day_of_week=day_of_week, timezone=tz
            )
    # Fallback: daily 9am
    return CronTrigger(hour=9, minute=0, timezone=tz)


def load_schedule_from_db():
    """Called on startup to restore schedule from DB."""
    from database import engine
    from models import Settings

    with Session(engine) as session:
        settings = session.get(Settings, 1)
        if not settings or not settings.email:
            print("[scheduler] No schedule configured yet.")
            return

        trigger = _build_digest_trigger(settings)
        scheduler.add_job(
            lambda: asyncio.ensure_future(run_digest_job("scheduled")),
            trigger=trigger,
            id=DIGEST_JOB_ID,
            replace_existing=True,
        )

        social_trigger = IntervalTrigger(hours=settings.social_refresh_hours)
        scheduler.add_job(
            lambda: asyncio.ensure_future(run_social_job()),
            trigger=social_trigger,
            id=SOCIAL_JOB_ID,
            replace_existing=True,
        )
        print(f"[scheduler] Schedule loaded: {settings.schedule_type} / {settings.schedule_value}")


def update_schedule(settings):
    """Update the digest schedule job (called after settings change)."""
    trigger = _build_digest_trigger(settings)
    if trigger is None:
        # Remove job if schedule is disabled
        if scheduler.get_job(DIGEST_JOB_ID):
            scheduler.remove_job(DIGEST_JOB_ID)
        print("[scheduler] Schedule disabled — job removed.")
    else:
        scheduler.add_job(
            lambda: asyncio.ensure_future(run_digest_job("scheduled")),
            trigger=trigger,
            id=DIGEST_JOB_ID,
            replace_existing=True,
        )

    social_trigger = IntervalTrigger(hours=settings.social_refresh_hours)
    scheduler.add_job(
        lambda: asyncio.ensure_future(run_social_job()),
        trigger=social_trigger,
        id=SOCIAL_JOB_ID,
        replace_existing=True,
    )
    print(f"[scheduler] Schedule updated: {settings.schedule_type} / {settings.schedule_value}")


def get_next_run_time() -> str | None:
    job = scheduler.get_job(DIGEST_JOB_ID)
    if job and job.next_run_time:
        return job.next_run_time.isoformat()
    return None
