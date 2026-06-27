"""
BlockForge AI – Configuration
"""

import os
import sys
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

# ── Global Path Injection ────────────────────────────────
# Ensure the backend directory is always in the path for AI models
backend_dir = str(Path(__file__).resolve().parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "BlockForge AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    # ── Paths ────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent
    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "/tmp/blockforge/uploads"))
    FRAMES_DIR: Path = Path(os.getenv("FRAMES_DIR", "/tmp/blockforge/frames"))
    OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "/tmp/blockforge/output"))
    MASKS_DIR: Path = Path(os.getenv("MASKS_DIR", "/tmp/blockforge/masks"))

    # ── Redis / Celery ───────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # ── GPU ──────────────────────────────────────────────
    GPU_DEVICE: str = "cuda:0"
    GPU_BATCH_SIZE: int = 4
    USE_FP16: bool = True
    MAX_GPU_MEMORY_GB: float = 8.0

    # ── Video defaults ───────────────────────────────────
    DEFAULT_CRF: int = 18
    DEFAULT_CODEC: str = "libx264"
    DEFAULT_PRESET: str = "slow"
    MAX_VIDEO_SIZE_MB: int = 500
    ALLOWED_EXTENSIONS: list[str] = ["mp4", "avi", "mov", "mkv", "webm"]

    # ── AI Models ────────────────────────────────────────
    SAM_CHECKPOINT: str = str(BASE_DIR / "ai_models/sam/sam_vit_h_4b8939.pth")
    SAM_MODEL_TYPE: str = "vit_h"
    LAMA_CHECKPOINT: str = str(BASE_DIR / "ai_models/lama/big-lama")
    REALESRGAN_MODEL: str = str(BASE_DIR / "ai_models/realesrgan/RealESRGAN_x4plus.pth")
    REALESRGAN_SCALE: int = 4
    YOLOV8_MODEL_PATH: str = "yolov8s.pt"  # Auto-downloaded on first use

    # ── CORS ─────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure directories exist
for d in [settings.UPLOAD_DIR, settings.FRAMES_DIR, settings.OUTPUT_DIR, settings.MASKS_DIR]:
    d.mkdir(parents=True, exist_ok=True)
