# KDRIs 2025 데이터셋 적용 (Item ③) — 2026-06-17

> 상태: **✅ 적용 + 라이브 검증 완료** (로컬 docker 스택).
> 핵심 정정: KDRIs 2025 데이터는 **이미 이미지에 baked** 되어 있어 별도 볼륨 마운트가 불필요했음. 런타임 `KDRIS_DATA_VERSION=2025` 지정만으로 전환됨.

## 현재 상태 (실측)
- `GET /api/v1/supplements/recommendations/latest` → **HTTP 200**, `reference_version: 2025` (이전 `2020-sample`).
- 데이터셋 컨텍스트: `dataset_status=official_2025_approved`, `dataset_version=2025`, `source_manifest_version=2.0`. 참조 **1795행** 로드.

## 정정: 데이터는 이미 baked 됨 (마운트 불필요)
처음엔 "repo `data/` 가 build context(`./backend`) 밖이라 볼륨 마운트가 필요"로 판단했으나, 실제로는:
- 데이터가 build context **안**에 존재(커밋됨): `backend/Nutrition-backend/data/nutrition_reference/kdris/{kdris_2025.csv, kdris_source_manifest.json, kdris_metadata.json}`.
- `backend/Dockerfile` 이 이미 COPY: `COPY Nutrition-backend ./Nutrition-backend` (line 45) + `COPY Nutrition-backend/data/nutrition_reference ./data/nutrition_reference` (line 46).
- 런타임 `resolve_nutrition_reference_root()` (config.py) 가 컨테이너에서 baked 경로(`/app/Nutrition-backend/data/nutrition_reference/kdris`)를 자동 resolve.

→ 따라서 **버전만 2025로 지정**하면 baked 2025 데이터를 사용. 볼륨 마운트·경로 override·호스트 사본 전부 불필요.

## 적용 내용 (`docker-compose.yml` `backend` 서비스 environment — 로컬 ops, 미커밋)
```yaml
    environment:
      # ...기존 env...
      KDRIS_DATA_VERSION: "2025"
      ALLOW_SAMPLE_KDRIS: "false"
```
- **재빌드 불필요** — env만이라 `docker compose up -d --no-deps backend` recreate 로 적용.

## 검증 명령
```bash
docker exec -w /app/Nutrition-backend lemon-aid-backend-1 python -c \
  "from src.nutrition.kdris import load_kdris_references, get_kdris_dataset_context; \
   print(get_kdris_dataset_context()); print(len(load_kdris_references()))"
# {'dataset_status': 'official_2025_approved', 'dataset_version': '2025', 'source_manifest_version': '2.0'}
# 1795
curl -s http://127.0.0.1:8000/api/v1/supplements/recommendations/latest \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['reference_version'])"   # 2025
```

## 비고
- `docker-compose.yml`은 사용자 flip 편집(lemon_app DATABASE_URL 등)과 함께 **미커밋 로컬 ops 설정**. 위 KDRIs 2개 env 는 repo `.env`(`KDRIS_DATA_VERSION="2025"`, `ALLOW_SAMPLE_KDRIS="false"`)와 일치.
- Docker 컨테이너가 **커밋된 형태로** 기본 2025를 쓰게 하려면 정석은 `config.py` 기본값 `kdris_data_version` 을 `"2020-sample"`→`"2025"` 로 변경하는 것. 단 config.py 는 foreign WIP + 전 환경/테스트 영향이라 본 작업에서는 미변경(제품 결정 필요).
- (구버전 이력) 외장드라이브 공백경로 VirtioFS bind-mount 버그로 한때 `~/lemonaid-kdris` 사본을 마운트했으나, baked 데이터 사용으로 전환하며 마운트·사본 모두 제거함.
