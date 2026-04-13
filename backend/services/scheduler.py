"""
Scheduler for MoodMarket — runs hourly social analysis automatically.
"""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

scheduler = AsyncIOScheduler()
SOCIAL_JOB_ID = "social_job"

DEFAULT_REFRESH_HOURS = 1  # Run social analysis every hour by default


async def run_social_job():
    """Core job: collect social data, score sentiment, generate signals."""
    from services.social.aggregator import run_social_analysis
    print("[scheduler] Running social analysis job")
    try:
        await run_social_analysis()
    except Exception as e:
        print(f"[scheduler] Social analysis failed: {e}")


def start_social_schedule(refresh_hours: int = DEFAULT_REFRESH_HOURS):
    """Start or restart the hourly social analysis job."""
    trigger = IntervalTrigger(hours=refresh_hours)
    scheduler.add_job(
        lambda: asyncio.ensure_future(run_social_job()),
        trigger=trigger,
        id=SOCIAL_JOB_ID,
        replace_existing=True,
    )
    print(f"[scheduler] Social analysis scheduled every {refresh_hours}h")
