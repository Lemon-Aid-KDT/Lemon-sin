"""Regression guard: every owner route must sit on an RLS seam before the flip.

After the FORCE RLS Stage-2 flip ``DATABASE_URL`` connects as the non-superuser
``lemon_app`` role. A route on the plain ``get_async_session`` dependency sets no
per-request RLS GUCs and commits owner/audit writes in-session, so under the flip
it silently fails closed (owner reads return 0 rows; ``audit_logs`` INSERT is
denied → 500). Owner routes must therefore either:

* use ``get_rls_context_session`` (dependency opens the request tx + sets GUCs), or
* keep ``get_async_session`` **and** wrap their body in
  ``rls_request_transaction`` / ``rls_request_transaction_allow_inner_commit``
  (needed only when the route schedules post-commit BackgroundTasks or calls a
  DO-NOT-TOUCH callee that commits + refreshes mid-request).

This test fails if any *new* route adopts ``get_async_session`` without being
added to the in-body-CM allowlist below — catching the exact class of bug that
left four supplement CRUD routes unmigrated until the live flip exposed them.
"""

from __future__ import annotations

from fastapi.dependencies.utils import get_flat_dependant
from fastapi.routing import APIRoute
from src.db.dependencies import get_async_session
from src.main import create_app

# Routes that intentionally keep ``get_async_session`` because they own their RLS
# transaction *in the route body* (rls_request_transaction /
# rls_request_transaction_allow_inner_commit). Adding a route here is a conscious
# assertion that its body is CM-wrapped. Anything else on get_async_session is a bug.
_IN_BODY_RLS_CM_ROUTES: frozenset[str] = frozenset(
    {
        "run_chatbot",  # rls_request_transaction_allow_inner_commit (store inner commit+refresh)
        "analyze_supplement_label",  # rls_request_transaction (+ post-commit learning task)
        "upload_supplement_analysis_session_image",  # rls_request_transaction
        "analyze_supplement_label_multi",  # rls_request_transaction
        "create_user_supplement",  # rls_request_transaction (+ post-commit learning task)
    }
)


def _routes_using_get_async_session() -> list[str]:
    """Return ``"NAME (METHODS PATH)"`` for every route depending on get_async_session."""
    app = create_app()
    offenders: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        flat = get_flat_dependant(route.dependant)
        if any(dep.call is get_async_session for dep in flat.dependencies):
            methods = ",".join(sorted(route.methods or set()))
            offenders.append(f"{route.endpoint.__name__} ({methods} {route.path})")
    return offenders


def test_no_route_uses_get_async_session_outside_the_cm_wrapped_allowlist() -> None:
    """Any get_async_session route not in the in-body-CM allowlist is flip-unsafe."""
    using = _routes_using_get_async_session()
    offenders = sorted(
        entry for entry in using if entry.split(" ", 1)[0] not in _IN_BODY_RLS_CM_ROUTES
    )
    assert not offenders, (
        "These routes depend on get_async_session but are not in the in-body-RLS-CM "
        "allowlist; under the lemon_app FORCE-RLS flip their owner reads return 0 rows "
        "and in-session audit/owner writes fail closed. Migrate to "
        "get_rls_context_session, or wrap the body in rls_request_transaction* and add "
        "the route to _IN_BODY_RLS_CM_ROUTES: " + "; ".join(offenders)
    )


def test_cm_wrapped_allowlist_has_no_stale_entries() -> None:
    """Every allowlisted name must still be a live get_async_session route."""
    live = {entry.split(" ", 1)[0] for entry in _routes_using_get_async_session()}
    stale = sorted(_IN_BODY_RLS_CM_ROUTES - live)
    assert not stale, (
        "These allowlist entries no longer use get_async_session (route renamed, "
        "removed, or migrated to get_rls_context_session); drop them from "
        "_IN_BODY_RLS_CM_ROUTES: " + ", ".join(stale)
    )
