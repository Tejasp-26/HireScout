from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# -- auth ----------------------------------------------------------------------

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class LoginRequest(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(max_length=200)


class UserOut(ORMModel):
    id: int
    name: str
    email: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(pattern=EMAIL_PATTERN, max_length=255)
    password: str = Field(min_length=8, max_length=72)
    role: Literal["admin", "recruiter"] = "recruiter"


# -- candidates ----------------------------------------------------------------

class CandidateSummary(ORMModel):
    id: int
    name: str
    email: Optional[str]
    location: Optional[str]
    current_title: Optional[str]
    current_company: Optional[str]
    years_experience: Optional[float]
    skills: list[str]
    source: str
    created_at: datetime


class CandidateDetail(CandidateSummary):
    phone: Optional[str]
    linkedin: Optional[str]
    github: Optional[str]
    education: list[dict]
    experience: list[dict]
    summary: Optional[str]
    resume_text: str
    original_filename: str
    parse_method: str


class CandidatePage(BaseModel):
    items: list[CandidateSummary]
    total: int
    page: int
    page_size: int


class SearchHit(BaseModel):
    candidate: CandidateSummary
    similarity: float


# -- jobs ----------------------------------------------------------------------

class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=20, max_length=20000)


class JobUpdate(BaseModel):
    required_skills: Optional[list[str]] = None
    nice_to_have_skills: Optional[list[str]] = None
    min_years_experience: Optional[float] = None


class JobOut(ORMModel):
    id: int
    title: str
    description: str
    required_skills: list[str]
    nice_to_have_skills: list[str]
    min_years_experience: Optional[float]
    extraction_method: str
    created_at: datetime


class MatchOut(BaseModel):
    candidate: CandidateSummary
    score: int
    breakdown: dict[str, int]
    matched_skills: list[str]
    missing_skills: list[str]
    nice_to_have_matched: list[str]
    rationale: Optional[str] = None


# -- ingestion -----------------------------------------------------------------

class IngestionLogOut(ORMModel):
    id: int
    source: str
    filename: str
    status: str
    detail: Optional[str]
    candidate_id: Optional[int]
    candidate_name: Optional[str]
    email: Optional[str]
    created_at: datetime


# -- assistant -----------------------------------------------------------------

class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class ChatResponse(BaseModel):
    answer: str
    candidates: list[CandidateSummary]
    ai_enabled: bool
