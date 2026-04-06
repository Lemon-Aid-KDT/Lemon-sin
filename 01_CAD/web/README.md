# CAD Vision — React Frontend (v5.6)

Next.js 16 + React 19 + Tailwind CSS v4 기반 CAD Vision 웹 프론트엔드.

## 기술 스택

| 기술 | 버전 | 용도 |
|------|------|------|
| Next.js | 16.2.1 | App Router, Turbopack |
| React | 19.2.4 | UI 프레임워크 |
| Tailwind CSS | v4 | `@theme inline` CSS 변수 기반 테마 |
| TanStack Query | v5.96 | 서버 상태 관리 + 캐싱 |
| next-themes | - | 다크/라이트 모드 (SSR-safe) |
| react-three-fiber | - | 3D 뷰어 (STL/STEP/IGES) |
| lucide-react | - | 아이콘 |
| TypeScript | 5 | 타입 안전성 |

## 페이지 구성

| 경로 | 페이지 | 설명 |
|------|--------|------|
| `/` | Dashboard | KPI 카드, 카테고리 차트, Ollama 상태, 도면 탐색기 |
| `/register` | Registration | 도면 업로드 + 파이프라인 단계별 진행 + 썸네일 미리보기 |
| `/search` | Search | 텍스트/이미지/DXF 검색 + 카테고리 필터 + 3열 결과 그리드 |
| `/analysis` | Analysis | 6:4 뷰어+사이드바 + 하단 Technical Assistant (AI 설명+Q&A) |
| `/viewer/dxf` | DXF Viewer | SVG 뷰어 + 레이어 토글 + 엔티티 통계 |
| `/viewer/stl` | 3D Viewer | Three.js WebGL + 줌 버튼 + 와이어프레임 + STP/IGES 지원 |
| `/tools` | Tools | BOM 추출, 치수 비교, DXF Diff, 버전 이력, 피드백 |

## 주요 기능

- **다크/라이트 모드**: Settings 패널에서 전환, `next-themes` + CSS 변수
- **LLM 모델 선택**: Ollama 설치 모델 중 CAD VLM 모델만 필터링 + 수동 전환
- **3D 뷰어**: STL(STLLoader), STP/IGES(백엔드 변환→BufferGeometry)
- **DXF 가시성**: 다크 모드에서 SVG 스트로크 자동 반전
- **카테고리 드롭다운**: Tools에서 카테고리→도면 캐스케이딩 선택

## 실행

```bash
npm install
npm run dev       # http://localhost:3000
```

백엔드 API가 `http://localhost:8000/api/v1`에서 실행 중이어야 합니다.

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` | FastAPI 백엔드 URL |
