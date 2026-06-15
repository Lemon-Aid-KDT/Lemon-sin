# DINOv3 음식 분류 + 다중요리 파이프라인

실사용(wild) 음식 분류를 위해, 우리가 학습한 YOLO(exp16b, wild 0.60) 대신
**DINOv3 사전학습 특징 + 실데이터 선형학습(probe)** 으로 wild 0.84를 달성한 분류기와,
**Grounding DINO 탐지 → 마스킹 → DINOv3 분류** 다중요리 파이프라인.

> 배경 실험 전체(왜 DINOv3·Grounding DINO인가)는 `docs/superpowers/plans/exp06_review/`의
> `_eval_*`, `_test_*` 스크립트와 메모리 `project-clip-zeroshot` 참조.

## 구성

| 파일 | 역할 |
|---|---|
| `train_probe.py` | DINOv3-vitb16 + realworld 실데이터로 선형 프로브 학습 → `probe_head.pt` 저장 |
| `probe_head.pt` / `probe_classes.json` | 학습된 선형 분류기(123KB) + 40클래스 목록 |
| `food_pipeline_dino.py` | `FoodPipeline` — 디텍터 박스 → (나머지 음식 마스킹) → DINOv3 분류. `classify_boxes(im, boxes)`로 탐지기 무관 |
| `app_pipeline_dino_demo.py` | Streamlit 데모 (port 8506) |

## 사전 준비

1. **HF 토큰** (DINOv3는 게이트): `hf auth login` 후 라이선스 동의. 실행 시 `HF_TOKEN` 환경변수.
   ⚠️ DINOv3는 상용 라이선스 별도 — 성과발표/연구용. 상용 배포 시 DINOv2(Apache-2.0, wild 0.83)로 교체 검토.
2. `transformers<5` 필수 (4.57.6 설치됨).
3. 디텍터: 단일요리는 인계 `../detector/detector_best.pt`, 다중요리는 Grounding DINO(`IDEA-Research/grounding-dino-tiny`, 비게이트).

## 핵심 결과 (wild 545 동일셋, 단일요리)

- exp16b(우리 YOLO) 0.598 → **DINOv3 프로브 0.842** (+0.244)
- 다중요리: Grounding DINO가 한상 음식 다수 검출(YOLO는 1~2개), 각 음식은 "나머지 마스킹" 후 분류
  (정수님 아이디어 — 타이트 크롭 0.72 vs 마스킹 0.84로 검증).

## 남은 과제

- 비대상 음식(흰밥·반찬) reject — Grounding DINO가 모든 food를 박스.
- 다중요리 분류 크롭 튜닝 — 작은 음식 OOD로 신뢰도 하락(generous pad + mask).
