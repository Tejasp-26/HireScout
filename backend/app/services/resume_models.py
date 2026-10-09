"""Structured resume shape shared by the LLM and heuristic parsers.

The models here have no default values on purpose: they double as the
Gemini response schema, and keeping every field explicit (nullable where
it can be missing) gives the most predictable structured output.
"""

from typing import Optional

from pydantic import BaseModel, Field


class EducationItem(BaseModel):
    degree: str = Field(description="Degree or qualification, e.g. 'B.Tech Computer Science'")
    institution: str
    year: Optional[str] = Field(description="Graduation year or range if stated")


class ExperienceItem(BaseModel):
    title: str
    company: str
    start: Optional[str] = Field(description="Start date as written, e.g. 'Jan 2022'")
    end: Optional[str] = Field(description="End date as written, or 'Present'")
    highlights: list[str] = Field(description="Up to 3 short achievement bullets")


class ParsedResume(BaseModel):
    name: str = Field(description="Candidate's full name")
    email: Optional[str]
    phone: Optional[str]
    location: Optional[str] = Field(description="City / region / country")
    linkedin: Optional[str]
    github: Optional[str]
    current_title: Optional[str] = Field(description="Most recent job title, or target role for students")
    current_company: Optional[str]
    years_experience: Optional[float] = Field(
        description="Total years of professional experience; 0 for students/freshers"
    )
    skills: list[str] = Field(description="Technical and professional skills, deduplicated")
    education: list[EducationItem]
    experience: list[ExperienceItem] = Field(description="Most recent first")
    summary: str = Field(description="Two-sentence neutral recruiter summary of the candidate")
