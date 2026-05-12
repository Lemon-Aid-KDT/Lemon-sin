# 🍋 Lemon Aid — AI 헬스케어 / 건강관리 플랫폼

> **만성질환자의 병원 기록과 생활 데이터를 기억하는 AI 영양·복약 관리 Agent**

사진 한 장으로 끝나는 만성질환 관리 — 영양제·식단 촬영 → 4개 Agent 협력 → 5종 분석 자동 출력.
경북대학교 AI/빅데이터 전문가 양성 과정 — (주)레몬헬스케어 협업 프로젝트.

---

## 📖 시작하기 — 무엇부터 봐야 하나

### 1️⃣ 가이드 문서 열기

| 파일 | 어떻게 보나 | 추천 |
|------|------------|------|
| **[`guide.html`](./guide.html)** | 다운로드 후 브라우저로 열기 (사이드바 + 다크모드 + PDF) | ⭐ 가장 보기 편함 |
| **[`PROJECT_GUIDE.md`](./PROJECT_GUIDE.md)** | GitHub 웹·VS Code·Cursor 등에서 마크다운으로 보기 | 코딩 툴 컨텍스트용 |

두 파일은 **같은 마크다운 본문을 공유**합니다. 팀원이 PROJECT_GUIDE.md만 수정하면 guide.html에 자동 반영됩니다.

### 2️⃣ 처음이라면 이 순서로 읽기 (30분)

1. **표지 + 한 줄 요약** — 우리가 뭘 만드나
2. **§1 프로젝트 개요** — 페르소나·차별화 5가지·일정
3. **§3 핵심 기능** — 4 Agent + 응모권 UX
4. **§7 AI 스택** — Claude·OCR·Tool Use
5. **§13 파일 구조** — 전체 디렉터리 트리
6. **§16 GitHub 협업 규칙** — 브랜치·커밋·PR
7. **부록 A 🚀 지금 시작** — D1~D5 액션 카드

---

## 👥 팀

```
🍋 Team Lemon Aid (5명)

A. 프론트 리드     : Flutter 라우팅 · 토큰 · 화면 통합
B. UI/UX           : 만성질환자 친화 UI · 챗봇 · 응모권
C. AI 엔지니어     : Claude API · 4개 Agent · 의료법 검수
D. 백엔드          : FastAPI · 알고리즘 · DB · 인증
E. 데이터·도메인   : KDRIs · 식약처 · Kaggle · 의료자문위
```

각 팀원은 본인에게 맞는 바이브 코딩 툴(Claude Code, Codex, Cursor, Cline, Windsurf 등)을 자유롭게 사용합니다. 모든 툴이 `PROJECT_GUIDE.md`를 우선 참조합니다.

---

## 🚀 D1 즉시 시작

상세는 [`PROJECT_GUIDE.md` 부록 A](./PROJECT_GUIDE.md#부록-a-d1-즉시-시작-가이드--🚀-5명이-지금-바로-작업-시작) 참조.

```bash
# 1) 저장소 클론
git clone https://github.com/Lemon-Aid-KDT/Lemon-sin.git
cd Lemon-sin

# 2) PROJECT_GUIDE.md 읽기 (30분)

# 3) 본인 영역 D1 액션 (부록 A.9 참조)
git checkout -b feat/<영역>-setup
```

---

## 🤝 협업 규칙 (요약, 상세는 §16)

- 브랜치: `main` (배포) / `dev` (통합) / `feat/<영역>-<짧은이름>` (개인)
- 커밋: `[영역] 내용` 또는 Conventional Commits — 예: `feat(ai): 챗봇 Tool 추가`
- PR: 1명 이상 리뷰 + CI 통과 후 머지
- 매일 18시 스탠드업 10분
- 코드 변경 시 `PROJECT_GUIDE.md` 동기 업데이트
- `guide.html`은 `<script id="md-source">` 안의 마크다운만 수정 (HTML/CSS/JS 영역 X)

---

## ⚖️ 컴플라이언스

> ⚠️ 본 서비스는 진단·치료가 아닌 **웰니스 기반 건강관리 보조 서비스**입니다.
> 의사·약사·영양사의 전문적 진단이나 처방을 대체하지 않습니다.

상세: [`PROJECT_GUIDE.md` §19 컴플라이언스 & 안전선](./PROJECT_GUIDE.md#19-컴플라이언스--안전선)

---

## 📂 저장소 구조 (현재 단계)

```
lemon-aid/
├─ README.md                  # 이 문서
├─ PROJECT_GUIDE.md           # 단일 진실 (모든 바이브 코딩 툴 공통 참조)
├─ guide.html                 # 브라우저 뷰어 (다크모드, PDF, Mermaid)
├─ .github/                   # CI / CODEOWNERS / PR 템플릿
├─ data/                      # 루트 데이터 placeholder
├─ yeong-Vision-Nutrition/    # 실제 구현 루트
│  ├─ backend/                # FastAPI 구현
│  ├─ data/                   # KDRIs / MFDS / reference fixtures
│  ├─ docs/                   # 구현 문서와 이전 버전 산출물
│  └─ mobile/                 # 모바일 트랙
└─ .gitignore
```

---

발주처: **(주)레몬헬스케어** — https://www.lemonhealthcare.com
