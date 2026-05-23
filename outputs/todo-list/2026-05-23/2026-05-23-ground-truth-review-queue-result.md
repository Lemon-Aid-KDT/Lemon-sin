# 2026-05-23 Ground Truth Review Queue 결과

## 목적

stage12에서 strict KPI readiness 실패 원인은 코드 매칭보다 ground-truth 검수 상태에 있었다. 이번 변경은 사람이 바로 검수할 수 있는 redacted review queue를 생성하는 도구를 추가한다.

도구는 raw OCR text, provider payload, request header, image bytes, `.env`, secret 값을 읽거나 저장하지 않는다. 출력은 fixture id, bounded warning code, provider status/error code, expected count, action hint만 포함한다.

## 구현 범위

- `backend/scripts/build_ocr_ground_truth_review_queue.py`
  - three-tier manifest와 evaluation JSON을 입력으로 받음
  - raw field key를 recursive reject
  - `expected_quality_warnings`와 `unscoreable_fixture_ids`를 fixture 단위로 병합
  - provider status/error code와 parsed ingredient count를 bounded metadata로 기록
  - `ground-truth-review-queue.jsonl` / `.md` 생성
- `backend/Nutrition-backend/tests/unit/scripts/test_build_ocr_ground_truth_review_queue.py`
  - review action 생성 검증
  - raw OCR/provider field 입력 차단 검증

## Stage13 생성 결과

대상:

```text
outputs/generated/ocr-eval/2026-05-23-stage13-ground-truth-review-queue/
```

생성 결과:

```text
queue_count=16
jsonl=outputs/generated/ocr-eval/2026-05-23-stage13-ground-truth-review-queue/ground-truth-review-queue.jsonl
markdown=outputs/generated/ocr-eval/2026-05-23-stage13-ground-truth-review-queue/ground-truth-review-queue.md
```

우선순위 분포:

```text
priority=10 count=1
priority=20 count=8
priority=30 count=2
priority=50 count=5
```

Action 분포:

```text
add_human_reviewed_expected_ingredients=9
clear_pending_review_after_manual_validation=16
replace_non_label_or_empty_ocr_fixture=1
verify_or_replace_low_quality_expected_ingredients=2
confirm_low_confidence_expected_rows=2
remove_heading_from_expected_ingredients=1
```

## Review 순서

1. `naver-live-0009`
   - reason: `expected_ingredients_missing`, `provider_error:ocr_empty_text`, `provisional_expected_fixture`, `unscoreable_fixture`
   - action: `replace_non_label_or_empty_ocr_fixture`
   - 해석: 텍스트 없는 블리스터 입력이라 ingredient-label fixture로 부적합
2. `naver-live-0001`, `0003`, `0004`, `0007`, `0008`, `0010`, `0011`, `0016`
   - reason: `expected_ingredients_missing`
   - action: human-reviewed expected ingredients 추가
3. `naver-live-0005`, `0014`
   - reason: `low_confidence_expected_ingredient`, `scoreable_expected_ingredients_missing`
   - action: low-confidence expected row 검수 또는 교체
4. `naver-live-0002`, `0006`, `0012`, `0013`, `0015`
   - reason: `provisional_expected_fixture` 중심
   - action: manual validation 후 pending warning 제거

## 보안 및 유출 점검

- queue artifact privacy scan 결과: `ocr_artifact_privacy_ok files=2`
- output에는 raw OCR text, provider payload, request headers, image bytes, secret 값이 없다.
- 입력 manifest/evaluation에 forbidden raw key가 있으면 `ValueError`로 fail closed 한다.
- 이미지 경로는 manifest에 있는 상대 경로만 사용하고 absolute local path로 resolve하지 않는다.

## 다음 보완 계획

1. priority 10/20 항목부터 expected fixture를 사람 검수로 채운다.
2. `naver-live-0009`는 라벨 이미지로 교체하거나 chronic KPI manifest에서 제외하고 대체 fixture를 추가한다.
3. 수정된 expected snapshot에서 `ground_truth_pending_human_review`를 제거하고 source를 `manual` 또는 `user_confirmed`로 승격한다.
4. manifest 재생성 후 strict KPI readiness gate를 재실행한다.

## 검증 기준

- review queue unit tests: `2 passed`
- generated review queue: completed
- generated artifact privacy scan: passed
- 공식 문서 확인:
  - Python `json`: https://docs.python.org/3/library/json.html
  - Python `dataclasses`: https://docs.python.org/3/library/dataclasses.html
