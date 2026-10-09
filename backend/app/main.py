import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.db import Base, SessionLocal, engine
from app.routers import analytics, assistant, auth, candidates, jobs, resumes
from app.services.vector_index import vector_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    config.RESUME_DIR.mkdir(parents=True, exist_ok=True)
    # Loads the saved index, or rebuilds it in a background thread.
    vector_index.load_or_rebuild(SessionLocal)
    yield


app = FastAPI(
    title=f"{config.APP_NAME} API",
    description="AI resume screening: parsing, semantic search and job matching.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (auth.router, candidates.router, resumes.router, jobs.router, assistant.router, analytics.router):
    app.include_router(router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "app": config.APP_NAME}
