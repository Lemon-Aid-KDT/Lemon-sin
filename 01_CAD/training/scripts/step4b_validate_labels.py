#!/usr/bin/env python3
"""
Step 4-B: 라벨 검증
- 카테고리 수량 검증 (예상 vs 실제)
- 극소 카테고리 플래그 (<20장 CRITICAL, <50장 WARNING)
- 중복 이미지 탐지 (perceptual hash, 크로스카테고리)
- 이미지 무결성 확인 (모든 정규화 이미지 재오픈)
- 소스 분포 분석

입력: drawing-datasets/normalized/
출력: drawing-datasets/normalized/label_report.json
"""

import os
import sys
import json
import time
from pathlib import Path
from collections import defaultdict
from multiprocessing import Pool

from PIL import Image
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from text_templates import (
    BASE_DIR, NORMALIZED_DIR, IMAGE_EXTS, EXCLUDE_CATEGORIES,
    CATEGORY_DESCRIPTIONS,
)

NUM_WORKERS = 10
CRITICAL_THRESHOLD = 20
WARNING_THRESHOLD = 50

# 통합 카테고리 파일
CLASS_NAMES_FILE = BASE_DIR / "drawing-datasets" / "unified_class_names.json"


def compute_dhash(img, hash_size=8):
    """Difference Hash (dHash) 계산 — 8x8 = 64bit"""
    # 그레이스케일 + 리사이즈
    img = img.convert('L').resize((hash_size + 1, hash_size), Image.LANCZOS)
    pixels = np.array(img)

    # 수평 그래디언트: 오른쪽 > 왼쪽이면 1
    diff = pixels[:, 1:] > pixels[:, :-1]
    # 64bit 해시를 16자리 hex 문자열로
    return ''.join(format(byte, '02x') for byte in np.packbits(diff.flatten()))


def validate_single_image(args):
    """단일 이미지 검증 (워커 함수)"""
    img_path, cat_name = args
    result = {
        'path': str(img_path),
        'category': cat_name,
        'status': 'ok',
        'dhash': None,
        'source': None,
        'size': None,
        'mode': None,
    }

    try:
        img = Image.open(img_path)
        img.load()  # 실제 디코딩 검증

        result['size'] = img.size
        result['mode'] = img.mode

        # 소스 추출 (파일명 접두사)
        stem = Path(img_path).stem
        if stem.startswith('misumi_'):
            result['source'] = 'misumi'
        elif stem.startswith('bearing_'):
            result['source'] = 'bearing'
        elif stem.startswith('staged_'):
            result['source'] = 'staged'
        else:
            result['source'] = 'unknown'

        # RGB 확인
        if img.mode != 'RGB':
            result['status'] = 'warn_not_rgb'

        # dHash 계산
        result['dhash'] = compute_dhash(img)

    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)

    return result


def find_cross_category_duplicates(results):
    """크로스카테고리 중복 탐지 (동일 dhash, 다른 카테고리)"""
    hash_to_entries = defaultdict(list)

    for r in results:
        if r['status'] != 'error' and r['dhash']:
            hash_to_entries[r['dhash']].append({
                'path': r['path'],
                'category': r['category'],
            })

    # 다른 카테고리에 동일 해시가 있는 경우만 추출
    duplicates = []
    for dhash, entries in hash_to_entries.items():
        categories = set(e['category'] for e in entries)
        if len(categories) > 1:
            duplicates.append({
                'dhash': dhash,
                'count': len(entries),
                'categories': list(categories),
                'files': entries[:10],  # 최대 10개만
            })

    # 같은 카테고리 내 중복도 별도 집계
    intra_duplicates = []
    for dhash, entries in hash_to_entries.items():
        if len(entries) > 1:
            categories = set(e['category'] for e in entries)
            if len(categories) == 1:
                intra_duplicates.append({
                    'dhash': dhash,
                    'category': list(categories)[0],
                    'count': len(entries),
                    'files': [e['path'] for e in entries[:5]],
                })

    return duplicates, intra_duplicates


def main():
    print("=" * 60)
    print("  Step 4-B: 라벨 검증")
    print(f"  입력: {NORMALIZED_DIR}")
    print("=" * 60)

    if not NORMALIZED_DIR.exists():
        print("  [ERROR] normalized 디렉토리 없음! Step 4-A를 먼저 실행하세요.")
        return None

    # 통합 카테고리 로드
    with open(CLASS_NAMES_FILE, 'r', encoding='utf-8') as f:
        class_names = json.load(f)
    expected_categories = {v for v in class_names.values() if v not in EXCLUDE_CATEGORIES}

    # === 1. 이미지 수집 ===
    print("\n[1/4] 정규화 이미지 수집 중...")
    tasks = []
    category_counts = defaultdict(int)

    for cat_dir in sorted(NORMALIZED_DIR.iterdir()):
        if not cat_dir.is_dir():
            continue
        cat_name = cat_dir.name
        for f in sorted(cat_dir.iterdir()):
            if f.suffix.lower() in IMAGE_EXTS and not f.name.startswith('.'):
                tasks.append((str(f), cat_name))
                category_counts[cat_name] += 1

    total_images = len(tasks)
    total_categories = len(category_counts)
    print(f"  {total_categories}개 카테고리, {total_images}장")

    if not tasks:
        print("  [ERROR] 검증할 이미지가 없습니다!")
        return None

    # === 2. 이미지 검증 (무결성 + dHash) ===
    print(f"\n[2/4] 이미지 검증 중 ({NUM_WORKERS} workers)...")
    start_time = time.time()

    results = []
    with Pool(NUM_WORKERS) as pool:
        for i, result in enumerate(pool.imap_unordered(validate_single_image, tasks), 1):
            results.append(result)
            if i % 2000 == 0 or i == total_images:
                elapsed = time.time() - start_time
                print(f"  [{i:>6d}/{total_images}] {i/elapsed:.0f} img/s")

    elapsed_validate = time.time() - start_time

    # === 3. 분석 ===
    print(f"\n[3/4] 분석 중...")

    # 무결성 결과
    ok_count = sum(1 for r in results if r['status'] == 'ok')
    warn_count = sum(1 for r in results if r['status'].startswith('warn'))
    error_count = sum(1 for r in results if r['status'] == 'error')
    errors = [r for r in results if r['status'] == 'error']

    print(f"  무결성: OK={ok_count}, WARN={warn_count}, ERROR={error_count}")

    # 소스 분포
    source_dist = defaultdict(lambda: defaultdict(int))
    for r in results:
        if r['status'] != 'error':
            source_dist[r['category']][r['source']] += 1

    # 극소 카테고리 플래그
    critical_categories = []
    warning_categories = []
    healthy_categories = []

    for cat_name, count in sorted(category_counts.items()):
        if count < CRITICAL_THRESHOLD:
            critical_categories.append({'name': cat_name, 'count': count, 'level': 'CRITICAL'})
        elif count < WARNING_THRESHOLD:
            warning_categories.append({'name': cat_name, 'count': count, 'level': 'WARNING'})
        else:
            healthy_categories.append({'name': cat_name, 'count': count})

    print(f"  극소 카테고리:")
    print(f"    CRITICAL (<{CRITICAL_THRESHOLD}장): {len(critical_categories)}개")
    for c in critical_categories:
        print(f"      - {c['name']}: {c['count']}장")
    print(f"    WARNING  (<{WARNING_THRESHOLD}장): {len(warning_categories)}개")
    for c in warning_categories:
        print(f"      - {c['name']}: {c['count']}장")
    print(f"    HEALTHY  (>={WARNING_THRESHOLD}장): {len(healthy_categories)}개")

    # 누락 카테고리 확인
    actual_categories = set(category_counts.keys())
    missing = expected_categories - actual_categories
    unexpected = actual_categories - expected_categories

    if missing:
        print(f"  [WARN] 누락 카테고리 ({len(missing)}개): {sorted(missing)}")
    if unexpected:
        print(f"  [WARN] 예상 외 카테고리 ({len(unexpected)}개): {sorted(unexpected)}")

    # 중복 탐지
    print(f"\n[4/4] 중복 탐지 중 (dHash)...")
    cross_dupes, intra_dupes = find_cross_category_duplicates(results)

    print(f"  크로스카테고리 중복: {len(cross_dupes)}건")
    if cross_dupes:
        for d in cross_dupes[:5]:
            print(f"    - hash={d['dhash'][:12]}... "
                  f"카테고리={d['categories']} ({d['count']}장)")
    print(f"  카테고리 내 중복: {len(intra_dupes)}건")

    # === 리포트 생성 ===
    report = {
        'step': '4-B: Label Validation',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {
            'total_images': total_images,
            'total_categories': total_categories,
            'integrity_ok': ok_count,
            'integrity_warn': warn_count,
            'integrity_error': error_count,
            'elapsed_seconds': round(elapsed_validate, 1),
        },
        'category_health': {
            'critical': critical_categories,
            'warning': warning_categories,
            'healthy_count': len(healthy_categories),
        },
        'missing_categories': sorted(list(missing)),
        'unexpected_categories': sorted(list(unexpected)),
        'category_counts': dict(sorted(category_counts.items())),
        'source_distribution': {
            cat: dict(sources) for cat, sources in sorted(source_dist.items())
        },
        'duplicates': {
            'cross_category': {
                'count': len(cross_dupes),
                'details': cross_dupes[:20],  # 상위 20개
            },
            'intra_category': {
                'count': len(intra_dupes),
                'total_duplicate_images': sum(d['count'] for d in intra_dupes),
                'details': sorted(intra_dupes, key=lambda x: -x['count'])[:20],
            },
        },
        'errors': [{'path': e['path'], 'error': e.get('error', 'unknown')} for e in errors[:50]],
        'recommendations': [],
    }

    # 추천 사항 생성
    if critical_categories:
        for c in critical_categories:
            report['recommendations'].append(
                f"CRITICAL: '{c['name']}'({c['count']}장) — 추가 수집 또는 제외 검토"
            )
    if cross_dupes:
        report['recommendations'].append(
            f"크로스카테고리 중복 {len(cross_dupes)}건 — 수동 검토 권장"
        )
    if error_count > 0:
        report['recommendations'].append(
            f"무결성 에러 {error_count}장 — 원본 확인 또는 제외"
        )

    report_path = NORMALIZED_DIR / 'label_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 최종 요약
    print(f"\n{'='*60}")
    print("  Step 4-B 완료: 라벨 검증")
    print(f"{'='*60}")
    print(f"  카테고리: {total_categories}개 (예상 {len(expected_categories)}개)")
    print(f"  이미지: {total_images}장")
    print(f"  무결성: OK={ok_count}, WARN={warn_count}, ERROR={error_count}")
    print(f"  CRITICAL 카테고리: {len(critical_categories)}개")
    print(f"  WARNING 카테고리: {len(warning_categories)}개")
    print(f"  크로스카테고리 중복: {len(cross_dupes)}건")
    print(f"  소요시간: {elapsed_validate:.1f}초 ({elapsed_validate/60:.1f}분)")
    print(f"\n  리포트: {report_path}")

    if report['recommendations']:
        print(f"\n  추천 사항:")
        for rec in report['recommendations']:
            print(f"    - {rec}")

    return report


if __name__ == '__main__':
    main()
