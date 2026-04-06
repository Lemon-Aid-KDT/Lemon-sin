# Changelog

## v5.6 (2026-04-06) — AI 언어 선택 + IGES 지원 개선

### Added
- **AI 응답 언어 선택**: Settings에 English / 한국어 / Both 3버튼 추가
  - localStorage 영속화 (`cad_language_pref`)
  - QAPanel: `buildDescriptionPrompt()` + `buildQALanguageSuffix()` 동적 프롬프트 생성
  - Description + Q&A 모두 선택된 언어로 출력
- **IGES 2D 와이어프레임 감지**: 3D 뷰어에서 FACE 없는 2D IGES 파일 업로드 시 명확한 안내 메시지
  - "DXF 뷰어에서 2D 도면으로 확인하세요" 가이드 제공

### Fixed
- IGES → STL 변환 로직 개선: `BRepMesh_IncrementalMesh` 추가 + CadQuery `Shape.exportStl()` fallback
- 3D 뷰어 에러 메시지: 에러 유형별 분기 (2D 와이어프레임 / CadQuery 미설치 / 일반 오류)
- 웹 버전 표기: TopNav, Settings, UserPanel 모두 v5.6으로 통일

---

## v5.5.3 (2026-04-06) — UX 개선 + 기능 강화

### Fixed
- Dashboard 모델 표시: stats refetch 10초 간격으로 변경, 모델 변경 즉시 반영
- 검색 카테고리 단독 검색: 텍스트 없이 카테고리만 선택해도 검색 가능
- DXF Diff 결과 설명 빈약: 일치율 %, 3개 통계 카드, 해석 가이드(한/영), 레이어 차이/요약 상세 표시

### Added
- 3D 뷰어 확대/축소 버튼: 좌상단 +/- 오버레이 (ZoomIn/ZoomOut/Reset)
- 도면 등록 파이프라인 UX: 단계별 진행 시뮬레이션 + 완료 후 썸네일 미리보기

---

## v5.5.2 (2026-04-06) — 모델 변경 + 검색 썸네일 수정

### Fixed
- Settings 모델 변경 실패: 백엔드 StatsResponse에 `ollama_model` + `ollama_healthy` 필드 추가
- 3D 뷰어 자동 회전: `autoRotate={false}`로 변경
- 검색 결과 NO PREVIEW: 이미지/DXF 검색 API 응답 타입 매핑 (`SearchResult.drawing_id` → `UnifiedSearchResult.record_id`)

---

## v5.5.1 (2026-04-06) — Hotfix 5건

### Fixed
- Settings 수동 모델 선택: Ollama 모델 드롭다운 + Apply 버튼 + CAD VLM 모델 필터링
- 검색 key 에러: key에 index fallback, channelScores null safety, ResultCard placeholder
- 분석 DXF 흰색 배경: `dxf-invert` CSS + `dxf-svg-container` SVG 스트로크 반전 (다크/라이트 분리)
- DXF/3D 뷰어 초기화 버튼: Clear File 버튼 + blob URL 해제
- 3D 뷰어 STP 에러: STL은 blob URL(STLLoader), STP/IGES는 백엔드 vertices/normals → BufferGeometry

---

## v5.5 (2026-04-06) — React 프론트엔드 + 다크/라이트 모드

### Added — React (Next.js 16 + React 19)
- **다크/라이트 모드**: `next-themes` + CSS 변수 분리, 전체 컴포넌트 하드코딩 색상 수정 (20+ 파일)
- **검색 업로드**: SearchBar에 이미지/DXF 파일 업로드 기능 연결 (hidden input + useMutation)
- **분석 DXF/CAD 표시**: DXF→SVG 변환, STP/STEP/IGES→메시 정보 표시, Clear Drawing 초기화
- **3D 뷰어**: react-three-fiber + drei + STLLoader/BufferGeometry, Dynamic import(ssr:false)
- **Settings 패널**: 테마 토글 + LLM 모델 드롭다운 + 검색 가중치/YOLO 임계값 표시
- **User 패널**: 표시 이름(localStorage), 시스템 정보 요약
- **Tools 카테고리 드롭다운**: DrawingSelector 재사용 컴포넌트 (캐스케이딩 + 수동 입력 토글)
- **DXF Diff 결과 보강**: 일치율 %, 해석 가이드, 레이어 차이, 요약 상세

### Changed — Backend
- `_auto_select_ollama_model()`: Gemma 4 + Qwen3.5 선호 순위 기반 자동 선택, Ollama 설치 모델 감지
- `StatsResponse`: `ollama_model`, `ollama_healthy` 필드 추가
- `GET /stats`: 현재 활성 모델명 반환

### New Files (React)
- `web/src/components/viewer/STLViewer3D.tsx`
- `web/src/components/tools/DrawingSelector.tsx`
- `web/src/components/settings/SettingsPanel.tsx`
- `web/src/components/settings/UserPanel.tsx`

### Dependencies
- `next-themes`, `@react-three/fiber`, `@react-three/drei`, `three`, `@types/three`

---

## v5.4 (2026-03-31) — 코어 아키텍처 통합 + Multi-CAD + UI/UX 리디자인

### Phase 1: Core Architecture Integration

#### Added
- `core/models.py`: 통합 DTO/Enum 정의 (ExtractedFacts, SearchQuery, UnifiedSearchResult, CompareInput, RenderResult, AnalysisResult + 4 Enum)
- `core/cad_router.py`: Universal CAD Router — `ensure_processable()` 단일 진입점, 8포맷 지원
- `core/renderer.py`: Universal Renderer — 3모드 (thumbnail/full/interactive), hashlib.md5 캐시
- `core/search_engine.py`: Unified Search Engine — 4채널 (text/image/gnn/part_number) 가중 합산
- `core/vlm_orchestrator.py`: VLM Orchestrator — LLM 4작업 통합, ExtractedFacts→AnalysisContext 자동 변환
- `core/comparison_engine.py`: Comparison Engine — 4모드 비교 (DXF구조/치수/시각SSIM/메타데이터)
- `pipeline.py`: lazy property 4개 (search_engine, vlm_orchestrator, comparison_engine, renderer)
- API: `POST /api/v1/drawings/search/unified` + `UnifiedSearchRequest`/`UnifiedSearchResultResponse`

### Phase 2: Additional Features

#### Added
- `scripts/augment_real_drawings.py`: 실제 도면 이미지 증강 (13장 → 208장, albumentations 5 combo)
- Multi-CAD 핸들러: DWG(ODA), STEP/STP(CadQuery), IGES(OCP), STL(numpy-stl)
- 비지원 포맷 안내: CATIA/NX/SolidWorks/Inventor 등 9개 확장자 → STEP 내보내기 안내
- `ALLOWED_CAD_EXTENSIONS`: .dwg/.stp/.step/.igs/.iges/.stl

### Phase 3: UI/UX Redesign — Engineering Terminal

#### Added
- `config/design_tokens.py`: 디자인 토큰 (16색 7-layer surface, Space Grotesk + Inter)
- `app/styles.py`: 글로벌 CSS 350줄 (TopNav 64px, 블루프린트 그리드, 유리 패널, 레거시 마이그레이션 포함)
- `app/sidebar.py`: Engineering Terminal 사이드바 (v5.4.0-PRO)
- `app/ui_helpers.py`: 공유 UI 헬퍼 12개 + SVG 아이콘 35개
- `app/pages/`: 7개 페이지 모듈 (pg_dashboard ~ pg_tools)
- `app/components/`: 6개 컴포넌트 (kpi_card, result_card, activity_table, ollama_status, processing_queue, drawing_viewer)
- `core/ko_en_dict.py`: `get_expansions()` 추가 (시맨틱 확장 뱃지 UI용)

#### Changed
- **Dashboard**: KPI 4-card + Ollama 상태 패널 + 최근 활동 테이블
- **Search**: 통합 검색 엔진 연결, 3열 카드 그리드, 시맨틱 확장 뱃지, 파일타입 확장 (STEP/STL)
- **Analysis**: 6:4 분할 (Drawing Viewer + AI 사이드바) + 하단 Q&A 패널
- **Registration**: 12종 업로더, CAD Router, processing_queue 2-phase, 배치 확장
- `main()`: 딕셔너리 기반 pages 모듈 라우팅
- `.streamlit/config.toml`: #5eb4ff / #0e0e0e / showSidebarNavigation=false

#### Removed
- 레거시 visionOS CSS 457줄 → styles.py 통합 (`streamlit_app.py` 3,457→2,993줄)

### Tests
- 7개 테스트 파일, 총 121건 추가 → **724 → 845 passed**

---

## v5.3 (2026-03-25) — DXF 검색 정확도 + 치수 비교 UX

### Added
- `core/dxf_reranker.py`: DXF 구조 검색 후처리 리랭커 (엔티티 분포 코사인 유사도 + 개수 비율 + 종횡비 보정)
- 치수 비교: 좌/우 독립 카테고리 필터 드롭박스
- 치수 비교: 양쪽 도면 이미지 나란히 표시 (DXF 자동 렌더링 포함)
- `_show_record_thumbnail()`: 공통 레코드 썸네일 헬퍼 함수

### Changed
- `search_by_dxf()`: 오버샘플 top_k×3→5, 리랭커 통합으로 오탐 감소
- 치수 비교 UI: 단일 selectbox → 카테고리+도면 2단계 선택

### Tests
- `test_v53_dxf_reranker.py`: 14건 추가 → **724 passed**

---

## v5.2 (2026-03-25) — 도구/검색 UI 개선

### Added
- BOM 추출: 카테고리별 도면 선택 드롭박스
- DXF 비교: 양쪽 DXF 렌더링 이미지 나란히 표시
- 검색: 파일 형식 필터 (PNG/JPG/DXF) 멀티셀렉트
- 이미지 검색: DXF 업로드 지원 (자동 PNG 변환)
- DXF 구조 검색: 업로드 DXF 미리보기 + 메타데이터 패널

---

## v5.1 (2026-03-25) — 버그 수정 + 검색/분석 품질 개선

### Fixed
- BOM 추출: `self._llm._base_url` → `self._llm.base_url` (속성명 오류)
- DXF 비교: `result.matched_count` → `len(result.matched)` (속성명 오류)
- DXF 검색 결과 이미지 미표시 → `_render_dxf_thumbnail()` PNG 폴백

### Added
- `core/ko_en_dict.py`: 한/영 기계부품 동의어 사전 (140+ 단일어, 20+ 복합어)
- `core/category_prompts.py`: 15개 카테고리별 LLM 특화 프롬프트 + YOLO 교정 지시문
- DXF 도면 분석 지원: DXF → PNG 렌더링 + 메타데이터 추출 → LLM 프롬프트 주입
- `search_by_text()`: 한글 쿼리 자동 확장 (한/영 동의어) 통합

### Tests
- `test_v51_features.py`: 22건 추가 (ko_en_dict 10 + category_prompts 7 + YOLO correction 5)

---

## v5.0 (2026-03-25) — FastAPI REST API + Docker Compose

### Added
- **FastAPI 라우터**: drawings, analysis, tools, feedback, health, stats (6개)
- **REST API 25+ 엔드포인트**: 등록, 검색 4종, 분석, BOM, 치수비교, DXF비교, SSE 스트리밍
- **API Client**: `APIClient` 클래스 (Streamlit → FastAPI HTTP 호출)
- **Docker Compose**: `cad-api(8000)` + `cad-ui(8501)` + `cad-chromadb(8100)` 3-컨테이너
- `run_api.py`: FastAPI 서버 진입점
- `docker-start.sh`: 빌드/시작/중지/리셋 스크립트
- **Pydantic 스키마**: 요청/응답 모델 타입 안전성
- **Rate Limiter**: IP 기반 분당 60 요청 제한
- **Dependency Injection**: `get_pipeline()`, `get_feedback_store()` DI 패턴

### Changed
- Streamlit: 직접 pipeline 호출 → `is_api_mode()` 분기로 API/로컬 자동 전환

### Tests
- `test_api_drawings.py`: 22건 (등록/검색/CRUD)
- `test_api_analysis.py`: 15건 (설명/Q&A/분류/스트리밍)
- `test_api_tools.py`: 22건 (통계/모델/치수/BOM/DXF/버전/피드백)
- `test_api_client.py`: 18건 (APIClient 단위 테스트)
- Rate limit store 테스트 격리 (`_rate_limit_store.clear()`)
- 총 412 → **688 passed**

---

## v4.0 (2026-03-19) — Phase N: ML 스택 대규모 업그레이드

### Added
- YOLO26 호환 + Qwen3.5 RAM 자동 선택 (48GB→27b, 16GB→9b, <16GB→4b)
- OpenCLIP ViT-L/14 (512d→768d) + ChromaDB image 재생성
- GNN DXF 구조 검색: DXFGraphBuilder + GINEncoder (R@1=0.614, R@5=0.765)
- ChromaDB 3채널 하이브리드 검색 (Image 0.1 + Text 0.6 + GNN 0.3)
- DXF 네이티브 지원: DXFRenderer + DXF 업로더 + DXF 구조 검색 탭
- **412 tests passed**
