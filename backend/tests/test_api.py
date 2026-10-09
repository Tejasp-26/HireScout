from tests.conftest import make_pdf

ALICE = [
    "Alice Nguyen",
    "Machine Learning Engineer",
    "alice.nguyen@example.com  +1 415 555 0134",
    "5 years of experience with Python, PyTorch, AWS and Docker.",
    "Built NLP models and deployed them with Kubernetes.",
]
BOB = [
    "Bob Okafor",
    "Frontend Developer",
    "bob.okafor@example.com",
    "3 years building React, TypeScript and Tailwind CSS interfaces.",
]


def _upload(client, lines, name):
    return client.post("/resumes/upload", files={"file": (name, make_pdf(lines), "application/pdf")}).json()


def test_requires_auth(client):
    from fastapi.testclient import TestClient

    from app.main import app

    anonymous = TestClient(app)
    assert anonymous.get("/candidates").status_code == 401
    assert anonymous.post("/auth/login", json={"email": "admin@test.dev", "password": "wrong"}).status_code == 401


def test_full_flow(client):
    alice = _upload(client, ALICE, "alice.pdf")
    assert alice["status"] == "added", alice
    assert alice["candidate_name"] == "Alice Nguyen"
    assert alice["parse_method"] == "heuristic"
    assert _upload(client, BOB, "bob.pdf")["status"] == "added"

    # Same file again, and the same person in a different file.
    assert _upload(client, ALICE, "alice.pdf")["status"] == "duplicate"
    assert _upload(client, ALICE + ["Updated 2026"], "alice-v2.pdf")["status"] == "duplicate"

    bad = client.post("/resumes/upload", files={"file": ("x.pdf", b"not a pdf", "application/pdf")}).json()
    assert bad["status"] == "failed"

    page = client.get("/candidates", params={"skill": "pytorch"}).json()
    assert page["total"] == 1 and page["items"][0]["name"] == "Alice Nguyen"

    detail = client.get(f"/candidates/{alice['candidate_id']}").json()
    assert detail["years_experience"] == 5
    assert "PyTorch" in detail["skills"]
    assert client.get(f"/candidates/{alice['candidate_id']}/resume").status_code == 200

    hits = client.get("/search", params={"q": "React TypeScript frontend"}).json()
    assert hits[0]["candidate"]["name"] == "Bob Okafor"

    job = client.post("/jobs", json={
        "title": "ML Engineer",
        "description": "Looking for 4+ years with Python, PyTorch, AWS and Kafka. Docker experience is required.",
    }).json()
    assert job["extraction_method"] == "heuristic"
    assert job["min_years_experience"] == 4

    matches = client.get(f"/jobs/{job['id']}/matches").json()
    assert matches[0]["candidate"]["name"] == "Alice Nguyen"
    assert "Kafka" in matches[0]["missing_skills"]
    assert matches[0]["score"] > matches[1]["score"]

    chat = client.post("/assistant/chat", json={"message": "Who knows PyTorch?"}).json()
    assert chat["ai_enabled"] is False and chat["candidates"]

    stats = client.get("/analytics").json()
    assert stats["totals"]["candidates"] == 2
    assert stats["ingestion_status"] == {"added": 2, "duplicate": 2, "failed": 1}

    assert client.delete(f"/candidates/{alice['candidate_id']}").status_code == 204
    assert client.get(f"/candidates/{alice['candidate_id']}").status_code == 404
    assert all(h["candidate"]["name"] != "Alice Nguyen" for h in client.get("/search", params={"q": "PyTorch"}).json())


def test_admin_can_create_users(client):
    res = client.post("/auth/users", json={"name": "Rae", "email": "rae@test.dev", "password": "longpassword"})
    assert res.status_code == 201 and res.json()["role"] == "recruiter"
    assert client.post("/auth/users", json={"name": "Rae", "email": "rae@test.dev", "password": "longpassword"}).status_code == 409
