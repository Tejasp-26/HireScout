"""Semantic search over candidates with FAISS + sentence-transformers.

Vectors are L2-normalised and stored in an inner-product index, so search
scores are cosine similarities. FAISS ids are the candidates' database ids,
which means the index never needs its own copy of candidate data and
deletes/updates are exact.
"""

import logging
import threading
from collections.abc import Callable

import faiss
import numpy as np
from sqlalchemy import select

from app import config
from app.models import Candidate

log = logging.getLogger(__name__)

Encoder = Callable[[list[str]], np.ndarray]

INDEX_FILE = "candidates.faiss"


def profile_text(candidate: Candidate) -> str:
    """The text we embed for a candidate - most informative parts first.

    MiniLM only reads the first ~256 tokens, so a structured profile beats
    embedding the raw resume (which often starts with contact details).
    """
    roles = "; ".join(
        f"{e.get('title', '')} at {e.get('company', '')}" for e in (candidate.experience or [])[:4]
    )
    parts = [
        candidate.current_title or "",
        "Skills: " + ", ".join(candidate.skills or []),
        candidate.summary or "",
        f"Experience: {roles}" if roles else "",
        (candidate.resume_text or "")[:1500],
    ]
    return "\n".join(p for p in parts if p)


class VectorIndex:
    def __init__(self, encoder: Encoder | None = None):
        self.encoder = encoder
        self._index: faiss.IndexIDMap2 | None = None
        self._lock = threading.RLock()
        self._rebuilding = False
        self._pending: dict[int, np.ndarray | None] = {}  # changes made during a rebuild

    # -- embedding -----------------------------------------------------------

    def _encode(self, texts: list[str]) -> np.ndarray:
        if self.encoder is None:
            with self._lock:
                if self.encoder is None:
                    from sentence_transformers import SentenceTransformer

                    log.info("Loading embedding model %s", config.EMBEDDING_MODEL)
                    model = SentenceTransformer(config.EMBEDDING_MODEL)
                    self.encoder = lambda batch: model.encode(
                        batch, normalize_embeddings=True, show_progress_bar=False
                    )
        vectors = np.asarray(self.encoder(texts), dtype=np.float32)
        faiss.normalize_L2(vectors)
        return vectors

    def _new_index(self, dim: int) -> faiss.IndexIDMap2:
        return faiss.IndexIDMap2(faiss.IndexFlatIP(dim))

    # -- status --------------------------------------------------------------

    @property
    def size(self) -> int:
        with self._lock:
            return self._index.ntotal if self._index is not None else 0

    @property
    def ready(self) -> bool:
        return not self._rebuilding

    # -- persistence ---------------------------------------------------------

    def _path(self):
        return config.INDEX_DIR / INDEX_FILE

    def _save(self) -> None:
        if self._index is None:
            return
        config.INDEX_DIR.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self._path()))

    def load_or_rebuild(self, session_factory) -> None:
        """Load the saved index, or rebuild it in the background if it is
        missing or out of sync with the database (so startup never blocks)."""
        with session_factory() as db:
            db_count = len(db.scalars(select(Candidate.id)).all())

        if self._path().exists():
            try:
                index = faiss.read_index(str(self._path()))
                if index.ntotal == db_count:
                    with self._lock:
                        self._index = index
                    log.info("Loaded vector index with %d candidates", db_count)
                    return
                log.info("Index has %d vectors but DB has %d candidates", index.ntotal, db_count)
            except Exception as exc:
                log.warning("Could not read vector index: %s", exc)

        self._rebuilding = True
        threading.Thread(target=self.rebuild, args=(session_factory,), daemon=True).start()

    def rebuild(self, session_factory) -> None:
        self._rebuilding = True
        try:
            with session_factory() as db:
                candidates = db.scalars(select(Candidate)).all()
                rows = [(c.id, profile_text(c)) for c in candidates]

            index = None
            for start in range(0, len(rows), 64):
                batch = rows[start:start + 64]
                vectors = self._encode([text for _, text in batch])
                if index is None:
                    index = self._new_index(vectors.shape[1])
                index.add_with_ids(vectors, np.array([cid for cid, _ in batch], dtype=np.int64))

            with self._lock:
                self._index = index
                # Replay uploads/deletes that happened while we were embedding.
                for cid, vector in self._pending.items():
                    self._apply(cid, vector)
                self._pending.clear()
                self._rebuilding = False
                self._save()
            log.info("Rebuilt vector index with %d candidates", self.size)
        except Exception:
            log.exception("Vector index rebuild failed")
        finally:
            self._rebuilding = False

    # -- mutations -----------------------------------------------------------

    def _apply(self, candidate_id: int, vector: np.ndarray | None) -> None:
        ids = np.array([candidate_id], dtype=np.int64)
        if self._index is not None:
            self._index.remove_ids(ids)
        if vector is not None:
            if self._index is None:
                self._index = self._new_index(vector.shape[1])
            self._index.add_with_ids(vector, ids)

    def upsert(self, candidate: Candidate) -> None:
        vector = self._encode([profile_text(candidate)])
        with self._lock:
            if self._rebuilding:
                self._pending[candidate.id] = vector
            self._apply(candidate.id, vector)
            self._save()

    def remove(self, candidate_id: int) -> None:
        with self._lock:
            if self._rebuilding:
                self._pending[candidate_id] = None
            self._apply(candidate_id, None)
            self._save()

    # -- queries -------------------------------------------------------------

    def search(self, text: str, k: int = 10) -> list[tuple[int, float]]:
        """Return [(candidate_id, cosine_similarity)], best first."""
        if self.size == 0 or not text.strip():
            return []
        vector = self._encode([text])
        with self._lock:
            k = min(k, self._index.ntotal)
            scores, ids = self._index.search(vector, k)
        return [(int(i), float(s)) for i, s in zip(ids[0], scores[0]) if i != -1]


vector_index = VectorIndex()
