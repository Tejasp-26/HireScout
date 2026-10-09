"""Rule-based resume parser - the offline fallback when no LLM is available."""

import re

from app.services.resume_models import ParsedResume
from app.services.skills import find_skills

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{3,5}")
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/in/[\w%-]+/?", re.IGNORECASE)
GITHUB_RE = re.compile(r"(?:https?://)?github\.com/[\w-]+/?", re.IGNORECASE)
YEARS_RE = re.compile(r"(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years|yrs)\b", re.IGNORECASE)

SECTION_WORDS = {
    "resume", "curriculum", "vitae", "cv", "profile", "summary", "objective",
    "education", "experience", "work", "skills", "projects", "certifications",
    "contact", "phone", "email", "address", "linkedin", "github", "portfolio",
    "declaration", "references", "hobbies", "interests", "achievements",
    "technical", "professional", "personal", "details", "languages",
}

ROLES = [
    "Machine Learning Engineer", "Software Development Engineer", "Full Stack Developer",
    "Full-Stack Developer", "Backend Engineer", "Backend Developer", "Frontend Engineer",
    "Frontend Developer", "Data Scientist", "Data Engineer", "Data Analyst",
    "DevOps Engineer", "Cloud Engineer", "AI Engineer", "Software Engineer",
    "Software Developer", "Web Developer", "Mobile Developer", "Android Developer",
    "iOS Developer", "QA Engineer", "Test Engineer", "Product Manager", "Project Manager",
    "Business Analyst", "UX Designer", "UI Designer", "HR Manager", "Recruiter",
    "Security Engineer", "Site Reliability Engineer",
]


def extract_email(text: str) -> str | None:
    match = EMAIL_RE.search(text)
    return match.group().lower() if match else None


def extract_phone(text: str) -> str | None:
    for match in PHONE_RE.finditer(text):
        candidate = match.group().strip()
        digits = re.sub(r"\D", "", candidate)
        # Real phone numbers have 10-13 digits; this skips years and date ranges.
        if 10 <= len(digits) <= 13:
            return candidate
    return None


def _first(pattern: re.Pattern, text: str) -> str | None:
    match = pattern.search(text)
    return match.group().rstrip("/").lower() if match else None


def _looks_like_name(words: list[str]) -> bool:
    return (
        2 <= len(words) <= 4
        and all(re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", w) for w in words)
        and not any(w.lower().strip(".") in SECTION_WORDS for w in words)
        and not find_skills(" ".join(words))
    )


def extract_name(text: str, email: str | None) -> str:
    """Pick the most name-like line near the top of the resume.

    Candidates whose words also appear in the person's own email address
    are preferred - a cheap but surprisingly strong confidence signal.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()][:15]
    email_local = (email or "").split("@")[0].lower()

    candidates: list[tuple[int, int, str]] = []
    for position, line in enumerate(lines):
        # "Jane Doe Email: jane@x.com | +1 555..." -> "Jane Doe"
        line = re.split(r"(?i)\b(?:email|e-mail|phone|mobile|tel)\b|[|•@]|https?://", line)[0]
        words = line.replace(",", " ").split()
        if not _looks_like_name(words):
            continue
        email_hits = sum(1 for w in words if len(w) >= 3 and w.lower() in email_local)
        candidates.append((email_hits, -position, " ".join(words)))

    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][2].title() if candidates[0][2].isupper() else candidates[0][2]

    if email_local:
        return re.sub(r"[._\d-]+", " ", email_local).strip().title() or "Unknown Candidate"
    return "Unknown Candidate"


def extract_title(text: str) -> str | None:
    lowered = text.lower()
    hits = [(lowered.find(role.lower()), role) for role in ROLES if role.lower() in lowered]
    # The earliest mention is usually the headline / current role.
    return min(hits)[1] if hits else None


def extract_years(text: str) -> float | None:
    values = [float(v) for v in YEARS_RE.findall(text) if 0 < float(v) <= 45]
    return max(values) if values else None


def parse(text: str) -> ParsedResume:
    email = extract_email(text)
    name = extract_name(text, email)
    title = extract_title(text)
    skills = find_skills(text)

    summary_parts = [f"{name} is"]
    summary_parts.append(f"a {title}" if title else "a candidate")
    if skills:
        summary_parts.append(f"with skills in {', '.join(skills[:6])}")

    return ParsedResume(
        name=name,
        email=email,
        phone=extract_phone(text),
        location=None,
        linkedin=_first(LINKEDIN_RE, text),
        github=_first(GITHUB_RE, text),
        current_title=title,
        current_company=None,
        years_experience=extract_years(text),
        skills=skills,
        education=[],
        experience=[],
        summary=" ".join(summary_parts) + ".",
    )
