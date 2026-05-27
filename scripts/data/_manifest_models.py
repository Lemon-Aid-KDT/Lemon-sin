"""다운샘플 매니페스트 Pydantic v2 모델.

balanced_500 train 서브셋의 클래스별 선택 stem 목록을 직렬화/검증한다.

Reference:
    docs/superpowers/specs/2026-05-27-aihub-yolo-balanced500-yolo11s-design.md §3.3
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ClassManifest(BaseModel):
    """한 클래스의 다운샘플 선택 결과."""

    model_config = ConfigDict(frozen=True)

    class_id: int = Field(ge=0, le=49, description="YOLO class id (0~49)")
    class_name: str = Field(min_length=1, description="클래스 이름")
    stems: list[str] = Field(description="선택된 파일 stem (확장자 제외, 정렬됨)")

    @field_validator("stems")
    @classmethod
    def _normalize_stems(cls, value: list[str]) -> list[str]:
        """stems를 정렬된 리스트로 정규화한다 (입력 순서 무시)."""
        return sorted(value)


class TrainManifest(BaseModel):
    """전체 train 서브셋 매니페스트."""

    model_config = ConfigDict(frozen=True)

    seed: int = Field(description="다운샘플에 사용한 random seed")
    cap_per_class: int = Field(gt=0, description="클래스당 상한 (예: 500)")
    classes: list[ClassManifest] = Field(
        min_length=1,
        description="50개 클래스의 선택 결과 (최소 1개 이상, 최대 50개 권장)",
    )

    @model_validator(mode="after")
    def _unique_class_ids(self) -> TrainManifest:
        """class_id 중복을 거부한다."""
        ids = [c.class_id for c in self.classes]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate class_id in TrainManifest.classes")
        return self
