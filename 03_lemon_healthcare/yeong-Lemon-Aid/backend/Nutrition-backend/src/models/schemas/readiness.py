"""Readiness response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReadinessComponentStatus = Literal["ready", "not_configured", "not_ready", "blocked"]
ReadinessOverallStatus = Literal["ready", "degraded", "not_ready"]


class ReadinessComponent(BaseModel):
    """One sanitized readiness component.

    Attributes:
        name: Component name.
        status: Sanitized component status.
        message_code: Stable safe message code.
        details: Safe non-secret details.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=80)
    status: ReadinessComponentStatus
    message_code: str = Field(min_length=1, max_length=120)
    details: dict[str, str | bool | int | float | None] = Field(default_factory=dict)


class ReadinessResponse(BaseModel):
    """Provider and release readiness response.

    Attributes:
        status: Overall readiness status.
        environment: Runtime environment.
        deployment_exposure: Whether deployment is local, private, or public.
        components: Sanitized component status list.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: ReadinessOverallStatus
    environment: str = Field(min_length=1, max_length=40)
    deployment_exposure: str = Field(min_length=1, max_length=40)
    components: list[ReadinessComponent] = Field(default_factory=list, max_length=40)
