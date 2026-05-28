# CVAT Docker 설치 및 YOLO 라벨링 가이드

> 목적: 크롤링 수집 이미지에 YOLO bounding box 라벨링을 팀 협업으로 진행하기 위한 CVAT 로컬 서버 구축
>
> 환경: Windows 11, PC2 (RTX 4060 Laptop 8GB)

---

## 0. 사전 요구사항 확인

- Windows 11 (WSL2 활성화 필요)
- RAM 16GB 이상 권장 (CVAT + DB + Redis 합산 ~4GB)
- 포트 8080 사용 가능 여부 확인

---

## 1. Docker Desktop 설치

### 1-1. WSL2 활성화 (관리자 PowerShell)

```powershell
wsl --install
```

재부팅 후 WSL2가 기본값으로 설정됐는지 확인:

```powershell
wsl --set-default-version 2
wsl --status
```

### 1-2. Docker Desktop 다운로드 및 설치

1. [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/) 접속
2. **Windows용 Docker Desktop** 다운로드 (AMD64)
3. 설치 옵션: **Use WSL2 instead of Hyper-V** 체크
4. 설치 완료 후 재시작
5. 설치 확인:

```powershell
docker --version
docker compose version
```

예상 출력:
```
Docker version 27.x.x, build ...
Docker Compose version v2.x.x
```

---

## 2. CVAT 설치

### 2-1. CVAT 저장소 클론

```powershell
cd C:\
git clone https://github.com/cvat-ai/cvat.git
cd cvat
```

### 2-2. CVAT 실행

```powershell
docker compose up -d
```

최초 실행 시 이미지 다운로드로 5~15분 소요. 완료 확인:

```powershell
docker compose ps
```

모든 서비스가 `running` 상태여야 함:
- cvat_server
- cvat_worker_default
- cvat_worker_export
- cvat_worker_import
- cvat_db (PostgreSQL)
- cvat_redis
- cvat_proxy (nginx)

### 2-3. 관리자 계정 생성

```powershell
docker exec -it cvat_server python manage.py createsuperuser
```

프롬프트에서 username, email, password 입력.

### 2-4. 브라우저 접속

```
http://localhost:8080
```

생성한 관리자 계정으로 로그인.

---

## 3. YOLO 라벨링 프로젝트 설정

### 3-1. 프로젝트 생성

1. 상단 메뉴 **Projects** → **Create new project**
2. Project name: `aihub-yolo-50-crawl-labeling`
3. **Labels** 탭 → **From file** 선택

### 3-2. 라벨 파일 준비 (50개 클래스)

아래 내용을 `cvat_labels.json`으로 저장 후 업로드:

```json
[
  {"name": "salad"},
  {"name": "mixed-rice-bowl"},
  {"name": "rice-bowl"},
  {"name": "fried-rice"},
  {"name": "rice-soup"},
  {"name": "rice-porridge"},
  {"name": "seaweed-rice-roll"},
  {"name": "spicy-rice-cakes"},
  {"name": "dumplings"},
  {"name": "fish-cake"},
  {"name": "fried-food-platter"},
  {"name": "savory-pancake"},
  {"name": "korean-blood-sausage"},
  {"name": "takoyaki"},
  {"name": "soup"},
  {"name": "stew"},
  {"name": "hot-pot"},
  {"name": "noodle-soup"},
  {"name": "cold-noodles"},
  {"name": "spicy-mixed-noodles"},
  {"name": "ramen"},
  {"name": "black-bean-noodles"},
  {"name": "spicy-seafood-noodles"},
  {"name": "fried-chicken"},
  {"name": "pork-cutlet"},
  {"name": "grilled-pork-belly"},
  {"name": "grilled-beef"},
  {"name": "barbecue-ribs"},
  {"name": "bulgogi"},
  {"name": "stir-fried-pork"},
  {"name": "braised-chicken"},
  {"name": "chicken-galbi"},
  {"name": "braised-pork-hock"},
  {"name": "grilled-fish"},
  {"name": "raw-fish"},
  {"name": "sushi"},
  {"name": "seafood-stew"},
  {"name": "shrimp-dish"},
  {"name": "squid-dish"},
  {"name": "sweet-and-sour-pork"},
  {"name": "mala-hot-pot"},
  {"name": "dim-sum"},
  {"name": "udon"},
  {"name": "pasta"},
  {"name": "pizza"},
  {"name": "hamburger"},
  {"name": "sandwich"},
  {"name": "curry"},
  {"name": "bread"},
  {"name": "cake"}
]
```

### 3-3. Task 생성 (이미지 업로드)

1. 프로젝트 내 **Create new task**
2. Task name 예: `crawl-batch-01-mala-hot-pot`
3. **Select files** → 크롤링 이미지 업로드 (jpg/png)
4. **Submit & Open**

### 3-4. 팀원 공유

1. CVAT이 실행 중인 PC의 로컬 IP 확인:

```powershell
ipconfig | findstr "IPv4"
```

2. 같은 네트워크 팀원은 `http://<PC-IP>:8080` 으로 접속
3. CVAT 관리자 페이지 → **Admin** → **Users** → 팀원 계정 생성

---

## 4. AI-assisted 자동 라벨링 (선택)

기존 exp03 best.pt 모델로 pre-annotation을 걸면 수작업을 크게 줄일 수 있다.

### 4-1. Nuclio 함수 서버 활성화

```powershell
# cvat 폴더에서
docker compose -f docker-compose.yml -f components/serverless/docker-compose.serverless.yml up -d
```

### 4-2. Nuclio 대시보드 접속

```
http://localhost:8070
```

### 4-3. 커스텀 모델 배포

CVAT 공식 docs의 [Custom detector](https://docs.cvat.ai/docs/manual/advanced/serverless-tutorial/) 참고.
exp03 best.pt를 Ultralytics YOLO detector로 래핑해 Nuclio에 배포하면
**AI Tools → Detectors** 탭에서 자동 라벨링 실행 가능.

---

## 5. YOLO 포맷 Export

라벨링 완료 후:

1. Task 선택 → **Actions** → **Export task dataset**
2. Format: **YOLO 1.1** 선택
3. ZIP 다운로드 → `images/` + `labels/` 구조로 압축됨
4. 압축 해제 후 `data/food_images/aihub_yolo_50_crawl/` 아래 배치

---

## 6. CVAT 종료 / 재시작

```powershell
# 종료
docker compose down

# 재시작 (데이터 유지)
docker compose up -d

# 데이터까지 완전 삭제 (주의)
docker compose down -v
```

---

## 참고

- CVAT 공식 문서: https://docs.cvat.ai/
- 크롤링 우선 타겟 클래스: `docs/superpowers/plans/2026-05-28-class-dataset-ap50-summary.csv`
  - 최우선: mala-hot-pot(270장), stir-fried-pork(240장), sweet-and-sour-pork(290장)
