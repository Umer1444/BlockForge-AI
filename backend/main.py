"""
BlockForge AI – FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from api.upload import router as upload_router
from api.process import router as process_router
from api.status import router as status_router
from api.websocket import router as ws_router

import logging

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
)
logger = logging.getLogger("blockforge")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/docs")

    # ── CORS ─────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Static files (processed output & input previews) ──
    app.mount(
        "/output",
        StaticFiles(directory=str(settings.OUTPUT_DIR)),
        name="output",
    )
    app.mount(
        "/uploads",
        StaticFiles(directory=str(settings.UPLOAD_DIR)),
        name="uploads",
    )

    # ── Routers ──────────────────────────────────────
    app.include_router(upload_router, prefix="/api", tags=["Upload"])
    app.include_router(process_router, prefix="/api", tags=["Process"])
    app.include_router(status_router, prefix="/api", tags=["Status"])
    app.include_router(ws_router, tags=["WebSocket"])

    # ── Health check ─────────────────────────────────
    @app.get("/health", tags=["System"])
    async def health_check():
        import torch

        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "gpu_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        }

    logger.info(f"⛏  {settings.APP_NAME} v{settings.APP_VERSION} ready")
    return app


app = create_app()
