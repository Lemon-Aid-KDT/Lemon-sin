"""Check the local backend development environment without reading secrets.

This script is intentionally limited to reproducibility signals:

* required project files and directories
* Python version compatibility with ``backend/pyproject.toml``
* dev-tool declarations in ``backend/requirements-dev.txt``
* import availability for focused test/format/lint tools
* Git-tracked local artifacts such as ``.env`` or virtualenv directories

It does not open ``.env`` files, request headers, OCR artifacts, provider
payloads, or application settings.
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

REQUIRED_PATHS = (
    "backend/pyproject.toml",
    "backend/requirements.txt",
    "backend/requirements-dev.txt",
    "backend/Nutrition-backend/src",
    "backend/Nutrition-backend/tests",
    "docs/team-collaboration/LOCAL_SETUP.md",
)
DEV_REQUIREMENT_PACKAGES = ("black", "ruff", "mypy", "pytest", "pip-audit")
TOOL_MODULES = {
    "black": "black",
    "ruff": "ruff",
    "mypy": "mypy",
    "pytest": "pytest",
    "pip-audit": "pip_audit",
}
MINIMUM_PYTHON_PARTS = 2
FORBIDDEN_TRACKED_PATHS = (
    ".env",
    ".venv",
    "backend/.env",
    "backend/.venv",
    "mobile/.env",
    "mobile/.venv",
    "backend/Nutrition-backend/.coverage",
    "backend/Nutrition-backend/htmlcov",
    "backend/.pytest_cache",
)


@dataclass(frozen=True)
class DevEnvCheck:
    """One bounded backend development environment check.

    Attributes:
        name: Stable check name for CLI output.
        ok: Whether the check passed.
        detail: Bounded diagnostic that avoids secrets and local absolute paths.
    """

    name: str
    ok: bool
    detail: str


def run_checks(
    *,
    repo_root: Path,
    tool_modules: dict[str, str] | None = None,
    python_version: tuple[int, int, int] | None = None,
) -> tuple[DevEnvCheck, ...]:
    """Run backend development environment checks.

    Args:
        repo_root: Lemon Aid project root.
        tool_modules: Optional package-to-module mapping for test isolation.
        python_version: Optional Python version tuple for test isolation.

    Returns:
        Tuple of check results.
    """
    resolved_root = repo_root.resolve()
    tools = tool_modules if tool_modules is not None else TOOL_MODULES
    version = python_version if python_version is not None else sys.version_info[:3]

    checks = [
        _check_required_paths(resolved_root),
        _check_python_version(resolved_root, version),
        _check_requirements_dev(resolved_root),
        _check_tool_imports(tools),
        _check_tracked_local_artifacts(resolved_root),
    ]
    return tuple(checks)


def _check_required_paths(repo_root: Path) -> DevEnvCheck:
    """Check that documented backend setup paths exist.

    Args:
        repo_root: Lemon Aid project root.

    Returns:
        Check result with missing project-relative paths.
    """
    missing = [path for path in REQUIRED_PATHS if not (repo_root / path).exists()]
    if missing:
        return DevEnvCheck(
            name="required_paths",
            ok=False,
            detail="missing=" + ",".join(missing),
        )
    return DevEnvCheck(name="required_paths", ok=True, detail=f"count={len(REQUIRED_PATHS)}")


def _check_python_version(repo_root: Path, version: tuple[int, int, int]) -> DevEnvCheck:
    """Check the interpreter version against ``requires-python``.

    Args:
        repo_root: Lemon Aid project root.
        version: Python version tuple to check.

    Returns:
        Check result for the active interpreter version.
    """
    pyproject_path = repo_root / "backend/pyproject.toml"
    if not pyproject_path.exists():
        return DevEnvCheck(
            name="python_version",
            ok=False,
            detail="missing=backend/pyproject.toml",
        )

    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    requires_python = str(data.get("project", {}).get("requires-python", ""))
    minimum = _parse_minimum_python(requires_python)
    if minimum is None:
        return DevEnvCheck(
            name="python_version",
            ok=False,
            detail=f"unsupported_requires_python={requires_python}",
        )

    current = version[:2]
    ok = current >= minimum
    return DevEnvCheck(
        name="python_version",
        ok=ok,
        detail=(
            f"current={version[0]}.{version[1]}.{version[2]} "
            f"required=>={minimum[0]}.{minimum[1]}"
        ),
    )


def _parse_minimum_python(specifier: str) -> tuple[int, int] | None:
    """Parse the repo's simple minimum Python specifier.

    Args:
        specifier: ``requires-python`` value from ``pyproject.toml``.

    Returns:
        Minimum major/minor tuple, or ``None`` for unsupported specifiers.
    """
    if not specifier.startswith(">="):
        return None
    raw_version = specifier.removeprefix(">=").strip()
    parts = raw_version.split(".")
    if len(parts) < MINIMUM_PYTHON_PARTS:
        return None
    try:
        return (int(parts[0]), int(parts[1]))
    except ValueError:
        return None


def _check_requirements_dev(repo_root: Path) -> DevEnvCheck:
    """Check that dev requirements declare the standard backend tools.

    Args:
        repo_root: Lemon Aid project root.

    Returns:
        Check result for ``backend/requirements-dev.txt``.
    """
    requirements_path = repo_root / "backend/requirements-dev.txt"
    if not requirements_path.exists():
        return DevEnvCheck(
            name="requirements_dev",
            ok=False,
            detail="missing=backend/requirements-dev.txt",
        )

    lines = _normalized_requirement_lines(requirements_path)
    missing_packages = [
        package
        for package in DEV_REQUIREMENT_PACKAGES
        if not any(line == package or line.startswith(f"{package}>") for line in lines)
    ]
    has_runtime_include = "-r requirements.txt" in lines
    problems = []
    if not has_runtime_include:
        problems.append("missing=-r requirements.txt")
    if missing_packages:
        problems.append("missing_packages=" + ",".join(missing_packages))
    if problems:
        return DevEnvCheck(name="requirements_dev", ok=False, detail=" ".join(problems))
    return DevEnvCheck(
        name="requirements_dev",
        ok=True,
        detail=f"tool_packages={len(DEV_REQUIREMENT_PACKAGES)} runtime_include=true",
    )


def _normalized_requirement_lines(path: Path) -> tuple[str, ...]:
    """Return normalized non-comment requirement lines.

    Args:
        path: Requirements file path.

    Returns:
        Non-empty requirement lines with inline comments removed.
    """
    lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", maxsplit=1)[0].strip()
        if line:
            lines.append(line)
    return tuple(lines)


def _check_tool_imports(tool_modules: dict[str, str]) -> DevEnvCheck:
    """Check whether focused backend dev tools are importable.

    Args:
        tool_modules: Package-to-module mapping.

    Returns:
        Check result for tool import availability.
    """
    missing = [
        package
        for package, module_name in sorted(tool_modules.items())
        if importlib.util.find_spec(module_name) is None
    ]
    if missing:
        return DevEnvCheck(
            name="tool_imports",
            ok=False,
            detail="missing=" + ",".join(missing),
        )
    return DevEnvCheck(name="tool_imports", ok=True, detail=f"count={len(tool_modules)}")


def _check_tracked_local_artifacts(repo_root: Path) -> DevEnvCheck:
    """Check Git does not track local-only backend artifacts.

    Args:
        repo_root: Lemon Aid project root.

    Returns:
        Check result listing project-relative tracked local artifacts.
    """
    project_paths = _tracked_project_paths(repo_root)
    forbidden = tuple(
        path
        for path in project_paths
        if any(
            path == forbidden_path or path.startswith(f"{forbidden_path}/")
            for forbidden_path in FORBIDDEN_TRACKED_PATHS
        )
    )
    if forbidden:
        return DevEnvCheck(
            name="tracked_local_artifacts",
            ok=False,
            detail="tracked=" + ",".join(forbidden),
        )
    return DevEnvCheck(name="tracked_local_artifacts", ok=True, detail="tracked=0")


def _tracked_project_paths(repo_root: Path) -> tuple[str, ...]:
    """Return Git-tracked paths below the Lemon Aid project root.

    Args:
        repo_root: Lemon Aid project root.

    Returns:
        Project-relative tracked paths. Empty when Git is unavailable.
    """
    git_root = _git_root(repo_root)
    if git_root is None:
        return ()
    try:
        project_prefix = repo_root.resolve().relative_to(git_root)
    except ValueError:
        return ()

    result = subprocess.run(
        ("git", "-C", str(git_root), "ls-files"),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ()

    prefix = "" if not project_prefix.parts else project_prefix.as_posix().strip("/")
    tracked_paths: list[str] = []
    for raw_path in result.stdout.splitlines():
        if not raw_path:
            continue
        if prefix:
            if not raw_path.startswith(f"{prefix}/"):
                continue
            tracked_paths.append(raw_path.removeprefix(f"{prefix}/"))
        else:
            tracked_paths.append(raw_path)
    return tuple(tracked_paths)


def _git_root(repo_root: Path) -> Path | None:
    """Return the enclosing Git root if available.

    Args:
        repo_root: Lemon Aid project root.

    Returns:
        Git root path, or ``None`` outside a Git worktree.
    """
    result = subprocess.run(
        ("git", "-C", str(repo_root), "rev-parse", "--show-toplevel"),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def _print_checks(checks: tuple[DevEnvCheck, ...]) -> None:
    """Print check results without local absolute paths or secret values.

    Args:
        checks: Check results.
    """
    for check in checks:
        stream = sys.stdout if check.ok else sys.stderr
        status = "ok" if check.ok else "fail"
        print(f"{status} {check.name} {check.detail}", file=stream)


def main(argv: list[str] | None = None) -> int:
    """Run the backend development environment doctor.

    Args:
        argv: Optional CLI argument list.

    Returns:
        Process exit code. Zero means all checks passed.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Lemon Aid project root. Defaults to the current directory.",
    )
    args = parser.parse_args(argv)

    checks = run_checks(repo_root=args.repo_root)
    _print_checks(checks)
    if all(check.ok for check in checks):
        print(f"backend_dev_env_ok checks={len(checks)}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
