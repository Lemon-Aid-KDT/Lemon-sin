"""Central OAuth scope registry for API authorization contracts."""

from __future__ import annotations

from enum import StrEnum


class ApiScope(StrEnum):
    """OAuth scopes accepted by protected API routes.

    Attributes:
        ANALYSIS_READ: Read persisted analysis results.
        ANALYSIS_WRITE: Create persisted analysis results.
        ANALYSIS_DELETE: Delete persisted analysis results.
        PRIVACY_READ: Read consent and deletion state.
        PRIVACY_WRITE: Grant or revoke consent.
        PRIVACY_DELETE: Request deletion of current-user data.
        SUPPLEMENT_READ: Read current-user supplement records.
        SUPPLEMENT_WRITE: Analyze and register current-user supplements.
        SUPPLEMENT_DELETE: Delete current-user supplement records.
        HEALTH_READ: Read current-user health summary data.
        HEALTH_WRITE: Sync current-user health device aggregate data.
        REGULATED_INPUT_WRITE: Create intake-only regulated document OCR previews.
        DASHBOARD_READ: Read current-user dashboard summaries.
    """

    ANALYSIS_READ = "analysis:read"
    ANALYSIS_WRITE = "analysis:write"
    ANALYSIS_DELETE = "analysis:delete"
    PRIVACY_READ = "privacy:read"
    PRIVACY_WRITE = "privacy:write"
    PRIVACY_DELETE = "privacy:delete"
    SUPPLEMENT_READ = "supplement:read"
    SUPPLEMENT_WRITE = "supplement:write"
    SUPPLEMENT_DELETE = "supplement:delete"
    HEALTH_READ = "health:read"
    HEALTH_WRITE = "health:write"
    REGULATED_INPUT_WRITE = "regulated_input:write"
    DASHBOARD_READ = "dashboard:read"


SCOPE_DESCRIPTIONS: dict[ApiScope, str] = {
    ApiScope.ANALYSIS_READ: "Read persisted analysis results.",
    ApiScope.ANALYSIS_WRITE: "Create persisted analysis results.",
    ApiScope.ANALYSIS_DELETE: "Delete persisted analysis results.",
    ApiScope.PRIVACY_READ: "Read consent and deletion state.",
    ApiScope.PRIVACY_WRITE: "Grant or revoke consent.",
    ApiScope.PRIVACY_DELETE: "Request deletion of current-user data.",
    ApiScope.SUPPLEMENT_READ: "Read current-user supplement records.",
    ApiScope.SUPPLEMENT_WRITE: "Analyze and register current-user supplements.",
    ApiScope.SUPPLEMENT_DELETE: "Delete current-user supplement records.",
    ApiScope.HEALTH_READ: "Read current-user health summary data.",
    ApiScope.HEALTH_WRITE: "Sync current-user health device aggregate data.",
    ApiScope.REGULATED_INPUT_WRITE: "Create intake-only regulated document OCR previews.",
    ApiScope.DASHBOARD_READ: "Read current-user dashboard summaries.",
}

ALL_API_SCOPES: tuple[str, ...] = tuple(scope.value for scope in ApiScope)


def scope_values(*scopes: ApiScope) -> tuple[str, ...]:
    """Return string values for registered API scopes.

    Args:
        scopes: Scope enum members.

    Returns:
        Tuple of OAuth scope strings.
    """
    return tuple(scope.value for scope in scopes)
