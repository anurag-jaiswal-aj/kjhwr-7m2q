from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import CORS_ORIGINS, DEFAULT_DB_PATH
from backend.app.db.database import init_db
from backend.app.api.endpoints import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database tables exist on startup
    init_db(DEFAULT_DB_PATH)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="UK Wind Generation Market Analytics API",
        version="1.0.0",
        description="REST API evaluating UK national wind generation forecasts and historical accuracy for January 2026.",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Environment-based CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
    )

    # Mount API router under /api
    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
