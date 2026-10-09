from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Candidate, IngestionLog, Job
from app.security import get_current_user
from app.services import drive_sync, llm
from app.services.vector_index import vector_index

router = APIRouter(tags=["analytics"], dependencies=[Depends(get_current_user)])


def _as_utc(value: datetime) -> datetime:
    # SQLite hands back naive datetimes even for timezone-aware columns.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@router.get("/analytics")
def analytics(db: Session = Depends(get_db)):
    candidates = db.scalars(select(Candidate)).all()
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=29)

    skills = Counter(s for c in candidates for s in c.skills or [])
    titles = Counter(c.current_title for c in candidates if c.current_title)
    sources = Counter(c.source for c in candidates)
    methods = Counter(c.parse_method for c in candidates)

    per_day = Counter(
        _as_utc(c.created_at).date().isoformat()
        for c in candidates
        if _as_utc(c.created_at) >= since
    )
    timeline = [
        {"date": (since + timedelta(days=i)).date().isoformat(),
         "count": per_day.get((since + timedelta(days=i)).date().isoformat(), 0)}
        for i in range(30)
    ]

    experience_buckets = Counter()
    for c in candidates:
        y = c.years_experience
        bucket = (
            "Unknown" if y is None else
            "0-1" if y < 1 else
            "1-3" if y < 3 else
            "3-5" if y < 5 else
            "5-10" if y < 10 else "10+"
        )
        experience_buckets[bucket] += 1

    log_status = dict(
        db.execute(select(IngestionLog.status, func.count()).group_by(IngestionLog.status)).all()
    )

    return {
        "totals": {
            "candidates": len(candidates),
            "jobs": db.scalar(select(func.count()).select_from(Job)) or 0,
            "added_last_7_days": sum(
                1 for c in candidates if _as_utc(c.created_at) >= now - timedelta(days=7)
            ),
            "unique_skills": len(skills),
        },
        "top_skills": [{"skill": s, "count": n} for s, n in skills.most_common(12)],
        "top_titles": [{"title": t, "count": n} for t, n in titles.most_common(8)],
        "experience": [
            {"bucket": b, "count": experience_buckets.get(b, 0)}
            for b in ["0-1", "1-3", "3-5", "5-10", "10+", "Unknown"]
        ],
        "sources": dict(sources),
        "parse_methods": dict(methods),
        "ingestion_status": log_status,
        "timeline": timeline,
        "system": {
            "ai_enabled": llm.enabled(),
            "drive_configured": drive_sync.configured(),
            "search_index_size": vector_index.size,
            "search_index_ready": vector_index.ready,
        },
    }
