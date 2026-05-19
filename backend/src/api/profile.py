from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.models.profile import Profile
from src.models.user import User
from src.schemas.profile import ProfileResponse, ProfileUpdate
from src.utils.deps import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.scalar(select(Profile).where(Profile.user_id == current_user.id))
    if not profile:
        profile = Profile(
            user_id=current_user.id,
            chronic_diseases=[],
            medications=[],
            goals=[],
        )
        db.add(profile)
        await db.flush()
    return profile


@router.put("", response_model=ProfileResponse)
async def update_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.scalar(select(Profile).where(Profile.user_id == current_user.id))
    if not profile:
        profile = Profile(user_id=current_user.id, chronic_diseases=[], medications=[], goals=[])
        db.add(profile)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(profile, field, value)

    await db.flush()
    return profile
