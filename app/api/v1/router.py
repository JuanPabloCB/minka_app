# app/api/v1/router.py
from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.sessions import router as sessions_router
from app.api.v1.orchestrator import router as orchestrator_router
from app.api.v1.plans import router as plans_router
from app.api.v1.legal_analyst import router as legal_analyst_router

router = APIRouter()
router.include_router(health_router)
router.include_router(sessions_router)
router.include_router(orchestrator_router)
router.include_router(plans_router)
router.include_router(legal_analyst_router)