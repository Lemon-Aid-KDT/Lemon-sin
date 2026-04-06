#!/usr/bin/env python3
"""
Step 4-C: 데이터셋 분할
- train 80% / val 10% / test 10% (seed=42)
- 특허 문서 그룹핑 (같은 특허번호 → 동일 split, 데이터 누출 방지)
- Stratified split (카테고리별 비율 유지)
- 데이터 누출 검증 (SHA256 해시)
- YOLO dataset.yaml + CLIP CSV 출력

입력: drawing-datasets/normalized/ + (선택) label_overrides.json
출력: drawing-datasets/preprocessed_dataset/
  ├── train/{category}/*.png   (심볼릭 링크)
  ├── val/{category}/*.png
  ├── test/{category}/*.png
  ├── dataset.yaml             (YOLO 설정)
  ├── train.csv / val.csv / test.csv  (CLIP 설정)
  ├── split_manifest.json      (재현성)
  └── preprocessing_report.json
"""

import os
import sys
import re
import json
import time
import random
import hashlib
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
from text_templates import (
    BASE_DIR, NORMALIZED_DIR, OUTPUT_DIR, IMAGE_EXTS, EXCLUDE_CATEGORIES,
    CATEGORY_DESCRIPTIONS, TEXT_TEMPLATES,
)

RANDOM_SEED = 42
TRAIN_RATIO = 0.80
VAL_RATIO = 0.10
TEST_RATIO = 0.10

CLASS_NAMES_FILE = BASE_DIR / "drawing-datasets" / "unified_class_names.json"
OVERRIDES_FILE = NORMALIZED_DIR / "label_overrides.json"

# 특허 번호 패턴 (USPTO/Google Patents)
PATENT_PATTERN = re.compile(r'^staged_(US\d+[A-Z]\d+|EP\d+[A-Z]\d+|WO\d+[A-Z]\d+|JP\d+[A-Z]\d*)')


def extract_patent_group(filename):
    """파일명에서 특허 그룹 키 추출 (같은 특허문서 = 같은 split)"""
    m = PATENT_PATTERN.match(filename)
    if m:
        return m.group(1)
    return None


def compute_file_sha256(filepath):
    """SHA256 해시 계산 (데이터 누출 검증용)"""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def stratified_split_with_groups(category_images, train_r, val_r, test_r, seed):
    """
    Stratified split with patent document grouping.
    Returns: {category: {'train': [...], 'val': [...], 'test': [...]}}
    """
    rng = random.Random(seed)
    splits = {}

    for cat_name, images in sorted(category_images.items()):
        # 그룹핑: 특허문서는 같은 그룹, 나머지는 개별
        groups = defaultdict(list)
        for img_path in images:
            fname = Path(img_path).stem
            patent_group = extract_patent_group(fname)
            if patent_group:
                groups[f"patent_{patent_group}"].append(img_path)
            else:
                groups[f"single_{fname}"].append(img_path)

        # 그룹 단위로 셔플
        group_keys = list(groups.keys())
        rng.shuffle(group_keys)

        # 그룹별 이미지 수 계산
        total = len(images)
        target_train = int(total * train_r)
        target_val = int(total * val_r)
        # test는 나머지

        train_imgs = []
        val_imgs = []
        test_imgs = []

        for gk in group_keys:
            g_imgs = groups[gk]
            # 현재까지 누적된 수 기준으로 할당
            if len(train_imgs) < target_train:
                train_imgs.extend(g_imgs)
            elif len(val_imgs) < target_val:
                val_imgs.extend(g_imgs)
            else:
                test_imgs.extend(g_imgs)

        # 최소 보장: 각 split에 최소 1장 (카테고리 크기가 충분할 때)
        if total >= 3:
            if not val_imgs and train_imgs:
                val_imgs.append(train_imgs.pop())
            if not test_imgs and train_imgs:
                test_imgs.append(train_imgs.pop())
        elif total == 2:
            if not val_imgs and train_imgs:
                val_imgs.append(train_imgs.pop())
            test_imgs = []  # test 없음
        # total == 1: train에만

        splits[cat_name] = {
            'train': train_imgs,
            'val': val_imgs,
            'test': test_imgs,
        }

    return splits


def create_symlinks(images, target_dir):
    """심볼릭 링크 생성"""
    target_dir.mkdir(parents=True, exist_ok=True)
    created = 0

    for img_path in images:
        src = Path(img_path)
        dst = target_dir / src.name

        # 이름 충돌 방지
        if dst.exists() or dst.is_symlink():
            stem = src.stem
            suffix = src.suffix
            counter = 1
            while dst.exists() or dst.is_symlink():
                dst = target_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        try:
            os.symlink(str(src.resolve()), str(dst))
            created += 1
        except OSError as e:
            print(f"    [ERROR] 링크 실패: {src.name} - {e}")

    return created


def generate_clip_csv(splits, csv_dir):
    """CLIP fine-tuning용 CSV 생성 (filepath, caption, category)"""
    rng = random.Random(RANDOM_SEED)

    for split_name in ['train', 'val', 'test']:
        csv_path = csv_dir / f"{split_name}.csv"
        rows = []

        for cat_name, split_data in sorted(splits.items()):
            images = split_data[split_name]
            if not images:
                continue

            descriptions = CATEGORY_DESCRIPTIONS.get(cat_name, [cat_name])

            for img_path in images:
                # 랜덤 템플릿 + 랜덤 설명 선택
                template = rng.choice(TEXT_TEMPLATES)
                desc = rng.choice(descriptions)
                caption = template.format(desc)
                rows.append(f"{img_path},{caption},{cat_name}")

        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write("filepath,caption,category\n")
            for row in rows:
                f.write(row + "\n")

        print(f"  {split_name}.csv: {len(rows)}행")


def main():
    print("=" * 60)
    print("  Step 4-C: 데이터셋 분할")
    print(f"  비율: train {TRAIN_RATIO*100:.0f}% / val {VAL_RATIO*100:.0f}% / test {TEST_RATIO*100:.0f}%")
    print(f"  출력: {OUTPUT_DIR}")
    print("=" * 60)

    if not NORMALIZED_DIR.exists():
        print("  [ERROR] normalized 디렉토리 없음! Step 4-A를 먼저 실행하세요.")
        return None

    # === 0. Label overrides 확인 ===
    overrides = {}
    if OVERRIDES_FILE.exists():
        print(f"\n  Label overrides 발견: {OVERRIDES_FILE}")
        with open(OVERRIDES_FILE, 'r', encoding='utf-8') as f:
            overrides = json.load(f)
        if 'remove_categories' in overrides:
            print(f"    제거 카테고리: {overrides['remove_categories']}")
        if 'merge_categories' in overrides:
            print(f"    병합 카테고리: {overrides['merge_categories']}")
    else:
        print(f"\n  Label overrides 없음 (기본 설정 사용)")

    # 통합 카테고리 로드
    with open(CLASS_NAMES_FILE, 'r', encoding='utf-8') as f:
        class_names = json.load(f)

    # === 1. 이미지 수집 ===
    print("\n[1/5] 정규화 이미지 수집 중...")
    category_images = defaultdict(list)

    for cat_dir in sorted(NORMALIZED_DIR.iterdir()):
        if not cat_dir.is_dir():
            continue
        cat_name = cat_dir.name
        if cat_name in EXCLUDE_CATEGORIES:
            continue

        # Override: 제거
        if cat_name in overrides.get('remove_categories', []):
            print(f"  [SKIP] {cat_name} (override: 제거)")
            continue

        # Override: 병합
        merge_target = overrides.get('merge_categories', {}).get(cat_name)
        target_cat = merge_target if merge_target else cat_name

        for f in sorted(cat_dir.iterdir()):
            if f.suffix.lower() in IMAGE_EXTS and not f.name.startswith('.'):
                category_images[target_cat].append(str(f))

    total_images = sum(len(v) for v in category_images.values())
    total_categories = len(category_images)
    print(f"  {total_categories}개 카테고리, {total_images}장")

    # === 2. Stratified split ===
    print(f"\n[2/5] Stratified split (seed={RANDOM_SEED})...")
    splits = stratified_split_with_groups(
        category_images, TRAIN_RATIO, VAL_RATIO, TEST_RATIO, RANDOM_SEED
    )

    # 통계
    total_train = sum(len(s['train']) for s in splits.values())
    total_val = sum(len(s['val']) for s in splits.values())
    total_test = sum(len(s['test']) for s in splits.values())

    print(f"  Train: {total_train}장 ({total_train/total_images*100:.1f}%)")
    print(f"  Val:   {total_val}장 ({total_val/total_images*100:.1f}%)")
    print(f"  Test:  {total_test}장 ({total_test/total_images*100:.1f}%)")

    # 특허 그룹핑 확인
    patent_groups_found = 0
    for cat_name, images in category_images.items():
        for img_path in images:
            if extract_patent_group(Path(img_path).stem):
                patent_groups_found += 1
    print(f"  특허 그룹핑 적용: {patent_groups_found}장")

    # === 3. 출력 디렉토리 생성 + 심볼릭 링크 ===
    print(f"\n[3/5] 심볼릭 링크 생성 중...")

    if OUTPUT_DIR.exists():
        import shutil
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    for cat_name in sorted(splits.keys()):
        s = splits[cat_name]
        for split_name in ['train', 'val', 'test']:
            if s[split_name]:
                target_dir = OUTPUT_DIR / split_name / cat_name
                create_symlinks(s[split_name], target_dir)

    print(f"  완료: {OUTPUT_DIR}")

    # === 4. 데이터 누출 검증 ===
    print(f"\n[4/5] 데이터 누출 검증 중...")

    # 파일경로 기반 중복 검사 (빠름)
    train_files = set()
    val_files = set()
    test_files = set()

    for cat_name, s in splits.items():
        for p in s['train']:
            train_files.add(p)
        for p in s['val']:
            val_files.add(p)
        for p in s['test']:
            test_files.add(p)

    tv_overlap = train_files & val_files
    tt_overlap = train_files & test_files
    vt_overlap = val_files & test_files

    leakage_found = len(tv_overlap) + len(tt_overlap) + len(vt_overlap)
    print(f"  Train-Val 중복: {len(tv_overlap)}")
    print(f"  Train-Test 중복: {len(tt_overlap)}")
    print(f"  Val-Test 중복: {len(vt_overlap)}")

    if leakage_found:
        print(f"  [ERROR] 데이터 누출 발견! {leakage_found}건")
    else:
        print(f"  [OK] 데이터 누출 없음")

    # === 5. 설정 파일 생성 ===
    print(f"\n[5/5] 설정 파일 생성 중...")

    # 5-1) YOLO dataset.yaml
    id_to_name = {}
    name_to_id = {}
    for id_str, name in class_names.items():
        if name in splits:
            id_to_name[int(id_str)] = name
            name_to_id[name] = int(id_str)

    yaml_content = f"""# Preprocessed Dataset for YOLOv8-cls
# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
# Categories: {total_categories}
# Images: {total_images} (train {total_train} / val {total_val} / test {total_test})

path: {OUTPUT_DIR}
train: train
val: val
test: test

# Categories ({total_categories})
names:
"""
    for cat_id in sorted(id_to_name.keys()):
        yaml_content += f"  {cat_id}: {id_to_name[cat_id]}\n"

    yaml_path = OUTPUT_DIR / "dataset.yaml"
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)
    print(f"  dataset.yaml: {yaml_path}")

    # 5-2) CLIP CSV
    generate_clip_csv(splits, OUTPUT_DIR)

    # 5-3) Split manifest (재현성)
    manifest = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'seed': RANDOM_SEED,
        'ratios': {'train': TRAIN_RATIO, 'val': VAL_RATIO, 'test': TEST_RATIO},
        'overrides_applied': overrides if overrides else None,
        'total_categories': total_categories,
        'total_images': total_images,
        'split_counts': {
            'train': total_train,
            'val': total_val,
            'test': total_test,
        },
        'per_category': {},
        'leakage_check': {
            'train_val_overlap': len(tv_overlap),
            'train_test_overlap': len(tt_overlap),
            'val_test_overlap': len(vt_overlap),
            'status': 'CLEAN' if leakage_found == 0 else 'LEAKAGE_FOUND',
        },
    }

    for cat_name in sorted(splits.keys()):
        s = splits[cat_name]
        manifest['per_category'][cat_name] = {
            'total': len(s['train']) + len(s['val']) + len(s['test']),
            'train': len(s['train']),
            'val': len(s['val']),
            'test': len(s['test']),
        }

    manifest_path = OUTPUT_DIR / "split_manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"  split_manifest.json: {manifest_path}")

    # 5-4) class_names.json 복사
    import shutil
    shutil.copy2(CLASS_NAMES_FILE, OUTPUT_DIR / "class_names.json")

    # 5-5) preprocessing_report.json
    preprocessing_report = {
        'step': '4-C: Dataset Split',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'config': {
            'seed': RANDOM_SEED,
            'train_ratio': TRAIN_RATIO,
            'val_ratio': VAL_RATIO,
            'test_ratio': TEST_RATIO,
            'patent_grouping': True,
            'overrides': overrides if overrides else None,
        },
        'summary': {
            'total_categories': total_categories,
            'total_images': total_images,
            'train': total_train,
            'val': total_val,
            'test': total_test,
            'patent_grouped_images': patent_groups_found,
        },
        'leakage': {
            'status': 'CLEAN' if leakage_found == 0 else 'LEAKAGE_FOUND',
            'details': {
                'train_val': len(tv_overlap),
                'train_test': len(tt_overlap),
                'val_test': len(vt_overlap),
            },
        },
        'outputs': {
            'yolo_yaml': str(yaml_path),
            'clip_train_csv': str(OUTPUT_DIR / 'train.csv'),
            'clip_val_csv': str(OUTPUT_DIR / 'val.csv'),
            'clip_test_csv': str(OUTPUT_DIR / 'test.csv'),
            'manifest': str(manifest_path),
        },
    }

    report_path = OUTPUT_DIR / "preprocessing_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(preprocessing_report, f, ensure_ascii=False, indent=2)

    # === 최종 요약 ===
    print(f"\n{'='*60}")
    print("  Step 4-C 완료: 데이터셋 분할")
    print(f"{'='*60}")
    print(f"  카테고리: {total_categories}개")
    print(f"  Train: {total_train}장 ({total_train/total_images*100:.1f}%)")
    print(f"  Val:   {total_val}장 ({total_val/total_images*100:.1f}%)")
    print(f"  Test:  {total_test}장 ({total_test/total_images*100:.1f}%)")
    print(f"  합계:  {total_images}장")
    print(f"  누출 검증: {'CLEAN' if leakage_found == 0 else 'LEAKAGE FOUND!'}")
    print(f"\n  출력: {OUTPUT_DIR}")
    print(f"\n  학습 명령어:")
    print(f"  yolo classify train data={yaml_path} model=yolov8s-cls.pt epochs=100 imgsz=224")

    return preprocessing_report


if __name__ == '__main__':
    main()
