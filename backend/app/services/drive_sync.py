"""Google Drive folder sync using a service account.

A service account (instead of a user OAuth token) never expires and needs
no browser login, so it works unattended on a server. Share the Drive
folder with the service account's email address (Viewer is enough).

Sync runs in a background thread; the UI polls `status()` for progress.
"""

import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app import config
from app.db import SessionLocal
from app.models import Candidate, IngestionLog
from app.services.ingestion import ingest_resume

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

_lock = threading.Lock()
_state: dict = {
    "running": False,
    "total": 0,
    "processed": 0,
    "added": 0,
    "duplicates": 0,
    "failed": 0,
    "started_at": None,
    "finished_at": None,
    "error": None,
}


def configured() -> bool:
    return bool(
        config.GOOGLE_DRIVE_FOLDER_ID
        and config.GOOGLE_SERVICE_ACCOUNT_FILE
        and Path(config.GOOGLE_SERVICE_ACCOUNT_FILE).is_file()
    )


def status() -> dict:
    with _lock:
        return {"configured": configured(), **_state}


def _drive_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(
        config.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _list_pdfs(service) -> list[dict]:
    query = (
        f"'{config.GOOGLE_DRIVE_FOLDER_ID}' in parents "
        "and mimeType='application/pdf' and trashed=false"
    )
    files, page_token = [], None
    while True:
        response = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name)",
                pageSize=200,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            return files


def start() -> bool:
    """Start a sync in the background. Returns False if one is running."""
    with _lock:
        if _state["running"]:
            return False
        _state.update(
            running=True, total=0, processed=0, added=0, duplicates=0, failed=0,
            started_at=datetime.now(timezone.utc).isoformat(), finished_at=None, error=None,
        )
    threading.Thread(target=_run, daemon=True).start()
    return True


def _bump(**counts) -> None:
    with _lock:
        for key, value in counts.items():
            _state[key] += value


def _run() -> None:
    db = SessionLocal()
    try:
        service = _drive_service()
        files = _list_pdfs(service)
        with _lock:
            _state["total"] = len(files)

        for file in files:
            already = db.scalar(select(Candidate).where(Candidate.source_ref == file["id"]))
            if already:
                # Skip without downloading; quiet so re-syncs don't flood the log.
                _bump(processed=1, duplicates=1)
                continue

            try:
                content = service.files().get_media(
                    fileId=file["id"], supportsAllDrives=True
                ).execute()
            except Exception as exc:
                db.add(IngestionLog(source="drive", filename=file["name"], status="failed",
                                    detail=f"Download failed: {exc}"))
                db.commit()
                _bump(processed=1, failed=1)
                continue

            result = ingest_resume(db, content, file["name"], source="drive", source_ref=file["id"])
            key = {"added": "added", "duplicate": "duplicates"}.get(result.status, "failed")
            _bump(processed=1, **{key: 1})
    except Exception as exc:
        log.exception("Drive sync failed")
        with _lock:
            _state["error"] = str(exc)
    finally:
        db.close()
        with _lock:
            _state["running"] = False
            _state["finished_at"] = datetime.now(timezone.utc).isoformat()
