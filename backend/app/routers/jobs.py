from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Job, User
from app.schemas import CandidateSummary, JobCreate, JobOut, JobUpdate, MatchOut
from app.security import get_current_user
from app.services.matching import explain_matches, extract_requirements, rank_candidates
from app.services.skills import normalize_skills

router = APIRouter(prefix="/jobs", tags=["jobs"], dependencies=[Depends(get_current_user)])


def _get_or_404(db: Session, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    return db.scalars(select(Job).order_by(Job.created_at.desc())).all()


@router.post("", response_model=JobOut, status_code=201)
def create_job(body: JobCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    reqs, method = extract_requirements(body.title.strip(), body.description.strip())
    job = Job(
        title=body.title.strip(),
        description=body.description.strip(),
        required_skills=reqs.required_skills,
        nice_to_have_skills=reqs.nice_to_have_skills,
        min_years_experience=reqs.min_years_experience,
        extraction_method=method,
        created_by=user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, job_id)


@router.patch("/{job_id}", response_model=JobOut)
def update_job(job_id: int, body: JobUpdate, db: Session = Depends(get_db)):
    """Let the recruiter correct the extracted requirements."""
    job = _get_or_404(db, job_id)
    if body.required_skills is not None:
        job.required_skills = normalize_skills(body.required_skills)
    if body.nice_to_have_skills is not None:
        job.nice_to_have_skills = normalize_skills(body.nice_to_have_skills)
    if "min_years_experience" in body.model_fields_set:
        job.min_years_experience = body.min_years_experience
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    db.delete(_get_or_404(db, job_id))
    db.commit()


@router.get("/{job_id}/matches", response_model=list[MatchOut])
def job_matches(
    job_id: int,
    limit: int = Query(20, ge=1, le=100),
    explain: int = Query(0, ge=0, le=10, description="Add AI rationale for the top N matches"),
    db: Session = Depends(get_db),
):
    job = _get_or_404(db, job_id)
    ranked = rank_candidates(db, job, limit=limit)
    rationales = explain_matches(job, ranked[:explain]) if explain else {}
    return [
        MatchOut(
            **{**r, "candidate": CandidateSummary.model_validate(r["candidate"])},
            rationale=rationales.get(r["candidate"].id),
        )
        for r in ranked
    ]
