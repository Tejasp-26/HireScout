from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.db import get_db
from app.models import Candidate
from app.schemas import CandidateDetail, CandidatePage, CandidateSummary, SearchHit
from app.security import get_current_user
from app.services.resume_parser import parse_resume
from app.services.skills import skill_key
from app.services.vector_index import vector_index

router = APIRouter(tags=["candidates"], dependencies=[Depends(get_current_user)])


def _get_or_404(db: Session, candidate_id: int) -> Candidate:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.get("/candidates", response_model=CandidatePage)
def list_candidates(
    q: str = "",
    skill: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Keyword filter over name / title / company / skills, newest first."""
    candidates = db.scalars(select(Candidate).order_by(Candidate.created_at.desc())).all()

    if q.strip():
        needle = q.strip().lower()
        candidates = [
            c for c in candidates
            if needle in " ".join(
                [c.name or "", c.current_title or "", c.current_company or "", c.location or "", *(c.skills or [])]
            ).lower()
        ]
    if skill.strip():
        wanted = skill_key(skill)
        candidates = [c for c in candidates if wanted in {skill_key(s) for s in c.skills or []}]

    start = (page - 1) * page_size
    return CandidatePage(
        items=candidates[start:start + page_size], total=len(candidates), page=page, page_size=page_size
    )


@router.get("/search", response_model=list[SearchHit])
def semantic_search(
    q: str = Query(..., min_length=2, max_length=500),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Natural-language search, e.g. "backend engineer who knows Kafka"."""
    hits = vector_index.search(q, k=limit)
    by_id = {c.id: c for c in db.scalars(select(Candidate).where(Candidate.id.in_([i for i, _ in hits])))}
    return [
        SearchHit(candidate=CandidateSummary.model_validate(by_id[cid]), similarity=round(score, 4))
        for cid, score in hits
        if cid in by_id
    ]


@router.get("/candidates/{candidate_id}", response_model=CandidateDetail)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, candidate_id)


@router.get("/candidates/{candidate_id}/resume")
def download_resume(candidate_id: int, db: Session = Depends(get_db)):
    candidate = _get_or_404(db, candidate_id)
    path = config.RESUME_DIR / candidate.resume_file
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Resume file is missing from storage")
    return FileResponse(path, media_type="application/pdf", filename=candidate.original_filename)


@router.post("/candidates/{candidate_id}/reparse", response_model=CandidateDetail)
def reparse_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """Re-run parsing on the stored text, e.g. after adding a Gemini key."""
    candidate = _get_or_404(db, candidate_id)
    parsed, method = parse_resume(candidate.resume_text)

    for field in (
        "name", "phone", "location", "linkedin", "github", "current_title",
        "current_company", "years_experience", "skills", "summary",
    ):
        setattr(candidate, field, getattr(parsed, field))
    if parsed.email and parsed.email != candidate.email:
        clash = db.scalar(select(Candidate).where(Candidate.email == parsed.email, Candidate.id != candidate.id))
        if clash is None:
            candidate.email = parsed.email
    candidate.education = [e.model_dump() for e in parsed.education]
    candidate.experience = [e.model_dump() for e in parsed.experience]
    candidate.parse_method = method

    db.commit()
    db.refresh(candidate)
    vector_index.upsert(candidate)
    return candidate


@router.delete("/candidates/{candidate_id}", status_code=204)
def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = _get_or_404(db, candidate_id)
    stored = config.RESUME_DIR / candidate.resume_file
    db.delete(candidate)
    db.commit()
    vector_index.remove(candidate_id)
    stored.unlink(missing_ok=True)
