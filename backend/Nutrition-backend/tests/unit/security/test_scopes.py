"""OAuth scope registry tests."""

from __future__ import annotations

from src.security.scopes import ALL_API_SCOPES, SCOPE_DESCRIPTIONS, ApiScope, scope_values


def test_scope_registry_values_are_unique_and_documented() -> None:
    """Verify every registered scope has one value and one description."""
    scope_values_from_enum = [scope.value for scope in ApiScope]

    assert len(scope_values_from_enum) == len(set(scope_values_from_enum))
    assert set(ALL_API_SCOPES) == set(scope_values_from_enum)
    assert set(SCOPE_DESCRIPTIONS) == set(ApiScope)


def test_p1_scope_registry_contains_supplement_health_and_dashboard_scopes() -> None:
    """Verify P1 contract scopes are centrally registered."""
    assert scope_values(
        ApiScope.SUPPLEMENT_READ,
        ApiScope.SUPPLEMENT_WRITE,
        ApiScope.SUPPLEMENT_DELETE,
        ApiScope.HEALTH_WRITE,
        ApiScope.REGULATED_INPUT_WRITE,
        ApiScope.DASHBOARD_READ,
    ) == (
        "supplement:read",
        "supplement:write",
        "supplement:delete",
        "health:write",
        "regulated_input:write",
        "dashboard:read",
    )
