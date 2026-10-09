import hashlib
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

# Configure an isolated, offline environment before the app is imported.
_tmp = tempfile.mkdtemp(prefix="hirescout-test-")
os.environ.update(
    DATA_DIR=_tmp,
    DATABASE_URL=f"sqlite:///{_tmp}/test.db",
    SECRET_KEY="test-secret",
    GEMINI_API_KEY="",
    GOOGLE_SERVICE_ACCOUNT_FILE="",
    GOOGLE_DRIVE_FOLDER_ID="",
)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.vector_index import vector_index  # noqa: E402


def fake_encoder(texts: list[str]) -> np.ndarray:
    """Deterministic bag-of-words hashing embedder - no model download."""
    vectors = np.zeros((len(texts), 256), dtype=np.float32)
    for row, text in enumerate(texts):
        for word in text.lower().split():
            vectors[row, int(hashlib.md5(word.encode()).hexdigest(), 16) % 256] += 1.0
    return vectors + 1e-6


vector_index.encoder = fake_encoder


def make_pdf(lines: list[str]) -> bytes:
    """Build a minimal single-page PDF containing the given text lines."""

    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    stream = "BT /F1 11 Tf 50 780 Td 14 TL " + " ".join(f"({esc(l)}) Tj T*" for l in lines) + " ET"
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{obj}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.db import SessionLocal
    from app.main import app
    from app.models import User
    from app.security import hash_password

    with TestClient(app) as c:
        with SessionLocal() as db:
            db.add(User(name="Test Admin", email="admin@test.dev", password_hash=hash_password("password123"), role="admin"))
            db.commit()
        token = c.post("/auth/login", json={"email": "admin@test.dev", "password": "password123"}).json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c
