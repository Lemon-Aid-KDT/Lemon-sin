from pydantic import BaseModel, Field


class ProfileUpdate(BaseModel):
    age: int | None = Field(default=None, ge=0, le=150)
    gender: str | None = Field(default=None, pattern="^[MF]$")
    height_cm: float | None = Field(default=None, gt=0, le=300)
    weight_kg: float | None = Field(default=None, gt=0, le=500)
    chronic_diseases: list[str] | None = None
    medications: list[str] | None = None
    goals: list[str] | None = None


class ProfileResponse(BaseModel):
    user_id: int
    age: int | None
    gender: str | None
    height_cm: float | None
    weight_kg: float | None
    chronic_diseases: list[str]
    medications: list[str]
    goals: list[str]

    model_config = {"from_attributes": True}
