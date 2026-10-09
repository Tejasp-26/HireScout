from app.models import Candidate, Job
from app.services.matching import extract_requirements, score_candidate


def _job(**kwargs) -> Job:
    defaults = dict(title="Backend Engineer", description="", required_skills=["Python", "AWS", "Docker", "Kafka"],
                    nice_to_have_skills=["Kubernetes"], min_years_experience=4.0)
    return Job(**{**defaults, **kwargs})


def test_score_combines_skills_semantic_and_experience():
    candidate = Candidate(skills=["python", "Amazon Web Services", "Docker", "Kubernetes"], years_experience=2.0)
    result = score_candidate(candidate, _job(), similarity=0.65)

    assert result["matched_skills"] == ["Python", "AWS", "Docker"]
    assert result["missing_skills"] == ["Kafka"]
    assert result["nice_to_have_matched"] == ["Kubernetes"]
    assert result["breakdown"] == {"skills": 75, "semantic": 100, "experience": 50, "nice": 100}
    # 0.5*0.75 + 0.3*1.0 + 0.1*0.5 + 0.1*1.0 = 0.825
    assert result["score"] == 82


def test_missing_signals_are_renormalised():
    candidate = Candidate(skills=["Python", "AWS"], years_experience=None)
    job = _job(required_skills=["Python", "AWS"], nice_to_have_skills=[], min_years_experience=None)
    result = score_candidate(candidate, job, similarity=None)
    assert result["breakdown"] == {"skills": 100}
    assert result["score"] == 100


def test_heuristic_requirement_extraction():
    reqs, method = extract_requirements(
        "Data Engineer", "We need 3+ years building pipelines with Python, Apache Spark and Airflow on GCP."
    )
    assert method == "heuristic"
    assert {"Python", "Apache Spark", "Airflow", "GCP"} <= set(reqs.required_skills)
    assert reqs.min_years_experience == 3
