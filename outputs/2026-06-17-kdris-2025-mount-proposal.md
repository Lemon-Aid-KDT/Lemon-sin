# KDRIs 2025 데이터 마운트 제안 (Item ③) — 2026-06-17

> 상태: **제안서만 / 미적용**. `docker-compose.yml`은 사용자 foreign WIP(미커밋 flip 편집 동거)라 직접 수정하지 않음. 아래 패치를 사용자가 직접 적용.

## 현재 상태 (실측)
- `GET /api/v1/supplements/recommendations/latest` → **HTTP 200 정상**. (과거 "상호작용 카드 500 = KDRIs 누락" 메모는 **stale**.)
- KDRIs는 번들된 **2020-sample** 데이터셋으로 동작 중.
  - config 기본값(`backend/Nutrition-backend/src/config.py`): `kdris_data_version="2020-sample"`, `allow_sample_kdris=True`, `kdris_data_path=None`, `kdris_manifest_path=None`.
  - 컨테이너에 `KDRIS_*` env 없음 → 위 기본값 사용.
- 따라서 이 변경은 **"500 수정"이 아니라 샘플 → 공식 2025 KDRIs 업그레이드**(프로덕션 준비)임.

## 데이터 위치 (확인됨)
- `data/nutrition_reference/kdris/kdris_2025.csv`
- `data/nutrition_reference/kdris/kdris_source_manifest.json`
- ⚠️ repo 루트 `data/` 는 build context(`./backend`) **밖** → Dockerfile COPY 불가 → **볼륨 마운트**로 주입.

## 패치 (`docker-compose.yml` 의 `backend` 서비스)
```yaml
  backend:
    volumes:
      - lemon-aid-paddle-cache:/home/lemon/.paddlex
      - lemon-aid-hf-cache:/home/lemon/.cache/huggingface
      - ./data/nutrition_reference/kdris:/app/data/kdris:ro            # 추가
    environment:
      # ...기존 env...
      KDRIS_DATA_VERSION: ${KDRIS_DATA_VERSION:-2025}                                          # 추가
      KDRIS_DATA_PATH: ${KDRIS_DATA_PATH:-/app/data/kdris/kdris_2025.csv}                      # 추가
      KDRIS_MANIFEST_PATH: ${KDRIS_MANIFEST_PATH:-/app/data/kdris/kdris_source_manifest.json}  # 추가
      ALLOW_SAMPLE_KDRIS: ${ALLOW_SAMPLE_KDRIS:-false}    # 추가(선택; 2025 정상 로드 확인 후에만 false)
```

## 적용 절차 (재빌드 불필요 — env+볼륨만)
1. 위 패치 적용.
2. `docker compose up -d --no-deps backend` 로 컨테이너 recreate (이미지 재빌드 X).
3. 검증: `curl -s http://127.0.0.1:8000/api/v1/supplements/recommendations/latest | python3 -c "import sys,json;print(json.load(sys.stdin)['reference_version'])"` → `2020-sample` 이 아닌 **`2025` 계열**로 바뀌는지 확인.
4. 2025가 정상 로드되는 것을 확인한 뒤에만 `ALLOW_SAMPLE_KDRIS=false` 유지 (로드 실패 시 fail-fast 하므로).

## 롤백
- 추가한 volume/env 3~4줄 제거 후 `docker compose up -d --no-deps backend` recreate → 다시 2020-sample 로 복귀.

## 참고
- Items ①(실천 리스트 한국어화)·②(당뇨 자동로드)는 2026-06-17 재빌드로 **이미 라이브 배포·검증 완료**. ③만 본 제안서로 남김.
