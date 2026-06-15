"""Upsert teammate-reviewed 40-class food nutrition values.

Revision ID: 0045_upsert_food_nutrition_40class_v2
Revises: 0044_normalize_check_constraint_names
Create Date: 2026-06-14 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0045_upsert_food_nutrition_40class_v2"
down_revision: str | Sequence[str] | None = "0044_normalize_check_constraint_names"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE = "aihub_taxo59_csv"
MANIFEST_VERSION = "food-nutrition-40class-v2"
PREVIOUS_MANIFEST_VERSION = "food-nutrition-taxo59-v1"

# Team deliverable: docs/deliverables/nutrition-40class/food_nutrition_40class.csv
# Values are class-average estimates on a 100g basis. They are not medical facts
# and must remain advisory until the user confirms actual food/portion data.
FOOD_NUTRITION_40CLASS_ROWS: tuple[tuple, ...] = (
    ("barbecue-ribs", "갈비", 7, 266.0, 188.96, 10.29, 3.54, 11.99, 10.81, 560.34, 43.6, 2.52, 0.03),
    ("black-bean-noodles", "짜장면", 3, 483.0, 111.72, 17.02, 5.92, 1.95, 6.14, 236.19, 8.68, 0.33, 0.03),
    ("braised-chicken", "찜닭", 3, 314.0, 126.63, 7.16, 0.78, 6.56, 9.68, 193.47, 30.0, 1.3, 0.0),
    ("braised-pork-hock", "족발", 3, 310.0, 194.99, 11.34, 6.85, 8.55, 16.5, 497.51, 57.55, 2.35, 0.0),
    ("bread", "빵", 45, 150.0, 274.41, 37.4, 9.14, 10.77, 7.34, 238.68, 57.54, 3.48, 0.37),
    ("bulgogi", "불고기", 3, 237.0, 144.91, 6.97, 2.27, 8.43, 10.12, 224.22, 27.08, 2.79, 0.0),
    ("cake", "케이크", 8, 182.0, 321.6, 35.09, 13.84, 18.06, 4.64, 146.36, 69.69, 3.71, 0.12),
    ("cold-noodles", "냉면", 4, 328.0, 166.23, 28.53, 1.85, 2.13, 7.8, 472.95, 31.89, 0.53, 0.02),
    ("curry", "카레", 8, 308.0, 153.67, 12.16, 1.74, 9.24, 5.9, 529.23, 30.36, 3.07, 0.41),
    ("dim-sum", "딤섬(찐만두)", 2, 272.0, 364.27, 34.71, 4.29, 19.3, 10.55, 149.78, 17.38, 7.5, 0.07),
    ("doenjang-jjigae", "된장찌개", 2, 300.0, 103.87, 4.48, 0.57, 6.75, 6.35, 378.21, 20.1, 2.01, 0.11),
    ("fish-cake", "어묵", 2, 110.0, 191.01, 16.52, 1.51, 7.81, 12.91, 401.07, 53.03, 0.57, 1.69),
    ("fried-chicken", "후라이드치킨", 43, 217.0, 236.26, 21.37, 4.98, 11.69, 11.37, 355.92, 88.0, 3.0, 0.83),
    ("fried-food-platter", "튀김(모둠)", 3, 124.0, 231.65, 18.34, 0.6, 11.86, 12.18, 486.79, 45.49, 2.0, 1.15),
    ("grilled-fish", "생선구이", 7, 74.0, 191.08, 0.46, None, 10.66, 21.69, 400.21, 61.25, 9.47, 0.68),
    ("grilled-pork-belly", "삼겹살", 1, 205.0, 220.4, 3.14, None, 18.2, 10.81, 159.28, 32.15, 9.28, 0.0),
    ("hamburger", "햄버거", 5, 227.0, 179.43, 16.68, 0.87, 7.15, 12.01, 293.58, 21.27, 4.0, 0.35),
    ("japanese-ramen", "일본라멘", 5, 496.0, 114.82, 13.52, 0.77, 4.51, 4.51, 400.73, 110.56, 1.61, 0.02),
    ("jjigae-red", "빨간찌개", 4, 371.0, 75.39, 4.1, 1.32, 3.92, 6.14, 452.91, 26.57, 0.44, 0.0),
    ("kalguksu", "칼국수", 5, 512.0, 95.03, 17.27, 1.64, 0.55, 4.29, 319.28, 2.54, 0.07, 0.0),
    ("korean-blood-sausage", "순대", 3, 206.0, 151.63, 13.05, 0.01, 6.47, 9.68, 476.18, 95.94, 2.04, 0.0),
    ("korean-ramyeon-red", "라면", 3, 519.0, 144.39, 19.87, None, 4.69, 5.41, 382.55, 0.0, 1.09, 0.03),
    ("mixed-rice-bowl", "비빔밥", 5, 362.0, 171.98, 28.75, 1.32, 3.65, 5.82, 236.23, 28.16, 0.47, 0.11),
    ("pasta", "파스타", 18, 359.0, 245.87, 27.11, 0.98, 12.03, 7.24, 366.43, 28.99, 1.5, 0.02),
    ("pizza", "피자", 29, 193.0, 199.4, 26.51, 2.46, 6.27, 7.71, 550.0, 13.61, 1.58, 0.08),
    ("pork-cutlet-dry", "돈가스", 6, 194.0, 241.61, 24.75, 7.7, 9.64, 12.69, 204.08, 65.13, 4.5, 0.87),
    ("raw-fish", "회", 7, 236.0, 114.61, 10.22, 2.17, 2.52, 12.11, 258.22, 13.37, 0.3, 0.01),
    ("rice-noodle-soup", "쌀국수", 11, 594.0, 97.96, 15.58, 0.19, 2.25, 3.53, 278.83, 13.0, 0.44, 0.02),
    ("rice-porridge", "죽", 8, 205.0, 227.06, 28.74, 15.85, 10.53, 4.79, 278.4, 32.43, 3.77, 0.25),
    ("rice-soup", "국밥", 3, 517.0, 91.34, 17.51, None, 0.71, 3.55, 192.17, 3.45, 0.06, 0.01),
    ("salad", "샐러드", 11, 134.0, 129.18, 10.64, 1.78, 7.52, 5.57, 128.31, 21.84, 1.17, 0.03),
    ("sandwich", "샌드위치", 26, 195.0, 242.8, 22.36, 1.77, 13.77, 8.34, 445.3, 53.57, 4.47, 0.21),
    ("savory-pancake", "전/부침개", 3, 217.0, 171.05, 23.73, None, 4.55, 8.15, 318.42, 10.99, 0.27, 0.78),
    ("seaweed-rice-roll", "김밥", 10, 205.0, 232.96, 37.97, 1.75, 5.11, 7.51, 372.18, 46.19, 0.51, 0.3),
    ("spicy-mixed-noodles", "비빔국수", 2, 175.0, 230.02, 47.3, 3.88, 0.77, 6.54, 448.53, 0.54, 0.08, 0.0),
    ("sushi", "초밥", 9, 221.0, 248.86, 36.9, 3.29, 3.55, 15.17, 536.98, 111.78, 0.69, 0.02),
    ("takoyaki", "타코야키", 1, 206.0, 161.46, 15.56, 1.65, 8.26, 5.23, 120.11, 36.6, 0.49, 0.77),
    ("tteokbokki-red", "떡볶이", 6, 280.0, 199.53, 33.73, 3.77, 4.42, 6.17, 458.77, 7.84, 1.06, 0.05),
    ("udon", "우동", 4, 468.0, 92.39, 10.01, None, 4.27, 2.51, 233.21, 9.31, 0.34, 0.01),
    ("western-cream-soup", "양식수프", 5, 274.0, 139.17, 16.24, 0.36, 5.84, 5.05, 527.14, 14.95, 1.38, 0.07),
)


def _food_nutrition_table() -> sa.TableClause:
    """Return the lightweight table object used by this migration."""
    return sa.table(
        "food_nutrition",
        sa.column("class_en", sa.String),
        sa.column("class_ko", sa.String),
        sa.column("n_source_codes", sa.SmallInteger),
        sa.column("serving_g", sa.Numeric),
        sa.column("kcal_100g", sa.Numeric),
        sa.column("carb_g", sa.Numeric),
        sa.column("sugar_g", sa.Numeric),
        sa.column("fat_g", sa.Numeric),
        sa.column("protein_g", sa.Numeric),
        sa.column("sodium_mg", sa.Numeric),
        sa.column("chol_mg", sa.Numeric),
        sa.column("sat_fat_g", sa.Numeric),
        sa.column("trans_fat_g", sa.Numeric),
        sa.column("source", sa.String),
        sa.column("source_manifest_version", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )


def upgrade() -> None:
    """Upsert the reviewed 40-class nutrition subset without removing other classes."""
    columns = (
        "class_en",
        "class_ko",
        "n_source_codes",
        "serving_g",
        "kcal_100g",
        "carb_g",
        "sugar_g",
        "fat_g",
        "protein_g",
        "sodium_mg",
        "chol_mg",
        "sat_fat_g",
        "trans_fat_g",
    )
    food_nutrition = _food_nutrition_table()
    rows = [
        {
            **dict(zip(columns, row, strict=True)),
            "source": SOURCE,
            "source_manifest_version": MANIFEST_VERSION,
            "is_active": True,
        }
        for row in FOOD_NUTRITION_40CLASS_ROWS
    ]
    stmt = postgresql.insert(food_nutrition).values(rows)
    op.execute(
        stmt.on_conflict_do_update(
            index_elements=["class_en"],
            set_={
                "class_ko": stmt.excluded.class_ko,
                "n_source_codes": stmt.excluded.n_source_codes,
                "serving_g": stmt.excluded.serving_g,
                "kcal_100g": stmt.excluded.kcal_100g,
                "carb_g": stmt.excluded.carb_g,
                "sugar_g": stmt.excluded.sugar_g,
                "fat_g": stmt.excluded.fat_g,
                "protein_g": stmt.excluded.protein_g,
                "sodium_mg": stmt.excluded.sodium_mg,
                "chol_mg": stmt.excluded.chol_mg,
                "sat_fat_g": stmt.excluded.sat_fat_g,
                "trans_fat_g": stmt.excluded.trans_fat_g,
                "source": stmt.excluded.source,
                "source_manifest_version": stmt.excluded.source_manifest_version,
                "is_active": stmt.excluded.is_active,
                "updated_at": sa.func.now(),
            },
        )
    )

    op.execute(
        """
        UPDATE public.food_nutrition fn
           SET food_catalog_item_id = fci.id,
               updated_at = now()
          FROM public.food_catalog_items fci
         WHERE fn.source_manifest_version = 'food-nutrition-40class-v2'
           AND fci.aliases @> jsonb_build_array(fn.class_en)
        """
    )


def downgrade() -> None:
    """Restore the manifest tag without deleting shared food_nutrition rows."""
    food_nutrition = _food_nutrition_table()
    op.execute(
        sa.update(food_nutrition)
        .where(food_nutrition.c.source_manifest_version == MANIFEST_VERSION)
        .values(source_manifest_version=PREVIOUS_MANIFEST_VERSION, updated_at=sa.func.now())
    )
