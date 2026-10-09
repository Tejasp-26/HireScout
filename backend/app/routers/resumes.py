from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.db import get_db
from app.models import IngestionLog
from app.schemas import IngestionLogOut
from app.security import get_current_user
from app.services import drive_sync
from app.services.ingestion import ingest_resume

router = APIRouter(prefix="/resumes", tags=["resumes"], dependencies=[Depends(get_current_user)])


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload one PDF. The UI sends files one at a time to show progress."""
    content = await file.read(config.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    result = ingest_resume(db, content, file.filename or "resume.pdf", source="upload")
    return result.to_dict()


@router.get("/logs", response_model=list[IngestionLogOut])
def ingestion_logs(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    return db.scalars(select(IngestionLog).order_by(IngestionLog.id.desc()).limit(limit)).all()


@router.get("/drive-sync")
def drive_sync_status():
    return drive_sync.status()


@router.post("/drive-sync", status_code=202)
def start_drive_sync():
    if not drive_sync.configured():
        raise HTTPException(
            status_code=400,
            detail="Google Drive sync is not configured. Set GOOGLE_SERVICE_ACCOUNT_FILE and GOOGLE_DRIVE_FOLDER_ID.",
        )
    if not drive_sync.start():
        raise HTTPException(status_code=409, detail="A sync is already running")
    return drive_sync.status()
