# 친구/본인 기여 영양제 라벨 사진 동의 메모

> 본 파일은 `raw/friend_contributed/inbox/`에 사진을 제출한 모든 기여자의 동의 사실을 누적 기록한다.
> 새 기여자가 추가될 때마다 아래 표에 행을 한 줄 더한다. 사진 자체는 `data/CLAUDE.md` Rule 6에 따라 git에 커밋하지 않는다(이 파일과 같은 디렉토리에 두되, `.gitignore`로 raw 이미지는 차단됨).

## 정책 요약

- **사용 범위**: Lemon Healthcare OCR fixture 평가 및 비공개 학습 목적
- **외부 전송**: 없음 (완전 로컬, PaddleOCR + Ollama Vision만 호출)
- **원본 이미지 retention**: 0일(`image_retention_days=0`) 정책. ground-truth 라벨링 결과만 보존하고 raw 이미지는 가명 hash로만 추적
- **vector 학습 적재**: 별도 `image_learning_dataset` consent 게이트를 통과한 뒤에만 진행 (기본 비활성)
- **외부 OCR 동의**: Google Vision / CLOVA로의 전송은 별도 `EXTERNAL_OCR_PROCESSING` consent 필요. 본 데이터셋은 외부 OCR로 보내지 않음

## 동의 기록 표

| 기여자 ID | 촬영일자 (YYYY-MM-DD) | 제출 파일 hash 또는 인덱스 범위 | 비고 (예: 라벨 언어, 제품 카테고리) |
| --- | --- | --- | --- |
| contributor-000 (template) | YYYY-MM-DD | <hash-prefix> | 예: 한국어 단일, 비타민 멀티 |

## 새 기여자 추가 절차

1. 기여자에게 위 "정책 요약"을 보여주고 명시 동의를 받는다.
2. 사진을 `inbox/`에 복사한다(파일명 임의).
3. `prepare_supplement_ocr_live_manifest.py`가 hash 기반 파일명으로 정규화한 뒤, 이 표에 hash 또는 인덱스 범위를 추가한다.
4. 기여자가 동의를 철회하면 해당 hash의 expected snapshot, manifest row, 가명 metadata를 모두 삭제한다.

## 관련 문서

- 본 디렉토리 상위 README: `../../../README.md` (Stage 0 워크플로 §②)
- 프로젝트 동의 정책: `docs/Nutrition-docs/10-compliance-checklist.md`, `docs/Nutrition-docs/17-image-collection-consent-plan.md`
- 데이터 작업 규칙: `data/CLAUDE.md`
