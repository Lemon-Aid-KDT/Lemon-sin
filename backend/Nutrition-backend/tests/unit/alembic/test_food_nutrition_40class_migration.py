"""Food nutrition 40-class migration data tests."""

from __future__ import annotations

from importlib import util
from pathlib import Path
from types import ModuleType

PROJECT_ROOT = Path(__file__).resolve().parents[5]
MIGRATION_PATH = (
    PROJECT_ROOT
    / "backend"
    / "alembic"
    / "versions"
    / "0045_upsert_food_nutrition_40class_v2.py"
)


def _load_migration() -> ModuleType:
    """Load the 0045 migration module by file path.

    Returns:
        Imported migration module.

    Raises:
        AssertionError: If the module cannot be loaded.
    """
    spec = util.spec_from_file_location("migration_0045", MIGRATION_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_food_nutrition_40class_migration_contains_reviewed_subset() -> None:
    """Verify the migration carries the reviewed 40-class manifest only."""
    migration = _load_migration()

    assert migration.MANIFEST_VERSION == "food-nutrition-40class-v2"
    assert len(migration.FOOD_NUTRITION_40CLASS_ROWS) == 40

    rows = {row[0]: row for row in migration.FOOD_NUTRITION_40CLASS_ROWS}
    assert rows["pizza"][9] == 550.0
    assert rows["fried-chicken"][10] == 88.0
    assert rows["fried-chicken"][11] == 3.0
    assert rows["korean-ramyeon-red"][6] is None
    assert rows["korean-ramyeon-red"][10] == 0.0


def test_food_nutrition_40class_migration_preserves_removed_class_policy() -> None:
    """Verify unsupported 59-class leftovers are not in the 40-class upsert list."""
    migration = _load_migration()

    class_names = {row[0] for row in migration.FOOD_NUTRITION_40CLASS_ROWS}
    assert "rice-bowl" not in class_names
    assert "dumplings" not in class_names
    assert "jjamppong" not in class_names
