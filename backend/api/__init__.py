from fastapi import APIRouter

from .status import router as status_router
from .ws import router as ws_router
from .process import router as process_router
from .upload import router as upload_router

api_router = APIRouter()

# Register routers
api_router.include_router(status_router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(ws_router, prefix="/stream", tags=["WebSocket"])
api_router.include_router(process_router, prefix="/process", tags=["Processing"])
api_router.include_router(upload_router, prefix="/upload", tags=["Upload"])
