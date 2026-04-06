#!/usr/bin/env python3
"""
Step 4-A: 이미지 정규화
- RGBA → RGB (흰색 배경 합성)
- 최대 1024px 리사이즈 (LANCZOS, 종횡비 유지)
- PNG RGB 통일 저장
- multiprocessing 10워커 병렬처리

입력: MiSUMi(54,185) + Bearing(383) + Staged(7,145) 원본
출력: drawing-datasets/normalized/{category}/{source}_{stem}.png
"""

import os
import sys
import json
import time
from pathlib import Path
from collections import defaultdict
from multiprocessing import Pool, cpu_count

from PIL import Image

# 공유 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent))
from text_templates import (
    BASE_DIR, MISUMI_PNG_DIR, BEARING_PNG_DIR, STAGED_DIR, NORMALIZED_DIR,
    MISUMI_DIR_MAP, BEARING_DIR_MAP, IMAGE_EXTS, EXCLUDE_CATEGORIES,
)

MAX_SIZE = 1024
NUM_WORKERS = 10
REPORT_EVERY = 500  # 진행상황 보고 주기


def normalize_image(args):
    """단일 이미지 정규화 (워커 함수)"""
    src_path, dst_path = args
    try:
        img = Image.open(src_path)
        original_mode = img.mode
        original_size = img.size

        # 1) RGBA → RGB: 흰색 배경 합성
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])  # alpha 채널을 마스크로
            img = background
        elif img.mode == 'P':
            # 팔레트 모드 → RGBA로 변환 후 흰색 합성
            img = img.convert('RGBA')
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode == 'LA':
            # Luminance + Alpha → RGBA → RGB
            img = img.convert('RGBA')
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # 2) 최대 1024px 리사이즈 (종횡비 유지)
        w, h = img.size
        resized = False
        if max(w, h) > MAX_SIZE:
            if w > h:
                new_w = MAX_SIZE
                new_h = int(h * MAX_SIZE / w)
            else:
                new_h = MAX_SIZE
                new_w = int(w * MAX_SIZE / h)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            resized = True

        # 3) PNG RGB 저장
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        img.save(dst_path, 'PNG')

        return {
            'status': 'ok',
            'src': str(src_path),
            'dst': str(dst_path),
            'original_mode': original_mode,
            'original_size': original_size,
            'final_size': img.size,
            'resized': resized,
            'rgba_converted': original_mode in ('RGBA', 'P', 'LA'),
        }
    except Exception as e:
        return {
            'status': 'error',
            'src': str(src_path),
            'dst': str(dst_path),
            'error': str(e),
        }


def collect_all_tasks():
    """모든 소스에서 정규화 태스크 수집"""
    tasks = []  # (src_path, dst_path)
    source_stats = defaultdict(lambda: defaultdict(int))  # source → category → count

    # === MiSUMi ===
    if MISUMI_PNG_DIR.exists():
        for dir_name, cat_name in MISUMI_DIR_MAP.items():
            if cat_name in EXCLUDE_CATEGORIES:
                continue
            cat_dir = MISUMI_PNG_DIR / dir_name
            if not cat_dir.exists():
                continue
            for f in sorted(cat_dir.iterdir()):
                if f.suffix.lower() in IMAGE_EXTS and not f.name.startswith('.'):
                    dst = NORMALIZED_DIR / cat_name / f"misumi_{f.stem}.png"
                    tasks.append((str(f), str(dst)))
                    source_stats['misumi'][cat_name] += 1
    else:
        print(f"  [WARN] MiSUMi 디렉토리 없음: {MISUMI_PNG_DIR}")

    # === Bearing ===
    if BEARING_PNG_DIR.exists():
        for dir_name, cat_name in BEARING_DIR_MAP.items():
            if cat_name in EXCLUDE_CATEGORIES:
                continue
            cat_dir = BEARING_PNG_DIR / dir_name
            if not cat_dir.exists():
                continue
            for f in sorted(cat_dir.iterdir()):
                if f.suffix.lower() in IMAGE_EXTS and not f.name.startswith('.'):
                    dst = NORMALIZED_DIR / cat_name / f"bearing_{f.stem}.png"
                    tasks.append((str(f), str(dst)))
                    source_stats['bearing'][cat_name] += 1
    else:
        print(f"  [WARN] Bearing 디렉토리 없음: {BEARING_PNG_DIR}")

    # === Staged ===
    if STAGED_DIR.exists():
        for cat_dir in sorted(STAGED_DIR.iterdir()):
            if not cat_dir.is_dir():
                continue
            cat_name = cat_dir.name
            if cat_name in EXCLUDE_CATEGORIES:
                continue
            for f in sorted(cat_dir.iterdir()):
                if f.suffix.lower() in IMAGE_EXTS and not f.name.startswith('.'):
                    dst = NORMALIZED_DIR / cat_name / f"staged_{f.stem}.png"
                    tasks.append((str(f), str(dst)))
                    source_stats['staged'][cat_name] += 1
    else:
        print(f"  [WARN] Staged 디렉토리 없음: {STAGED_DIR}")

    return tasks, source_stats


def main():
    print("=" * 60)
    print("  Step 4-A: 이미지 정규화")
    print(f"  최대 크기: {MAX_SIZE}px")
    print(f"  워커 수: {NUM_WORKERS}")
    print(f"  출력: {NORMALIZED_DIR}")
    print("=" * 60)

    # 기존 출력 정리
    if NORMALIZED_DIR.exists():
        import shutil
        print(f"\n  기존 normalized 디렉토리 삭제 중...")
        shutil.rmtree(NORMALIZED_DIR)
    NORMALIZED_DIR.mkdir(parents=True)

    # === 1. 태스크 수집 ===
    print("\n[1/3] 이미지 태스크 수집 중...")
    tasks, source_stats = collect_all_tasks()

    misumi_count = sum(source_stats['misumi'].values())
    bearing_count = sum(source_stats['bearing'].values())
    staged_count = sum(source_stats['staged'].values())

    print(f"  MiSUMi: {len(source_stats['misumi'])}개 카테고리, {misumi_count}장")
    print(f"  Bearing: {len(source_stats['bearing'])}개 카테고리, {bearing_count}장")
    print(f"  Staged: {len(source_stats['staged'])}개 카테고리, {staged_count}장")
    print(f"  합계: {len(tasks)}장")

    if not tasks:
        print("  [ERROR] 처리할 이미지가 없습니다!")
        return

    # === 2. 병렬 정규화 ===
    print(f"\n[2/3] 이미지 정규화 중 ({NUM_WORKERS} workers)...")
    start_time = time.time()

    results = []
    error_count = 0
    rgba_count = 0
    resize_count = 0
    mode_dist = defaultdict(int)
    size_dist = {'small': 0, 'medium': 0, 'large': 0, 'xlarge': 0}  # <512, 512-1024, 1024-2048, 2048+

    with Pool(NUM_WORKERS) as pool:
        for i, result in enumerate(pool.imap_unordered(normalize_image, tasks), 1):
            results.append(result)

            if result['status'] == 'ok':
                mode_dist[result['original_mode']] += 1
                if result['rgba_converted']:
                    rgba_count += 1
                if result['resized']:
                    resize_count += 1

                # 원본 크기 분포
                max_dim = max(result['original_size'])
                if max_dim < 512:
                    size_dist['small'] += 1
                elif max_dim < 1024:
                    size_dist['medium'] += 1
                elif max_dim < 2048:
                    size_dist['large'] += 1
                else:
                    size_dist['xlarge'] += 1
            else:
                error_count += 1

            # 진행상황 보고
            if i % REPORT_EVERY == 0 or i == len(tasks):
                elapsed = time.time() - start_time
                speed = i / elapsed
                remaining = (len(tasks) - i) / speed if speed > 0 else 0
                print(f"  [{i:>6d}/{len(tasks)}] {speed:.1f} img/s, "
                      f"errors: {error_count}, "
                      f"elapsed: {elapsed:.0f}s, "
                      f"remaining: ~{remaining:.0f}s")

    elapsed_total = time.time() - start_time

    # === 3. 리포트 생성 ===
    print(f"\n[3/3] 정규화 리포트 생성 중...")

    # 카테고리별 최종 수량 확인
    category_counts = defaultdict(int)
    for result in results:
        if result['status'] == 'ok':
            # dst 경로에서 카테고리 추출
            dst_path = Path(result['dst'])
            cat_name = dst_path.parent.name
            category_counts[cat_name] += 1

    # 에러 목록
    errors = [r for r in results if r['status'] == 'error']

    report = {
        'step': '4-A: Image Normalization',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'config': {
            'max_size': MAX_SIZE,
            'num_workers': NUM_WORKERS,
            'output_dir': str(NORMALIZED_DIR),
        },
        'summary': {
            'total_input': len(tasks),
            'total_success': len(tasks) - error_count,
            'total_errors': error_count,
            'elapsed_seconds': round(elapsed_total, 1),
            'speed_img_per_sec': round(len(tasks) / elapsed_total, 2),
        },
        'sources': {
            'misumi': {'categories': len(source_stats['misumi']), 'images': misumi_count},
            'bearing': {'categories': len(source_stats['bearing']), 'images': bearing_count},
            'staged': {'categories': len(source_stats['staged']), 'images': staged_count},
        },
        'conversions': {
            'rgba_to_rgb': rgba_count,
            'resized': resize_count,
            'not_resized': len(tasks) - error_count - resize_count,
        },
        'original_mode_distribution': dict(mode_dist),
        'original_size_distribution': {
            '<512px': size_dist['small'],
            '512-1024px': size_dist['medium'],
            '1024-2048px': size_dist['large'],
            '2048px+': size_dist['xlarge'],
        },
        'categories': {
            'total': len(category_counts),
            'per_category': dict(sorted(category_counts.items())),
        },
        'source_per_category': {
            'misumi': dict(sorted(source_stats['misumi'].items())),
            'bearing': dict(sorted(source_stats['bearing'].items())),
            'staged': dict(sorted(source_stats['staged'].items())),
        },
        'errors': [{'src': e['src'], 'error': e['error']} for e in errors[:50]],
    }

    report_path = NORMALIZED_DIR / 'normalization_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # === 최종 요약 ===
    print(f"\n{'='*60}")
    print("  Step 4-A 완료: 이미지 정규화")
    print(f"{'='*60}")
    print(f"  처리: {len(tasks) - error_count}/{len(tasks)}장 성공")
    print(f"  에러: {error_count}장")
    print(f"  카테고리: {len(category_counts)}개")
    print(f"  RGBA→RGB 변환: {rgba_count}장")
    print(f"  리사이즈: {resize_count}장")
    print(f"  소요시간: {elapsed_total:.1f}초 ({elapsed_total/60:.1f}분)")
    print(f"  속도: {len(tasks)/elapsed_total:.1f} img/s")
    print(f"\n  모드 분포: {dict(mode_dist)}")
    print(f"  크기 분포: <512={size_dist['small']}, "
          f"512-1024={size_dist['medium']}, "
          f"1024-2048={size_dist['large']}, "
          f"2048+={size_dist['xlarge']}")
    print(f"\n  리포트: {report_path}")

    if errors:
        print(f"\n  [WARN] 에러 샘플 (처음 5개):")
        for e in errors[:5]:
            print(f"    - {Path(e['src']).name}: {e['error']}")

    return report


if __name__ == '__main__':
    main()
