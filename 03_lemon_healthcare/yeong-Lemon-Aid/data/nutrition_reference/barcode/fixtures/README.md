# Barcode Identity Fixtures

P1-1 FoodQR/MFDS 평가용 fixture 공간입니다.

- 실제 API 키, full request URL, raw provider payload는 저장하지 않습니다.
- 실제 제품 fixture는 공개 데이터 또는 팀 동의 제품만 사용합니다.
- 정확도, 커버리지, OCR 대비 개선율은 fixture 관측값이 수집된 뒤에만 계산합니다.
- `*.example.jsonl` 파일은 형식 예시이며 성능 주장 근거가 아닙니다.

## C003 contract fixture gate

- `c003_contract_cases.example.jsonl`은 C003 fixture 형식 예시만 제공합니다.
- 현재 C003 live fixture는 서비스 권한 확인 전까지 생성하지 않습니다.
- C003 권한이 확인되면 공개 문서 sample 또는 팀 동의 제품에서 allowlisted field만 저장합니다.
- 저장 금지: `MFDS_API_KEY`, full request URL, 원문 HTML 오류, raw provider payload.

## 2026-05-16 공개 FoodQR fixture

- `barcode_identity_cases.foodqr-public.2026-05-16.jsonl`
- 출처: 공공데이터포털 FoodQR 공개 API에서 수집한 allowlisted field
- 검증: 각 barcode를 `brcd_no` exact lookup으로 재조회한 observation만 저장
- 주의: 동일 barcode가 여러 FoodQR 행/version으로 반환될 수 있으므로, 이 fixture는 자동 제품 확정 근거가 아니라 provider contract 평가용입니다.
