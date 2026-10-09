"""One pipeline for every resume source: validate -> dedupe -> extract ->
parse -> store -> index -> log."""

import hashlib
import logging
from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.models import Candidate, IngestionLog
from app.services.pdf_text import extract_text
from app.services.resume_parser import parse_resume
from app.services.vector_index import vector_index

log = logging.getLogger(__name__)


@dataclass
class IngestResult:
    filename: str
    status: str  # added | duplicate | failed
    detail: str
    candidate_id: int | None = None
    candidate_name: str | None = None
    email: str | None = None
    parse_method: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _log(db: Session, source: str, result: IngestResult) -> None:
    db.add(
        IngestionLog(
            source=source,
            filename=result.filename,
            status=result.status,
            detail=result.detail,
            candidate_id=result.candidate_id,
            candidate_name=result.candidate_name,
            email=result.email,
        )
    )
    db.commit()


def ingest_resume(
    db: Session,
    content: bytes,
    filename: str,
    source: str = "upload",
    source_ref: str | None = None,
) -> IngestResult:
    try:
        result = _ingest(db, content, filename, source, source_ref)
    except Exception as exc:
        db.rollback()
        log.exception("Failed to ingest %s", filename)
        result = IngestResult(filename, "failed", str(exc) or exc.__class__.__name__)

    try:
        _log(db, source, result)
    except Exception:
        db.rollback()
        log.exception("Could not write ingestion log for %s", filename)
    return result


def _ingest(db, content, filename, source, source_ref) -> IngestResult:
    if not content.startswith(b"%PDF"):
        return IngestResult(filename, "failed", "Not a PDF file")
    if len(content) > config.MAX_UPLOAD_MB * 1024 * 1024:
        return IngestResult(filename, "failed", f"File is larger than {config.MAX_UPLOAD_MB} MB")

    file_hash = hashlib.sha256(content).hexdigest()
    existing = db.scalar(select(Candidate).where(Candidate.file_hash == file_hash))
    if existing:
        return IngestResult(
            filename, "duplicate", "This exact file was already imported",
            existing.id, existing.name, existing.email,
        )

    text = extract_text(content)
    parsed, method = parse_resume(text)

    if parsed.email:
        existing = db.scalar(select(Candidate).where(Candidate.email == parsed.email))
        if existing:
            return IngestResult(
                filename, "duplicate", "A candidate with this email already exists",
                existing.id, existing.name, existing.email,
            )

    config.RESUME_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{file_hash[:20]}.pdf"
    (config.RESUME_DIR / stored_name).write_bytes(content)

    candidate = Candidate(
        name=parsed.name,
        email=parsed.email,
        phone=parsed.phone,
        location=parsed.location,
        linkedin=parsed.linkedin,
        github=parsed.github,
        current_title=parsed.current_title,
        current_company=parsed.current_company,
        years_experience=parsed.years_experience,
        skills=parsed.skills,
        education=[e.model_dump() for e in parsed.education],
        experience=[e.model_dump() for e in parsed.experience],
        summary=parsed.summary,
        resume_text=text,
        resume_file=stored_name,
        original_filename=filename,
        file_hash=file_hash,
        source=source,
        source_ref=source_ref,
        parse_method=method,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    detail = f"Parsed with {'Gemini' if method == 'llm' else 'heuristics'}"
    try:
        vector_index.upsert(candidate)
    except Exception as exc:
        # The candidate is saved; the index self-heals on next startup.
        log.exception("Could not index candidate %s", candidate.id)
        detail += f" (search indexing failed: {exc})"

    return IngestResult(
        filename, "added", detail, candidate.id, candidate.name, candidate.email, method
    )
