from fastapi import APIRouter

from src.api.auth import router as auth_router
from src.api.email_verification import router as email_verification_router
from src.api.profile import router as profile_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(email_verification_router)
api_router.include_router(profile_router)
