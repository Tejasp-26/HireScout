from app.services import heuristic_parser
from app.services.pdf_text import repair_letter_spacing
from app.services.skills import find_skills, normalize_skills, skill_key

RESUME = """PRIYA SHARMA
Senior Backend Engineer
priya.sharma@example.com | +91 98765 43210 | linkedin.com/in/priya-sharma
Bengaluru, India

SUMMARY
Backend engineer with 6+ years of experience building Python and Go services on AWS.

SKILLS
Python, FastAPI, PostgreSQL, Docker, Kubernetes, Kafka, ReactJS

EXPERIENCE
Software Engineer, Acme Corp (2019 - 2024)
"""


def test_heuristic_parse_extracts_core_fields():
    parsed = heuristic_parser.parse(RESUME)

    assert parsed.name == "Priya Sharma"
    assert parsed.email == "priya.sharma@example.com"
    assert parsed.phone and parsed.phone.replace(" ", "").endswith("9876543210")
    assert parsed.linkedin == "linkedin.com/in/priya-sharma"
    assert parsed.years_experience == 6
    assert parsed.current_title == "Backend Engineer"
    for skill in ["Python", "Go", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Kafka", "React", "AWS"]:
        assert skill in parsed.skills


def test_name_prefers_line_matching_email():
    text = "Curriculum Vitae\nData Platform Team\nArjun Mehta\narjun.mehta@example.com"
    assert heuristic_parser.extract_name(text, "arjun.mehta@example.com") == "Arjun Mehta"


def test_name_falls_back_to_email_username():
    assert heuristic_parser.extract_name("SKILLS\nPython", "jane_doe@example.com") == "Jane Doe"


def test_phone_ignores_year_ranges():
    assert heuristic_parser.extract_phone("Worked 2019 - 2024 at Acme") is None


def test_letter_spacing_repair():
    assert repair_letter_spacing("J A N E  D O E\nP y t h o n  D e v") == "JANE DOE\nPython Dev"
    assert repair_letter_spacing("Normal text stays as is") == "Normal text stays as is"


def test_skill_aliases_and_boundaries():
    assert skill_key("ReactJS") == skill_key("react.js") == "react"
    assert normalize_skills(["k8s", "Kubernetes", "postgres", " AWS "]) == ["Kubernetes", "PostgreSQL", "AWS"]

    found = find_skills("Built JavaScript apps with MySQL; let's go to the R&D lab")
    assert "JavaScript" in found and "MySQL" in found
    assert "Java" not in found  # no match inside "JavaScript"
    assert "SQL" not in found  # no match inside "MySQL"
    assert "Go" not in found and "R" not in found
