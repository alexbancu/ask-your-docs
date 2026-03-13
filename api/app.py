"""FastAPI application factory with CORS and lifespan management."""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import load_config
from api.rag_service import CloudRAGService
from api.routes import router, set_rag_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Initialize RAG service on startup, cleanup on shutdown."""
    logger.info("Starting RAG service initialization...")
    config = load_config()
    service = CloudRAGService(config)
    set_rag_service(service)
    logger.info("RAG service ready")
    yield
    logger.info("Shutting down RAG service")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app instance.
    """
    application = FastAPI(
        title="Acme Corp Knowledge Base API",
        description="RAG-powered Q&A over Acme Corp internal documents",
        version="1.0.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin
            for origin in [
                "http://localhost:5173",
                "http://localhost:3000",
                os.getenv("FRONTEND_URL"),
            ]
            if origin
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(router)

    return application


app = create_app()
