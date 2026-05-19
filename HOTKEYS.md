# Lemon Aid 단축키 / 사용법 치트시트

> 자주 까먹는 명령어 모음. 한 화면에 다 보이게 압축.

---

## 🚀 매일 쓰는 단축키 (외울 거 5개)

| 상황 | 단축키 / 명령 |
|---|---|
| **출근 — 풀스택 다 켜기** | `Ctrl+Shift+B` (VS Code) |
| **퇴근 — Docker 정리** | `Ctrl+Shift+P` → `Tasks: Run Task` → `🍋 풀스택 정리` |
| **모바일 코드 수정 후 반영** | 모바일 터미널에서 `r` (Hot reload) |
| **모바일 큰 변경 후 반영** | 모바일 터미널에서 `R` (Hot restart) |
| **모바일 / 백엔드 종료** | 각 터미널에서 `Ctrl+C` |

---

## 🍋 풀스택 시작 — 3가지 방법

### 1. VS Code 단축키 (가장 빠름)
```
Ctrl+Shift+B
```

### 2. 바탕화면 더블클릭
`start.bat` 더블클릭 (탐색기 또는 바탕화면 바로가기)

### 3. PowerShell
```powershell
cd C:\Claude_Projects\lemon_healthcare\Lemon_Aid
.\start.ps1
```

→ 자동으로 실행되는 것:
- Docker (Postgres + Redis) 백그라운드
- Backend (uvicorn) 새 창 → `http://localhost:8000`
- Mobile (Flutter + 키 자동 주입) 새 창 → 에뮬레이터에 빌드

---

## 🛑 종료 방법

### 풀스택 정리 (Docker)
```
Ctrl+Shift+P → Tasks: Run Task → 🍋 풀스택 정리
```
또는 `stop.bat` 더블클릭.

### Backend / Mobile 창
각 창에서 **`Ctrl+C`** 한 번 (안전 종료).

---

## 📦 부분만 시작 (가끔 필요)

| 작업 | 방법 |
|---|---|
| Backend만 재시작 | `Ctrl+Shift+P` → `Tasks: Run Task` → `🍋 Backend 만 시작` |
| Mobile만 재시작 | `Ctrl+Shift+P` → `Tasks: Run Task` → `🍋 Mobile 만 시작` |
| Docker만 재시작 | PowerShell: `docker compose up -d` (프로젝트 루트에서) |

---

## 🐛 모바일 디버거 (브레이크포인트)

VS Code 에서 `mobile/lib/main.dart` 열고:
```
F5
```
→ "Flutter (debug, 에뮬레이터)" 자동 실행, 디버거 attach.

---

## 🔑 환경변수 (한 번 등록하면 계속 사용)

PowerShell:
```powershell
# 카카오 키 등록
[System.Environment]::SetEnvironmentVariable("KAKAO_NATIVE_APP_KEY", "여기에키", "User")

# 구글 Web Client ID 등록
[System.Environment]::SetEnvironmentVariable("GOOGLE_SERVER_CLIENT_ID", "여기에ID", "User")

# 백엔드 API URL (선택 — 안 줘도 자동: Android 에뮬레이터 10.0.2.2, 기타 localhost)
[System.Environment]::SetEnvironmentVariable("LEMON_API_BASE_URL", "http://10.0.2.2:8000", "User")
```

확인:
```powershell
[System.Environment]::GetEnvironmentVariable("KAKAO_NATIVE_APP_KEY", "User")
[System.Environment]::GetEnvironmentVariable("GOOGLE_SERVER_CLIENT_ID", "User")
```

⚠️ **환경변수 등록 후 VS Code 완전히 닫고 재시작** — 새 세션부터 반영됨.

---

## 🧪 백엔드 테스트 (Swagger)

브라우저:
```
http://localhost:8000/docs
```
- POST /api/v1/auth/signup
- POST /api/v1/auth/login
- POST /api/v1/auth/email/send-code
- POST /api/v1/auth/email/verify-code
- POST /api/v1/auth/kakao
- POST /api/v1/auth/google
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout

서버 살아있는지 빠르게:
```powershell
curl http://localhost:8000/health
```

---

## 🐳 Docker 명령어

```powershell
# 컨테이너 상태
docker ps --filter "name=lemon_aid"

# 컨테이너 로그 (Postgres)
docker logs lemon_aid_db --tail 50

# 컨테이너 로그 (Redis)
docker logs lemon_aid_redis --tail 50

# DB 직접 접속 (psql)
docker exec -it lemon_aid_db psql -U lemon -d lemon_aid

# Redis 직접 접속
docker exec -it lemon_aid_redis redis-cli
```

DB 안에서 자주 쓰는 SQL:
```sql
-- 사용자 목록
SELECT id, email, display_name, kakao_id, google_id, email_verified_at FROM users;

-- 이메일 인증 코드 (디버그용 — 코드 안 받았을 때)
SELECT email, code, purpose, created_at, consumed_at FROM email_verifications ORDER BY created_at DESC LIMIT 5;

-- 종료 (psql 안에서)
\q
```

---

## 🌳 Git 자주 쓰는 명령

```powershell
# 현재 브랜치 / 변경 파일
git status

# 최근 커밋 5개
git log --oneline -5

# 작업 브랜치 (taedong-design) 푸시
git push origin taedong-design

# 원격 최신 가져오기 (다른 사람 커밋)
git fetch origin

# 원격 다른 브랜치 코드만 받아오기 (백엔드 폴더만)
git checkout origin/sunghoon-database -- backend/
```

⚠️ **메인 브랜치 푸시 / 머지 절대 금지.** 항상 `taedong-design` 또는 다른 작업 브랜치.

---

## 🔧 자주 막히는 거 — 빠른 해결

### "키 설정 후 사용할 수 있어요" 안내 (모바일)
- 원인: `flutter run` 으로 그냥 띄움. dart-define 안 들어감.
- 해결: 모바일 창 `q` 종료 → `Ctrl+Shift+P` → `🍋 Mobile 만 시작`

### Backend 500 에러
- 원인: Docker (Postgres) 안 떠있음.
- 해결: PowerShell에서 `docker ps` 확인. 비었으면 `docker compose up -d`

### 메일 안 옴 (Resend)
- 원인 1: Resend 도메인 검증 미완료 → Resend 콘솔 Domains 에서 `Verified` 확인
- 원인 2: 본인 가입 이메일 외엔 발송 못 함 (도메인 인증 안 했을 때)
- 임시: 백엔드 터미널 로그에 `[email] ... 인증 코드: 123456` 출력 → 그 코드 입력

### "git index.lock" 에러
- 원인: 직전 git 명령이 비정상 종료됨
- 해결: PowerShell에서 `Remove-Item C:\Claude_Projects\lemon_healthcare\Lemon_Aid\.git\index.lock`

### OneDrive 빌드 잠금 (`compressDebugAssets failed`)
- 원인: OneDrive가 빌드 폴더 잠금
- 해결: 시스템 트레이 OneDrive → 동기화 일시 중지 2시간 → `flutter clean` → 재빌드
- 영구 해결: OneDrive 자동 시작 끄기 (이미 처리됨)

---

## 📁 주요 경로 (복붙용)

```
C:\Claude_Projects\lemon_healthcare\Lemon_Aid\           ← 루트
├── start.ps1 / start.bat                               ← 풀스택 시작
├── stop.ps1  / stop.bat                                ← Docker 정리
├── docker-compose.yml                                  ← DB / Redis 정의
├── .vscode/
│   ├── tasks.json                                      ← Ctrl+Shift+B 등
│   └── extensions.json
├── backend/
│   ├── .env                                            ← 시크릿 (.gitignore)
│   ├── .env.example                                    ← 키 템플릿
│   ├── src/                                            ← 백엔드 코드
│   └── alembic/versions/                               ← DB 마이그레이션
└── mobile/
    ├── .env.example                                    ← 모바일 키 가이드
    ├── .vscode/launch.json                             ← F5 디버거 설정
    ├── scripts/run-dev.ps1                             ← Mobile 단독 실행
    ├── lib/                                            ← Flutter 코드
    └── android/app/src/main/                           ← Android 설정
```

---

## 🆘 진짜 막혔을 때

1. 백엔드 / 모바일 / Docker 다 끄기 (`stop.bat`)
2. PC 재부팅 (가끔 정말 효과 있음)
3. `start.bat` 다시
4. 그래도 안 되면 — 정확한 에러 메시지 + 어느 단계에서 막혔는지 정리해서 다음 세션에 가져오기

---

_마지막 업데이트: 풀스택 자동화 셋업 완료 시점_
