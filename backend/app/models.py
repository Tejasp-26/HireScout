from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="recruiter")  # admin | recruiter
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    location: Mapped[Optional[str]] = mapped_column(String(200))
    linkedin: Mapped[Optional[str]] = mapped_column(String(300))
    github: Mapped[Optional[str]] = mapped_column(String(300))

    current_title: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    current_company: Mapped[Optional[str]] = mapped_column(String(200))
    years_experience: Mapped[Optional[float]] = mapped_column(Float)

    # Lists stored as JSON so they round-trip cleanly instead of comma strings.
    skills: Mapped[list] = mapped_column(JSON, default=list)
    education: Mapped[list] = mapped_column(JSON, default=list)
    experience: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[Optional[str]] = mapped_column(Text)

    resume_text: Mapped[str] = mapped_column(Text, default="")
    resume_file: Mapped[str] = mapped_column(String(300))  # stored filename in RESUME_DIR
    original_filename: Mapped[str] = mapped_column(String(300))
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    source: Mapped[str] = mapped_column(String(20), default="upload")  # upload | drive
    source_ref: Mapped[Optional[str]] = mapped_column(String(200), index=True)  # e.g. Drive file id
    parse_method: Mapped[str] = mapped_column(String(20), default="heuristic")  # llm | heuristic

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    nice_to_have_skills: Mapped[list] = mapped_column(JSON, default=list)
    min_years_experience: Mapped[Optional[float]] = mapped_column(Float)
    extraction_method: Mapped[str] = mapped_column(String(20), default="heuristic")
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IngestionLog(Base):
    __tablename__ = "ingestion_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(20))
    filename: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20))  # added | duplicate | failed
    detail: Mapped[Optional[str]] = mapped_column(Text)
    candidate_id: Mapped[Optional[int]] = mapped_column(Integer)
    candidate_name: Mapped[Optional[str]] = mapped_column(String(200))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
