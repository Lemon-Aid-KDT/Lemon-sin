# -*- coding: utf-8 -*-
r"""
nutrition_map_aihub.json 영양 정보 → 식약처(MFDS) 19,495건 DB 로 보강

기존 nutrition_map_aihub.json: AI Hub 영양DB.xlsx (400 항목, 기본 영양)
MFDS DB: 19,495 음식, 160 컬럼 (비타민·미네랄·식이섬유·지방세부 등 풍부)

매칭 방법:
  1. AI Hub 코드 (8자리) → 식품대분류코드 (앞 2자리) 비교
  2. 식품명 SequenceMatcher 유사도 (대분류 같은 것들 중)
  3. top 1 매칭 → MFDS 영양 컬럼 추가

추가되는 필드:
  fiber_g, calcium_mg, iron_mg, potassium_mg,
  cholesterol_mg, saturated_fat_g, trans_fat_g,
  vitamin_a_ug, vitamin_c_mg, vitamin_d_ug, vitamin_e_mg,
  vitamin_k_ug, vitamin_b6_mg, vitamin_b12_ug,
  omega3_g, omega6_g

실행:
  python enrich_nutrition_with_mfds.py
  python enrich_nutrition_with_mfds.py --mfds mfds_food_db_19495.xlsx --in nutrition_map_aihub.json --out nutrition_map_enriched.json
"""

import argparse
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import openpyxl
except ImportError:
    print("[ERROR] pip install openpyxl"); sys.exit(1)


# MFDS xlsx 컬럼 인덱스 (확인된 매핑)
MFDS_COLS = {
    "code": 0, "name": 1,
    "category_2digit_code": 6,    # 식품대분류코드 (01, 02, ...)
    "category_2digit_name": 7,
    "ref_weight_g": 16,            # 영양성분함량기준량
    "kcal": 17,
    "water_g": 18, "protein_g": 19, "fat_g": 20,
    "carb_g": 22, "sugar_g": 23, "fiber_g": 24,
    "calcium_mg": 25, "iron_mg": 26, "phosphorus_mg": 27,
    "potassium_mg": 28, "sodium_mg": 29,
    "vitamin_a_ug": 30,
    "vitamin_c_mg": 36, "vitamin_d_ug": 37,
    "cholesterol_mg": 38, "saturated_fat_g": 39, "trans_fat_g": 40,
    "vitamin_b6_mg": 44, "vitamin_b12_ug": 45,
    "vitamin_e_mg": 51, "vitamin_k_ug": 60,
    "omega3_g": 99, "omega6_g": 100,
}


def load_mfds(xlsx_path):
    """MFDS xlsx → [(name, category2, {nutrition fields}), ...]"""
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb.active
    items = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[MFDS_COLS["name"]]:
            continue
        name = str(row[MFDS_COLS["name"]]).strip()
        cat2 = str(row[MFDS_COLS["category_2digit_code"]] or "").strip()
        # 영양 필드
        nutr = {}
        for k, idx in MFDS_COLS.items():
            if k in ("code", "name", "category_2digit_code",
                     "category_2digit_name"):
                continue
            try:
                v = row[idx]
                if isinstance(v, (int, float)):
                    nutr[k] = round(float(v), 3)
            except (IndexError, TypeError):
                pass
        items.append((name, cat2, nutr))
    return items


def normalize_name(name):
    """공백·언더스코어·특수문자 제거 정규화.
    예: '김치_찌개', '김치 찌개', '(김치)찌개' → 모두 '김치찌개'"""
    if not name:
        return ""
    s = str(name).strip()
    for c in [" ", "_", "-", ".", "·", "/", "(", ")", "[", "]", ",", "(", ")"]:
        s = s.replace(c, "")
    return s


def sorted_chars(name):
    """문자 정렬 - 순서 다른 경우(찌개_김치 vs 김치찌개) 비교용."""
    return "".join(sorted(normalize_name(name)))


def best_mfds_match(target_name, target_cat2, mfds_items):
    """정규화 + 정렬 비교까지 포함된 robust 매칭."""
    target_norm = normalize_name(target_name)
    target_sorted = sorted_chars(target_name)
    best = (None, 0.0)
    for name, cat2, nutr in mfds_items:
        # 1. 원본 정확 일치
        if target_name == name:
            return ((name, nutr), 1.0)
        # 2. 정규화 정확 일치 (공백/언더스코어만 다른 경우)
        if target_norm == normalize_name(name):
            return ((name, nutr), 0.98)
        # 3. 정렬 후 정확 일치 (어순만 다른 경우 — "찌개_김치" vs "김치찌개")
        if target_sorted == sorted_chars(name) and len(target_norm) >= 4:
            s = 0.90
            if s > best[1]:
                best = ((name, nutr), s)
            continue
        # 4. 정규화 후 substring (target 이 name 의 일부)
        n_norm = normalize_name(name)
        if target_norm in n_norm and len(target_norm) >= 3:
            s = 0.85 - 0.001 * (len(n_norm) - len(target_norm))
            if s > best[1]:
                best = ((name, nutr), s)
            continue
        # 5. SequenceMatcher (정규화 후)
        s = SequenceMatcher(None, target_norm, n_norm).ratio()
        if s > best[1]:
            best = ((name, nutr), s)
    return best


def find_variants(target_name, mfds_items, max_variants=50):
    """target_name 의 모든 변형 찾기.
    구조: 정확일치(=기본) + '_' 로 시작하는 변형 + 포함된 다른 형태.

    예: target="김치찌개" → [
        {label:"기본", name:"김치찌개", ...},
        {label:"꽁치", name:"김치찌개_꽁치", ...},
        {label:"돼지고기", name:"김치찌개_돼지고기", ...},
        ...
    ]
    """
    variants = []
    seen_names = set()
    target_norm = normalize_name(target_name)

    for name, cat2, nutr in mfds_items:
        if name in seen_names:
            continue
        n_norm = normalize_name(name)
        label = None

        # 1. 정규화 정확일치 = 기본 ("김치_찌개" 등도 포함)
        if n_norm == target_norm:
            label = "기본"

        # 2. STRICT prefix + 명시적 구분자 (가장 안전한 변형 패턴)
        #    "{target}_X" or "{target} X" or "{target}/X" 형태
        elif (name.startswith(target_name + "_") or
              name.startswith(target_name + " ") or
              name.startswith(target_name + "/") or
              name.startswith(target_name + "(") or
              name.startswith(target_name + "-")):
            rest = name[len(target_name):].lstrip(" _-·/()")
            label = rest if rest else None

        # 3. 정규화된 prefix + 구분자 없이 직접 이어진 짧은 부분 (보수적)
        #    예: "비빔밥" → "비빔밥덮밥" 같은 경우는 다른 음식이므로 제외
        #    단, "{target}류" 같은 단일 글자 suffix 는 허용
        elif (n_norm.startswith(target_norm) and
              len(n_norm) - len(target_norm) <= 2 and
              len(target_norm) >= 3):
            rest = name[len(target_name):].lstrip(" _-·")
            label = rest if rest else None

        # 4. 어순/접미사/substring 매칭은 false positive 가 많아서 제외
        #    이런 케이스는 별도 음식으로 취급해서 새 클래스 후보로 둠

        if label is not None:
            variants.append({
                "label": label,
                "name": name,
                **nutr,
            })
            seen_names.add(name)
            if len(variants) >= max_variants:
                break

    # ----- 정책 -----
    # "X{target}" 패턴 (소불고기/오리불고기 등) 은 별개 음식으로 취급, 변형 아님.
    # 분류기가 "불고기" 출력했을 때 변형 0개면 → MFDS best_match (소불고기 등) 영양
    # 사용된 단일 영양값으로 처리. 사용자는 명확한 라벨이 필요하면 분류기 정확도 ↑
    # 또는 더 세분화된 클래스 학습으로 해결.

    # 기본 (정확일치) 을 첫 번째로 정렬
    variants.sort(key=lambda x: 0 if x["label"] == "기본" else 1)
    return variants


def main():
    ap = argparse.ArgumentParser()
    proj = Path(__file__).parent
    ap.add_argument("--mfds", default=str(proj / "mfds_food_db_19495.xlsx"))
    ap.add_argument("--in", dest="inp",
                    default=str(proj / "nutrition_map_aihub.json"))
    ap.add_argument("--out",
                    default=str(proj / "nutrition_map_enriched.json"))
    ap.add_argument("--threshold", type=float, default=0.6,
                    help="매칭 점수 임계값 (이하는 미매칭으로 처리)")
    args = ap.parse_args()

    for p in (args.mfds, args.inp):
        if not Path(p).exists():
            print(f"[ERROR] 없음: {p}"); sys.exit(1)

    print(f"=== MFDS DB 로드 ===")
    mfds_items = load_mfds(args.mfds)
    print(f"  {len(mfds_items):,} 음식 로드")
    cats = sorted(set(it[1] for it in mfds_items))
    print(f"  식품대분류 코드: {cats}")

    print(f"\n=== nutrition_map_aihub.json 로드 ===")
    nut_map = json.loads(Path(args.inp).read_text(encoding="utf-8"))
    print(f"  {len(nut_map)} 코드")

    print(f"\n=== 매칭 + 보강 + 변형 수집 ===")
    stats = {"matched": 0, "weak": 0, "no_name": 0,
             "with_variants": 0, "total_variants": 0}
    weak_samples = []
    for code, info in nut_map.items():
        name_ko = info.get("name_ko")
        if not name_ko:
            stats["no_name"] += 1
            continue

        # 1) Best 단일 매칭 → default 영양 보강
        (match, score) = best_mfds_match(name_ko, None, mfds_items)
        if match is None or score < args.threshold:
            stats["weak"] += 1
            if len(weak_samples) < 15:
                weak_samples.append((code, name_ko, match[0] if match else "",
                                     round(score, 2)))
        else:
            mfds_name, mfds_nutr = match
            info["mfds_match"] = mfds_name
            info["mfds_match_score"] = round(score, 3)
            for k, v in mfds_nutr.items():
                if k in info:
                    info[f"mfds_{k}"] = v
                else:
                    info[k] = v
            stats["matched"] += 1

        # 2) 변형 리스트 수집 (앱에서 사용자가 고를 옵션들)
        variants = find_variants(name_ko, mfds_items)
        if variants:
            info["variants"] = variants
            info["variant_count"] = len(variants)
            stats["with_variants"] += 1
            stats["total_variants"] += len(variants)

    print(f"  Best 매칭 성공 : {stats['matched']:,}")
    print(f"  약한 매칭 (제외): {stats['weak']:,}")
    print(f"  이름 없음 (스킵): {stats['no_name']:,}")
    print(f"  변형 있는 코드 : {stats['with_variants']:,}")
    print(f"  총 변형 항목   : {stats['total_variants']:,}")
    avg_v = stats['total_variants'] / max(1, stats['with_variants'])
    print(f"  코드당 평균 변형: {avg_v:.1f}개")

    if weak_samples:
        print(f"\n  약한 매칭 샘플 (threshold {args.threshold} 미달):")
        for code, our_name, mfds_name, sc in weak_samples:
            print(f"    {code}  '{our_name}' ~ '{mfds_name}'  ({sc})")

    Path(args.out).write_text(
        json.dumps(nut_map, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n저장 -> {args.out}")
    print(f"\n샘플 (보강된 코드 1개):")
    matched_codes = [c for c, v in nut_map.items() if "mfds_match" in v]
    if matched_codes:
        sample = nut_map[matched_codes[0]]
        print(json.dumps({matched_codes[0]: sample},
                          ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
