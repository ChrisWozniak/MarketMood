import asyncio
import json
import os
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from database import get_session
from models import DigestRun, Settings
from services.scheduler import run_digest_job, get_next_run_time, REPORTS_DIR

router = APIRouter()


@router.post("/run-now")
async def run_now(session: Session = Depends(get_session)):
    """Trigger an immediate digest run."""
    await run_digest_job(trigger="manual")
    # Return the latest run
    runs = session.exec(select(DigestRun).order_by(DigestRun.id.desc()).limit(1)).all()
    if runs:
        run = runs[0]
        return {
            "status": run.status,
            "run_at": run.run_at.isoformat(),
            "trigger": run.trigger,
            "error": run.error_message,
        }
    return {"status": "triggered"}


@router.get("/history")
def get_history(limit: int = 20, session: Session = Depends(get_session)):
    """List past digest runs (most recent first)."""
    runs = session.exec(
        select(DigestRun).order_by(DigestRun.id.desc()).limit(limit)
    ).all()
    return [
        {
            "id": r.id,
            "run_at": r.run_at.isoformat(),
            "trigger": r.trigger,
            "status": r.status,
            "error": r.error_message,
        }
        for r in runs
    ]


@router.get("/history/{run_id}")
def get_history_item(run_id: int, session: Session = Depends(get_session)):
    """Get full report for a specific digest run."""
    run = session.get(DigestRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "id": run.id,
        "run_at": run.run_at.isoformat(),
        "trigger": run.trigger,
        "status": run.status,
        "html": run.summary_html,
        "json": json.loads(run.summary_json) if run.summary_json else None,
        "error": run.error_message,
    }


@router.get("/next-run")
def next_run():
    return {"next_run": get_next_run_time()}


@router.get("/reports", response_class=HTMLResponse)
def list_reports(request: Request):
    """Return an HTML index of all saved digest report files."""
    from datetime import datetime as _dt

    # Absolute base URL of the backend (e.g. http://localhost:8000)
    # This ensures report links always open the raw HTML, not the React SPA.
    backend_base = str(request.base_url).rstrip("/")

    try:
        files = sorted(
            [f for f in os.listdir(REPORTS_DIR) if f.endswith(".html")],
            reverse=True,
        )
    except FileNotFoundError:
        files = []

    rows = ""
    for f in files:
        # Parse date from filename: digest_YYYY-MM-DD_HH-MM-SS.html
        try:
            date_part = f.replace("digest_", "").replace(".html", "")
            dt = _dt.strptime(date_part, "%Y-%m-%d_%H-%M-%S")
            label = dt.strftime("%b %d,  %I:%M %p") + " UTC"
        except ValueError:
            label = f
        rows += (
            f'<tr><td style="padding:8px 16px;">'
            f'<a href="{backend_base}/reports/{f}" target="_blank" '
            f'style="color:#60a5fa;text-decoration:none;font-size:14px;">{label}</a>'
            f'</td></tr>\n'
        )

    body = rows or '<tr><td style="padding:16px;color:#64748b;">No reports found.</td></tr>'

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Digest Reports</title>
  <style>
    body {{ margin: 0; background: #0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #f1f5f9; padding: 32px 24px; }}
    h1 {{ font-size: 22px; font-weight: 700; margin: 0 0 4px 0; color: #f8fafc; }}
    p  {{ color: #64748b; font-size: 13px; margin: 0 0 24px 0; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 680px; background: #1e293b; border-radius: 12px; overflow: hidden; }}
    tr:not(:last-child) {{ border-bottom: 1px solid #334155; }}
    tr:hover {{ background: #273548; }}
  </style>
</head>
<body>
  <h1>📰 Digest Reports</h1>
  <p>Stored in <code style="color:#94a3b8;">digest_reports/</code> &nbsp;·&nbsp; {len(files)} file{"s" if len(files) != 1 else ""}</p>
  <table>
    <tbody>{body}</tbody>
  </table>
</body>
</html>"""
