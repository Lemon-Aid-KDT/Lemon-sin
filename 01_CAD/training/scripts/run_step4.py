#!/usr/bin/env python3
"""
Step 4 오케스트레이터: 전처리 파이프라인 전체 실행
  4-A: 이미지 정규화 (RGBA→RGB, 리사이즈, PNG 통일)
  4-B: 라벨 검증 (수량, 극소 카테고리, 중복, 무결성)
  4-C: 데이터셋 분할 (train/val/test, 특허 그룹핑, YOLO+CLIP)

사용법:
  python preprocessing/run_step4.py          # 전체 실행
  python preprocessing/run_step4.py --skip-normalize  # 4-A 건너뛰기 (이미 완료)
  python preprocessing/run_step4.py --only 4a         # 4-A만 실행
  python preprocessing/run_step4.py --only 4b         # 4-B만 실행
  python preprocessing/run_step4.py --only 4c         # 4-C만 실행
"""

import sys
import time
import argparse
from pathlib import Path

# 현재 디렉토리를 path에 추가
sys.path.insert(0, str(Path(__file__).parent))


def run_step4a():
    """4-A: 이미지 정규화"""
    print("\n" + "=" * 70)
    print("  STEP 4-A: 이미지 정규화 시작")
    print("=" * 70)
    from step4a_normalize import main as step4a_main
    return step4a_main()


def run_step4b():
    """4-B: 라벨 검증"""
    print("\n" + "=" * 70)
    print("  STEP 4-B: 라벨 검증 시작")
    print("=" * 70)
    from step4b_validate_labels import main as step4b_main
    return step4b_main()


def run_step4c():
    """4-C: 데이터셋 분할"""
    print("\n" + "=" * 70)
    print("  STEP 4-C: 데이터셋 분할 시작")
    print("=" * 70)
    from step4c_split_dataset import main as step4c_main
    return step4c_main()


def main():
    parser = argparse.ArgumentParser(description='Step 4: 전처리 파이프라인')
    parser.add_argument('--skip-normalize', action='store_true',
                       help='4-A 정규화 건너뛰기 (이미 완료된 경우)')
    parser.add_argument('--only', choices=['4a', '4b', '4c'],
                       help='특정 단계만 실행')
    args = parser.parse_args()

    overall_start = time.time()

    print("=" * 70)
    print("  Step 4: 전처리 파이프라인")
    print("  4-A: 이미지 정규화 (RGBA→RGB, max 1024px, PNG)")
    print("  4-B: 라벨 검증 (수량, 중복, 무결성)")
    print("  4-C: 데이터셋 분할 (train/val/test 80/10/10)")
    print("=" * 70)

    results = {}

    # 개별 실행 모드
    if args.only:
        if args.only == '4a':
            results['4a'] = run_step4a()
        elif args.only == '4b':
            results['4b'] = run_step4b()
        elif args.only == '4c':
            results['4c'] = run_step4c()
    else:
        # 전체 실행
        # 4-A
        if args.skip_normalize:
            print("\n  [SKIP] 4-A 정규화 건너뛰기 (--skip-normalize)")
        else:
            results['4a'] = run_step4a()
            if results['4a'] is None:
                print("\n  [ABORT] 4-A 실패 — 파이프라인 중단")
                return

        # 4-B
        results['4b'] = run_step4b()
        if results['4b'] is None:
            print("\n  [ABORT] 4-B 실패 — 파이프라인 중단")
            return

        # 4-B 결과 확인: CRITICAL 카테고리 경고
        critical = results['4b'].get('category_health', {}).get('critical', [])
        if critical:
            print(f"\n  [INFO] CRITICAL 카테고리 {len(critical)}개 발견:")
            for c in critical:
                print(f"    - {c['name']}: {c['count']}장")
            print("  → label_overrides.json으로 제거/병합 가능 (현재는 그대로 진행)")

        # 4-C
        results['4c'] = run_step4c()
        if results['4c'] is None:
            print("\n  [ABORT] 4-C 실패 — 파이프라인 중단")
            return

    # 최종 요약
    overall_elapsed = time.time() - overall_start

    print(f"\n{'='*70}")
    print("  Step 4 전처리 파이프라인 완료")
    print(f"{'='*70}")
    print(f"  총 소요시간: {overall_elapsed:.1f}초 ({overall_elapsed/60:.1f}분)")

    if '4a' in results and results['4a']:
        s = results['4a']['summary']
        print(f"\n  4-A 정규화:")
        print(f"    {s['total_success']}/{s['total_input']}장 성공 "
              f"({s['elapsed_seconds']}초)")

    if '4b' in results and results['4b']:
        s = results['4b']['summary']
        print(f"\n  4-B 라벨 검증:")
        print(f"    {s['total_categories']}개 카테고리, {s['total_images']}장")
        print(f"    무결성: OK={s['integrity_ok']}, ERROR={s['integrity_error']}")

    if '4c' in results and results['4c']:
        s = results['4c']['summary']
        print(f"\n  4-C 데이터셋 분할:")
        print(f"    Train {s['train']} / Val {s['val']} / Test {s['test']}")
        print(f"    누출: {results['4c']['leakage']['status']}")


if __name__ == '__main__':
    main()
