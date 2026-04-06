"""
DrawingLLM — Streamlit 웹 UI

도면 업로드, 검색, 분석 기능을 제공하는 웹 인터페이스
실행: streamlit run app/streamlit_app.py
"""

import atexit
import glob
import sys
import re
import uuid
import tempfile
import time
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from loguru import logger
from PIL import Image

from core.pipeline import DrawingPipeline
from config.settings import settings


# ─────────────────────────────────────────────
# 로그 로테이션 설정
# ─────────────────────────────────────────────

def _setup_logging():
    """loguru 로그 로테이션 구성 (로그 파일 무한 팽창 방지)."""
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(log_path),
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression="gz",
        enqueue=True,  # thread-safe
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name}:{function}:{line} | {message}",
    )

_setup_logging()


# ─────────────────────────────────────────────
# 임시 파일 정리 유틸리티
# ─────────────────────────────────────────────

_TEMP_FILE_MAX_AGE_HOURS = 1  # 1시간 이상 된 임시 파일 자동 정리

def _cleanup_stale_temp_files():
    """오래된 DrawingLLM 임시 파일을 삭제한다 (세션 간 누수 방지)."""
    try:
        tmp_dir = Path(tempfile.gettempdir())
        cutoff = time.time() - (_TEMP_FILE_MAX_AGE_HOURS * 3600)
        patterns = ["drawingllm_search_*", "drawingllm_analyze_*"]
        removed = 0
        for pattern in patterns:
            for f in tmp_dir.glob(pattern):
                try:
                    if f.is_file() and f.stat().st_mtime < cutoff:
                        f.unlink()
                        removed += 1
                except OSError:
                    pass
        if removed:
            logger.info(f"오래된 임시 파일 {removed}개 정리 완료")
    except Exception as e:
        logger.debug(f"임시 파일 정리 중 오류 (무시): {e}")

# 앱 시작 시 오래된 임시 파일 정리
_cleanup_stale_temp_files()


# ─────────────────────────────────────────────
# 보안 유틸리티
# ─────────────────────────────────────────────

_ALLOWED_UPLOAD_DIR = Path("./data/sample_drawings").resolve()
_ALLOWED_BATCH_BASE = Path("./data").resolve()

def _sanitize_filename(filename: str) -> str:
    """파일명에서 경로 탐색 문자 및 위험 문자를 제거한다."""
    filename = filename.replace("/", "").replace("\\", "").replace("\x00", "")
    filename = filename.lstrip(".")
    filename = re.sub(r'[^\w\-.]', '_', filename)
    if not filename:
        filename = f"upload_{uuid.uuid4().hex[:8]}"
    return filename

def _validate_batch_path(path_str: str) -> Path | None:
    """배치 등록 경로가 허용된 데이터 디렉토리 내에 있는지 검증한다."""
    try:
        batch_path = Path(path_str).resolve()
        if not str(batch_path).startswith(str(_ALLOWED_BATCH_BASE)):
            return None
        if not batch_path.exists() or not batch_path.is_dir():
            return None
        return batch_path
    except (ValueError, OSError):
        return None


# ─────────────────────────────────────────────
# 파일 경로 해결 (호스트 ↔ Docker 호환)
# ─────────────────────────────────────────────

@st.cache_data(ttl=300)
def _build_filename_index() -> dict[str, str]:
    """upload_dir 아래의 파일명 → 실제 경로 인덱스를 구축한다 (캐싱 5분)."""
    index: dict[str, str] = {}
    base = Path(settings.upload_dir)
    if base.exists():
        for f in base.rglob("*"):
            if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".jpeg", ".pdf", ".tiff", ".tif"}:
                index[f.name] = str(f)
    return index


def _resolve_file_path(file_path: str | None) -> Path | None:
    """
    저장된 파일 경로를 현재 환경에서 접근 가능한 경로로 해결한다.

    전략 순서:
      1) 원본 경로 그대로 시도
      2) 경로 접두사 리맵 (DRAWING_PATH_REMAP_FROM → DRAWING_PATH_REMAP_TO)
      3) 파일명으로 upload_dir 아래에서 검색
    """
    if not file_path:
        return None

    # 1) 원본 경로
    p = Path(file_path)
    if p.exists():
        return p

    # 2) 경로 접두사 리맵
    remap_from = settings.drawing_path_remap_from
    remap_to = settings.drawing_path_remap_to
    if remap_from and remap_to and file_path.startswith(remap_from):
        remapped = Path(file_path.replace(remap_from, remap_to, 1))
        if remapped.exists():
            return remapped

    # 2b) drawing-datasets/staged → data/staged 리맵 (학습 데이터 경로 보정)
    if "/drawing-datasets/staged/" in file_path:
        # 로컬: drawing-datasets → data 치환
        alt = Path(file_path.replace("/drawing-datasets/staged/", "/data/staged/", 1))
        if alt.exists():
            return alt
        # Docker: data 디렉토리 기준으로 staged/ 하위 경로 검색
        staged_idx = file_path.index("/staged/")
        staged_rel = file_path[staged_idx + 1:]  # staged/Category/file.png
        data_dir = Path(settings.chroma_persist_dir).parent  # /app/data
        candidate = data_dir / staged_rel
        if candidate.exists():
            return candidate

    # 3) 파일명으로 upload_dir 하위에서 검색
    fname = p.name
    index = _build_filename_index()
    if fname in index:
        return Path(index[fname])

    return None


# ─────────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="CAD Vision — AI 도면 검색 시스템",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────
# 커스텀 CSS 테마 (프로덕션 그레이드)
# ─────────────────────────────────────────────

st.markdown("""
<style>
/* ═══════════════════════════════════════════
   CAD Vision — visionOS Liquid Glass Design
   Inspired by iOS/iPadOS 26 & Apple visionOS
   ═══════════════════════════════════════════ */

/* ── Global ── */
/* 아이콘 폰트(Material Symbols)를 보존하기 위해 * 에는 !important 를 사용하지 않음 */
* { font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', system-ui, sans-serif; }
/* 텍스트 컨테이너에만 !important 적용 (아이콘 span 제외) */
body, p, h1, h2, h3, h4, h5, h6, div, input, textarea, select, button, a, li, td, th,
label, summary, article, section, header, footer, nav, main, form, figcaption,
.stMarkdown, .stText, [data-testid="stMetric"], [data-testid="stExpander"] summary p {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', system-ui, sans-serif !important;
}
.block-container { padding-top: 2rem !important; }

/* 미세한 메시 그라디언트 배경 */
[data-testid="stAppViewContainer"] > section > div.block-container {
    background:
        radial-gradient(ellipse at 20% 0%, rgba(0, 122, 255, 0.04) 0%, transparent 50%),
        radial-gradient(ellipse at 80% 100%, rgba(100, 210, 255, 0.03) 0%, transparent 50%);
}

/* ── 사이드바: Liquid Glass ── */
section[data-testid="stSidebar"] {
    background: rgba(28, 28, 30, 0.78) !important;
    -webkit-backdrop-filter: blur(60px) saturate(180%);
    backdrop-filter: blur(60px) saturate(180%);
    border-right: 0.5px solid rgba(255, 255, 255, 0.10) !important;
}
section[data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }

/* 사이드바 라디오 — visionOS pill style */
section[data-testid="stSidebar"] [data-testid="stRadio"] label {
    padding: 11px 16px !important;
    border-radius: 14px !important;
    margin-bottom: 3px !important;
    transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94) !important;
    border: 1px solid transparent !important;
    position: relative !important;
}
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: rgba(255, 255, 255, 0.08) !important;
    border-color: rgba(255, 255, 255, 0.10) !important;
}

/* ═══════════════════════════════════════════
   메트릭 카드 — Glass Material
   ═══════════════════════════════════════════ */
div[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.06);
    -webkit-backdrop-filter: blur(40px) saturate(180%);
    backdrop-filter: blur(40px) saturate(180%);
    border: 0.5px solid rgba(255, 255, 255, 0.15);
    border-radius: 20px;
    padding: 20px 24px;
    box-shadow:
        0 2px 16px rgba(0, 0, 0, 0.15),
        inset 0 0.5px 0 rgba(255, 255, 255, 0.12);
    transition: transform 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94),
                border-color 0.3s, box-shadow 0.3s;
    position: relative;
    overflow: hidden;
}
div[data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 0.5px;
    background: linear-gradient(90deg,
        transparent 0%,
        rgba(255, 255, 255, 0.25) 30%,
        rgba(255, 255, 255, 0.25) 70%,
        transparent 100%);
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-2px) scale(1.01);
    border-color: rgba(255, 255, 255, 0.25);
    box-shadow:
        0 8px 32px rgba(0, 0, 0, 0.20),
        0 0 20px rgba(0, 122, 255, 0.06),
        inset 0 0.5px 0 rgba(255, 255, 255, 0.15);
}
div[data-testid="stMetric"] label {
    color: rgba(255, 255, 255, 0.50) !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    font-weight: 500 !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: rgba(255, 255, 255, 0.92) !important;
    font-size: 1.85rem !important;
    font-weight: 700 !important;
    background: linear-gradient(135deg, #64D2FF 0%, #0A84FF 50%, #5E5CE6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* ═══════════════════════════════════════════
   버튼 — visionOS Capsule Style
   ═══════════════════════════════════════════ */
.stButton > button {
    border-radius: 14px !important;
    font-weight: 600 !important;
    transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94) !important;
    letter-spacing: 0.01em !important;
}
.stButton > button[kind="primary"] {
    background: rgba(0, 122, 255, 0.85) !important;
    -webkit-backdrop-filter: blur(20px);
    backdrop-filter: blur(20px);
    border: 0.5px solid rgba(255, 255, 255, 0.20) !important;
    box-shadow: 0 2px 12px rgba(0, 122, 255, 0.30),
                inset 0 0.5px 0 rgba(255, 255, 255, 0.20) !important;
    padding: 0.55rem 1.6rem !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) scale(1.02) !important;
    box-shadow: 0 6px 24px rgba(0, 122, 255, 0.40),
                inset 0 0.5px 0 rgba(255, 255, 255, 0.25) !important;
    background: rgba(10, 132, 255, 0.95) !important;
}
.stButton > button[kind="secondary"] {
    border: 0.5px solid rgba(255, 255, 255, 0.15) !important;
    background: rgba(255, 255, 255, 0.06) !important;
    -webkit-backdrop-filter: blur(20px);
    backdrop-filter: blur(20px);
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(255, 255, 255, 0.12) !important;
    border-color: rgba(255, 255, 255, 0.25) !important;
}

/* ═══════════════════════════════════════════
   Expander — Glass Card
   ═══════════════════════════════════════════ */
[data-testid="stExpander"] {
    background: rgba(255, 255, 255, 0.04) !important;
    -webkit-backdrop-filter: blur(30px) saturate(150%);
    backdrop-filter: blur(30px) saturate(150%);
    border: 0.5px solid rgba(255, 255, 255, 0.10) !important;
    border-radius: 18px !important;
    margin-bottom: 8px !important;
    overflow: hidden !important;
    transition: border-color 0.3s, box-shadow 0.3s, background 0.3s !important;
}
[data-testid="stExpander"]:hover {
    border-color: rgba(255, 255, 255, 0.20) !important;
    background: rgba(255, 255, 255, 0.06) !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12),
                0 0 12px rgba(0, 122, 255, 0.04) !important;
}
[data-testid="stExpander"] summary {
    padding: 14px 18px !important;
}

/* ═══════════════════════════════════════════
   탭 — Liquid Glass Segmented Control
   ═══════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: rgba(255, 255, 255, 0.05);
    -webkit-backdrop-filter: blur(30px);
    backdrop-filter: blur(30px);
    border-radius: 16px;
    padding: 4px;
    border: 0.5px solid rgba(255, 255, 255, 0.10);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 13px !important;
    padding: 10px 24px !important;
    font-weight: 600 !important;
    color: rgba(255, 255, 255, 0.45) !important;
    background: transparent !important;
    transition: all 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94) !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: rgba(255, 255, 255, 0.70) !important;
    background: rgba(255, 255, 255, 0.05) !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: rgba(255, 255, 255, 0.12) !important;
    color: rgba(255, 255, 255, 0.92) !important;
    box-shadow: 0 1px 8px rgba(0, 0, 0, 0.12),
                inset 0 0.5px 0 rgba(255, 255, 255, 0.15) !important;
    -webkit-backdrop-filter: blur(20px);
    backdrop-filter: blur(20px);
}
.stTabs [data-baseweb="tab-highlight"] {
    background-color: transparent !important;
}

/* ═══════════════════════════════════════════
   Input / Select — Glass Fields
   ═══════════════════════════════════════════ */
.stTextInput > div > div > input,
.stSelectbox > div > div {
    border-radius: 14px !important;
    border-color: rgba(255, 255, 255, 0.12) !important;
    background: rgba(255, 255, 255, 0.05) !important;
    -webkit-backdrop-filter: blur(20px);
    backdrop-filter: blur(20px);
}
.stTextInput > div > div > input:focus {
    border-color: rgba(0, 122, 255, 0.60) !important;
    box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.12),
                0 0 16px rgba(0, 122, 255, 0.08) !important;
}

/* ═══════════════════════════════════════════
   파일 업로더 — Glass Drop Zone
   ═══════════════════════════════════════════ */
[data-testid="stFileUploader"] > section {
    border: 1.5px dashed rgba(255, 255, 255, 0.15) !important;
    border-radius: 20px !important;
    background: rgba(255, 255, 255, 0.03) !important;
    -webkit-backdrop-filter: blur(30px);
    backdrop-filter: blur(30px);
    padding: 2rem !important;
    transition: border-color 0.3s, background 0.3s !important;
}
[data-testid="stFileUploader"] > section:hover {
    border-color: rgba(0, 122, 255, 0.40) !important;
    background: rgba(0, 122, 255, 0.04) !important;
}

/* ═══════════════════════════════════════════
   유사도 점수 바 — Glass Bar
   ═══════════════════════════════════════════ */
.score-bar-bg {
    background: rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    height: 28px;
    overflow: hidden;
    border: 0.5px solid rgba(255, 255, 255, 0.10);
    -webkit-backdrop-filter: blur(20px);
    backdrop-filter: blur(20px);
}
.score-bar-fill {
    height: 100%;
    border-radius: 12px;
    display: flex;
    align-items: center;
    padding-left: 12px;
    color: white;
    font-size: 0.82rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    text-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

/* ═══════════════════════════════════════════
   페이지네이션
   ═══════════════════════════════════════════ */
.pagination-bar {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 12px 0;
    color: rgba(255, 255, 255, 0.40);
    font-size: 0.9rem;
}
.pagination-bar b { color: rgba(255, 255, 255, 0.88); }

/* ═══════════════════════════════════════════
   빈 상태 — Glass Empty State
   ═══════════════════════════════════════════ */
.empty-state {
    text-align: center;
    padding: 60px 40px;
    color: rgba(255, 255, 255, 0.30);
}
.empty-state .icon {
    font-size: 3.5rem;
    margin-bottom: 16px;
    opacity: 0.6;
}
.empty-state h3 {
    color: rgba(255, 255, 255, 0.60);
    margin-bottom: 8px;
    font-weight: 600;
    font-size: 1.1rem;
}
.empty-state p {
    color: rgba(255, 255, 255, 0.35);
    font-size: 0.92rem;
    line-height: 1.6;
}

/* ── 기능 카드 — Liquid Glass Card ── */
.feature-card {
    background: rgba(255, 255, 255, 0.05);
    -webkit-backdrop-filter: blur(40px) saturate(180%);
    backdrop-filter: blur(40px) saturate(180%);
    border: 0.5px solid rgba(255, 255, 255, 0.12);
    border-radius: 22px;
    padding: 32px 22px;
    text-align: center;
    transition: all 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    position: relative;
    overflow: hidden;
}
.feature-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 0.5px;
    background: linear-gradient(90deg,
        transparent 0%,
        rgba(255, 255, 255, 0.20) 30%,
        rgba(255, 255, 255, 0.20) 70%,
        transparent 100%);
}
.feature-card:hover {
    transform: translateY(-4px) scale(1.01);
    border-color: rgba(255, 255, 255, 0.22);
    background: rgba(255, 255, 255, 0.08);
    box-shadow:
        0 12px 40px rgba(0, 0, 0, 0.20),
        0 0 24px rgba(0, 122, 255, 0.05),
        inset 0 0.5px 0 rgba(255, 255, 255, 0.15);
}
.feature-card .icon {
    font-size: 2.4rem;
    margin-bottom: 16px;
    display: inline-block;
}
.feature-card h4 {
    color: rgba(255, 255, 255, 0.88);
    margin: 0 0 10px 0;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: -0.01em;
}
.feature-card p {
    color: rgba(255, 255, 255, 0.40);
    font-size: 0.82rem;
    margin: 0;
    line-height: 1.65;
}

/* ── 섹션 컨테이너 — Glass Section ── */
.section-card {
    background: rgba(255, 255, 255, 0.04);
    -webkit-backdrop-filter: blur(40px) saturate(160%);
    backdrop-filter: blur(40px) saturate(160%);
    border: 0.5px solid rgba(255, 255, 255, 0.10);
    border-radius: 24px;
    padding: 30px;
    margin-bottom: 24px;
    position: relative;
}
.section-card::before {
    content: '';
    position: absolute;
    top: 0; left: 30px; right: 30px;
    height: 0.5px;
    background: linear-gradient(90deg,
        transparent,
        rgba(255, 255, 255, 0.15),
        transparent);
}

/* ── 채팅 — Glass Chat ── */
.stChatMessage {
    border-radius: 20px !important;
    background: rgba(255, 255, 255, 0.04) !important;
    border: 0.5px solid rgba(255, 255, 255, 0.08) !important;
}
[data-testid="stChatInput"] > div {
    border-radius: 18px !important;
    border-color: rgba(255, 255, 255, 0.12) !important;
    background: rgba(255, 255, 255, 0.04) !important;
}

/* ── 디바이더 ── */
hr {
    border-color: rgba(255, 255, 255, 0.06) !important;
    opacity: 0.8 !important;
}

/* ── 스크롤바 — Minimal ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.12);
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.22);
}

/* ── 페이지 헤더 — visionOS Title ── */
.page-header {
    margin-bottom: 8px;
    padding-bottom: 20px;
    border-bottom: 0.5px solid rgba(255, 255, 255, 0.06);
}
.page-header h1 {
    font-size: 1.8rem;
    font-weight: 700;
    color: rgba(255, 255, 255, 0.92);
    margin-bottom: 6px;
    letter-spacing: -0.02em;
}
.page-header p {
    color: rgba(255, 255, 255, 0.40);
    font-size: 0.9rem;
    margin: 0;
    font-weight: 400;
}

/* ── 상태 뱃지 — Glass Pill ── */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    border-radius: 50px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    -webkit-backdrop-filter: blur(20px);
    backdrop-filter: blur(20px);
}
.status-badge.online {
    background: rgba(48, 209, 88, 0.12);
    color: #30D158;
    border: 0.5px solid rgba(48, 209, 88, 0.25);
}
.status-badge.offline {
    background: rgba(255, 69, 58, 0.12);
    color: #FF453A;
    border: 0.5px solid rgba(255, 69, 58, 0.25);
}

/* ── 프로그레스바 ── */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #0A84FF, #5E5CE6) !important;
    border-radius: 8px !important;
}
.stProgress > div > div {
    background: rgba(255, 255, 255, 0.06) !important;
    border-radius: 8px !important;
}

/* ── 알림 — Glass Alert ── */
.stAlert {
    border-radius: 16px !important;
    border: 0.5px solid rgba(255, 255, 255, 0.10) !important;
    -webkit-backdrop-filter: blur(20px);
    backdrop-filter: blur(20px);
}

/* ── 글로벌 텍스트 색상 보정 ── */
.stMarkdown, .stText { color: rgba(255, 255, 255, 0.85); }

/* ── SF Symbol SVG 아이콘 정렬 ── */
.sf-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.icon svg, .sf-icon svg {
    vertical-align: middle;
}
.page-header h1 .sf-icon {
    margin-right: 8px;
}
.feature-card .icon svg {
    opacity: 0.7;
}
.empty-state .icon svg {
    opacity: 0.5;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SF Symbols 스타일 인라인 SVG 아이콘
# ─────────────────────────────────────────────

_SVG_ATTRS = 'xmlns="http://www.w3.org/2000/svg" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"'

_ICONS = {
    # ── 네비게이션 ──
    "home": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M3 10.5L12 3l9 7.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1z"/><path d="M9 21V14h6v7"/></svg>',
    "dashboard": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><rect x="3" y="12" width="4" height="9" rx="1"/><rect x="10" y="5" width="4" height="16" rx="1"/><rect x="17" y="8" width="4" height="13" rx="1"/></svg>',
    "upload": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M14 3H6a1 1 0 00-1 1v16a1 1 0 001 1h12a1 1 0 001-1V8z"/><path d="M14 3v5h5"/><path d="M12 17v-6m-3 3l3-3 3 3"/></svg>',
    "search": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.35-4.35"/></svg>',
    "robot": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><rect x="4" y="6" width="16" height="14" rx="3"/><circle cx="9" cy="13" r="1.5" fill="currentColor" stroke="none"/><circle cx="15" cy="13" r="1.5" fill="currentColor" stroke="none"/><path d="M12 3v3"/><circle cx="12" cy="2.5" r="1"/><path d="M2 12h2m16 0h2"/></svg>',

    # ── 상태/액션 ──
    "gear": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72l1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>',
    "check": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M5 13l4 4L19 7"/></svg>',
    "xmark": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>',
    "warning": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M12 2L1 21h22z"/><path d="M12 9v5m0 3v.01"/></svg>',
    "trash": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M3 6h18M8 6V4a1 1 0 011-1h6a1 1 0 011 1v2"/><path d="M5 6v14a2 2 0 002 2h10a2 2 0 002-2V6"/><path d="M10 11v6m4-6v6"/></svg>',
    "refresh": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M1 4v6h6"/><path d="M3.51 15a9 9 0 100-6.41L1 10"/></svg>',
    "rocket": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M4.5 16.5L2 22l5.5-2.5"/><path d="M15 2s5 2 5 10-5 10-5 10H9S4 14 4 12s0-4 2-6l3-2z"/><circle cx="12" cy="10" r="2"/></svg>',

    # ── 컨텐츠 타입 ──
    "image": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>',
    "doc": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M14 3H6a1 1 0 00-1 1v16a1 1 0 001 1h12a1 1 0 001-1V8z"/><path d="M14 3v5h5"/><path d="M8 13h8m-8 4h5"/></svg>',
    "text": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M14 3H6a1 1 0 00-1 1v16a1 1 0 001 1h12a1 1 0 001-1V8z"/><path d="M14 3v5h5"/><path d="M8 11h8m-8 3h8m-8 3h4"/></svg>',
    "pencil": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>',
    "clipboard": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><rect x="5" y="2" width="14" height="20" rx="2"/><path d="M9 2h6v2a1 1 0 01-1 1h-4a1 1 0 01-1-1z"/><path d="M9 12h6m-6 4h4"/></svg>',

    # ── 카테고리 ──
    "target": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
    "wrench": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91A6 6 0 016.23 2.53l3.77 3.77z"/></svg>',
    "bolt": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>',
    "car": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M5 17h14M5 17a2 2 0 01-2-2V9a2 2 0 012-2h1l2-3h8l2 3h1a2 2 0 012 2v6a2 2 0 01-2 2M5 17a2 2 0 100 4 2 2 0 000-4zm14 0a2 2 0 100 4 2 2 0 000-4z"/></svg>',
    "package": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M16.5 9.4l-9-5.19M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><path d="M3.27 6.96L12 12.01l8.73-5.05M12 22.08V12"/></svg>',
    "tag": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><circle cx="7" cy="7" r="1" fill="currentColor" stroke="none"/></svg>',
    "shaft": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M6 4v16"/><path d="M18 4v16"/><rect x="6" y="8" width="12" height="8" rx="1"/></svg>',
    "bearing": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="3.5" r="1" fill="currentColor" stroke="none"/><circle cx="12" cy="20.5" r="1" fill="currentColor" stroke="none"/><circle cx="3.5" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="20.5" cy="12" r="1" fill="currentColor" stroke="none"/></svg>',
    "racing": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M5 17h14M5 17a2 2 0 01-2-2v-3l2-5h14l2 5v3a2 2 0 01-2 2M5 17a2 2 0 100 4 2 2 0 000-4zm14 0a2 2 0 100 4 2 2 0 000-4z"/></svg>',

    # ── 검색/필터 ──
    "chat": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>',
    "hashtag": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M4 9h16M4 15h16M10 3l-2 18M16 3l-2 18"/></svg>',
    "ruler": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M2 6h20v12H2z"/><path d="M6 6v4m4-4v6m4-6v4m4-4v6"/></svg>',
    "globe": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15 15 0 014 10 15 15 0 01-4 10 15 15 0 01-4-10A15 15 0 0112 2z"/></svg>',

    # ── UI 요소 ──
    "pin": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M15 4.5l-4 7.5H5l6 8v-5h3.5l4.5-7-4-3.5z"/></svg>',
    "folder": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>',
    "person": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>',
    "drafting": f'<svg {_SVG_ATTRS} width="20" height="20" viewBox="0 0 24 24"><path d="M2 22L22 2"/><path d="M2 22l5-1-4-4z"/><path d="M18 8l-4-4"/><circle cx="12" cy="12" r="1.5"/><path d="M7 2h10M2 7v10"/></svg>',
    "circle_green": f'<svg width="20" height="20" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="6" fill="#30D158"/></svg>',
}


def _icon(name: str, size: int = 20) -> str:
    """SF Symbols 스타일 SVG 아이콘을 인라인 HTML span으로 반환한다."""
    svg = _ICONS.get(name, "")
    if not svg:
        return ""
    if size != 20:
        svg = svg.replace('width="20"', f'width="{size}"').replace('height="20"', f'height="{size}"')
    return f'<span class="sf-icon">{svg}</span>'


# ─────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────

ITEMS_PER_PAGE = 15
CATEGORY_MAP = {
    "": "전체",
    "engine": "엔진",
    "chassis": "섀시",
    "body": "차체",
    "electrical": "전장",
    "transmission": "변속기",
    "Shafts": "샤프트",
    "bearing_UCP": "베어링 UCP",
    "bearing_UCF": "베어링 UCF",
    "other": "기타",
}


def _get_category_map() -> dict[str, str]:
    """YOLO-cls 클래스명을 포함한 동적 카테고리 맵 생성

    YOLO 모델이 로드되면 73클래스를 자동으로 추가한다.
    기존 CATEGORY_MAP을 기반으로 하되 YOLO 클래스를 병합한다.
    """
    merged = dict(CATEGORY_MAP)
    try:
        pipeline = get_pipeline()
        stats = pipeline.get_stats()
        yolo_info = stats.get("yolo_classifier", {})
        if yolo_info.get("healthy") and pipeline._classifier:
            for name in pipeline._classifier.class_names:
                if name not in merged:
                    merged[name] = name
    except Exception:
        pass
    return merged


# ─────────────────────────────────────────────
# 파이프라인 초기화 (캐싱)
# ─────────────────────────────────────────────

@st.cache_resource
def get_pipeline():
    """파이프라인 싱글턴 (Streamlit 세션 간 공유).

    core.dependencies.get_pipeline()에 위임하여
    FastAPI와 동일한 인스턴스를 공유한다.
    """
    from core.dependencies import get_pipeline as _get_pipeline
    return _get_pipeline()


# ─────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        # CAD Vision 브랜딩 — visionOS Glass Style
        st.markdown(
            '<div style="text-align:center; padding: 16px 0 10px 0;">'
            '<div style="width:52px;height:52px;margin:0 auto 12px;'
            'background:rgba(255,255,255,0.08);'
            'backdrop-filter:blur(30px);-webkit-backdrop-filter:blur(30px);'
            'border-radius:16px;display:flex;align-items:center;justify-content:center;'
            'border:0.5px solid rgba(255,255,255,0.18);'
            'box-shadow:0 4px 16px rgba(0,0,0,0.15),inset 0 0.5px 0 rgba(255,255,255,0.15);">'
            f'{_icon("drafting", 26)}</div>'
            '<span style="font-size:1.25rem; font-weight:700; '
            'background:linear-gradient(135deg,#64D2FF,#0A84FF);'
            '-webkit-background-clip:text;-webkit-text-fill-color:transparent;'
            'letter-spacing:-0.02em;">CAD Vision</span><br>'
            '<span style="font-size:0.65rem; color:rgba(255,255,255,0.35); letter-spacing:0.06em;'
            'text-transform:uppercase; font-weight:500;">AI Drawing Search Engine</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.divider()

        page = st.radio(
            "메뉴",
            ["대시보드", "도면 등록", "도면 검색", "도면 분석", "도구"],
            label_visibility="collapsed",
        )

        st.divider()

        # 시스템 상태
        with st.expander("시스템 상태", expanded=False):
            try:
                pipeline = get_pipeline()
                stats = pipeline.get_stats()

                col_a, col_b = st.columns(2)
                col_a.metric("도면", f"{stats['total_drawings']:,}")
                col_b.metric("벡터", f"{stats['vector_store']['image_collection_count']:,}")

                if stats["ollama_healthy"]:
                    st.markdown(
                        f'<span class="status-badge online">● Ollama ({settings.ollama_model})</span>',
                        unsafe_allow_html=True,
                    )
                    # 모델 선택 드롭다운
                    try:
                        from core.llm import DrawingLLM
                        _llm_tmp = DrawingLLM(
                            base_url=settings.ollama_base_url,
                            model=settings.ollama_model,
                        )
                        available_models = _llm_tmp.get_available_models()
                        if available_models:
                            model_names = [m["name"] for m in available_models]
                            model_labels = [f'{m["name"]} ({m["size"]})' for m in available_models]
                            current_idx = 0
                            for idx, name in enumerate(model_names):
                                if name == settings.ollama_model:
                                    current_idx = idx
                                    break
                            selected_label = st.selectbox(
                                "LLM 모델",
                                model_labels,
                                index=current_idx,
                                key="ollama_model_select",
                            )
                            selected_model = model_names[model_labels.index(selected_label)]
                            if selected_model != st.session_state.get("_active_ollama_model", settings.ollama_model):
                                st.session_state["_active_ollama_model"] = selected_model
                                settings.ollama_model = selected_model
                                # pipeline의 LLM 모델도 교체
                                if hasattr(pipeline, '_llm') and pipeline._llm is not None:
                                    pipeline._llm.model = selected_model
                                st.toast(f"모델 변경: {selected_model}")
                    except Exception:
                        pass  # 모델 목록 조회 실패 시 무시
                else:
                    st.markdown(
                        '<span class="status-badge offline">● Ollama 미연결</span>',
                        unsafe_allow_html=True,
                    )

                # YOLO-cls 상태
                yolo_info = stats.get("yolo_classifier", {})
                if yolo_info.get("enabled"):
                    if yolo_info.get("healthy"):
                        n_cls = yolo_info.get("num_classes", 0)
                        st.markdown(
                            f'<span class="status-badge online">● YOLO-cls {n_cls}cls</span>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            '<span class="status-badge offline">● YOLO-cls 오류</span>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.markdown(
                        '<span class="status-badge offline">● YOLO-cls 비활성</span>',
                        unsafe_allow_html=True,
                    )
            except Exception as e:
                st.error(f"상태 확인 실패: {e}")

        # 사이드바 푸터 — visionOS
        st.markdown(
            '<div style="position:fixed; bottom:14px; left:14px; '
            'color:rgba(255,255,255,0.18); font-size:0.62rem; letter-spacing:0.04em;'
            'font-weight:500;">'
            'CAD Vision v2.0 · Liquid Glass</div>',
            unsafe_allow_html=True,
        )

    return page


# ─────────────────────────────────────────────
# 페이지: 대시보드
# ─────────────────────────────────────────────

def page_dashboard():
    st.markdown(
        f'<div class="page-header">'
        f'<h1>{_icon("dashboard", 28)} 대시보드</h1>'
        f'<p>등록된 도면 현황과 시스템 상태를 한눈에 확인합니다.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 메트릭 카드
    col1, col2, col3, col4, col5 = st.columns(5)

    try:
        pipeline = get_pipeline()
        stats = pipeline.get_stats()

        col1.metric("총 등록 도면", f"{stats['total_drawings']:,}건")
        col2.metric("이미지 벡터", f"{stats['vector_store']['image_collection_count']:,}건")
        col3.metric("텍스트 벡터", f"{stats['vector_store']['text_collection_count']:,}건")
        col4.metric("Ollama", "연결됨" if stats["ollama_healthy"] else "미연결")

        yolo_info = stats.get("yolo_classifier", {})
        if yolo_info.get("healthy"):
            col5.metric("YOLO-cls", f"{yolo_info.get('num_classes', 0)}cls")
        else:
            col5.metric("YOLO-cls", "비활성")
    except Exception:
        col1.metric("총 등록 도면", "—")
        col2.metric("이미지 벡터", "—")
        col3.metric("텍스트 벡터", "—")
        col4.metric("Ollama", "—")
        col5.metric("YOLO-cls", "—")

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── 필터 + 검색 바 ──
    st.markdown(
        f'<h4 style="color:rgba(255,255,255,0.85);display:flex;align-items:center;gap:8px;">'
        f'{_icon("clipboard", 18)} 등록된 도면 목록</h4>',
        unsafe_allow_html=True,
    )

    col_filter, col_search = st.columns([1, 2])

    with col_filter:
        dynamic_map = _get_category_map()
        filter_category = st.selectbox(
            "카테고리 필터",
            options=list(dynamic_map.keys()),
            format_func=lambda x: dynamic_map.get(x, x),
            key="dash_filter_cat",
        )

    with col_search:
        search_keyword = st.text_input(
            "파일명 검색",
            placeholder="파일명으로 검색...",
            key="dash_search",
        )

    try:
        records = pipeline.get_all_records()

        # 필터 적용
        if filter_category:
            records = [r for r in records if r.category == filter_category]
        if search_keyword:
            kw = search_keyword.lower()
            records = [r for r in records if kw in r.file_name.lower()]

        total = len(records)

        if total == 0:
            if filter_category or search_keyword:
                st.markdown(
                    f'<div class="empty-state">'
                    f'<div class="icon">{_icon("search", 48)}</div>'
                    f'<h3>검색 결과 없음</h3>'
                    f'<p>필터 조건에 맞는 도면이 없습니다. 필터를 조정해보세요.</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="empty-state">'
                    f'<div class="icon">{_icon("drafting", 48)}</div>'
                    f'<h3>등록된 도면이 없습니다</h3>'
                    f'<p>왼쪽 메뉴의 "도면 등록"에서 도면을 등록해주세요.</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            return

        # ── 페이지네이션 ──
        total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

        if "dash_page" not in st.session_state:
            st.session_state.dash_page = 1
        if st.session_state.dash_page > total_pages:
            st.session_state.dash_page = total_pages

        current_page = st.session_state.dash_page

        col_prev, col_info, col_next = st.columns([1, 3, 1])
        with col_prev:
            if st.button("◀ 이전", disabled=(current_page <= 1), key="dash_prev"):
                st.session_state.dash_page -= 1
                st.rerun()
        with col_info:
            st.markdown(
                f'<div class="pagination-bar">'
                f'총 <b>{total:,}</b>건 &nbsp;|&nbsp; '
                f'페이지 <b>{current_page}</b> / {total_pages}'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col_next:
            if st.button("다음 ▶", disabled=(current_page >= total_pages), key="dash_next"):
                st.session_state.dash_page += 1
                st.rerun()

        # 현재 페이지 레코드
        start = (current_page - 1) * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        page_records = records[start:end]

        # ── 도면 목록 ──
        for record in page_records:
            cat_label = dynamic_map.get(record.category, record.category or '미분류')
            # YOLO 신뢰도가 있으면 표시
            yolo_badge = ""
            if record.yolo_confidence > 0:
                yolo_badge = f" ({record.yolo_confidence:.0%})"
            with st.expander(f"{record.file_name} — {cat_label}{yolo_badge} (ID: {record.drawing_id[:8]})"):
                col_img, col_info, col_action = st.columns([1, 2, 0.5])

                with col_img:
                    resolved = _resolve_file_path(record.file_path)
                    if resolved:
                        try:
                            img = Image.open(resolved)
                            st.image(img, width=280)
                        except Exception:
                            st.markdown(
                                f'<div style="background:#1e293b;border-radius:10px;padding:40px;text-align:center;color:#475569;">'
                                f'<div style="margin-bottom:8px;">{_icon("image", 32)}</div>'
                                f'미리보기 불가</div>',
                                unsafe_allow_html=True,
                            )
                    else:
                        st.markdown(
                            f'<div style="background:#1e293b;border-radius:10px;padding:40px;text-align:center;color:#475569;">'
                            f'<div style="margin-bottom:8px;">{_icon("image", 32)}</div>'
                            f'이미지 경로 없음</div>',
                            unsafe_allow_html=True,
                        )

                with col_info:
                    st.markdown(f"**카테고리:** {cat_label}")
                    pn = ', '.join(record.part_numbers) if record.part_numbers else '—'
                    st.markdown(f"**부품번호:** `{pn}`")
                    mat = ', '.join(record.materials) if record.materials else '—'
                    st.markdown(f"**재질:** {mat}")
                    dims = ', '.join(record.dimensions[:5]) if record.dimensions else '—'
                    st.markdown(f"**치수:** {dims}")
                    if record.description:
                        st.markdown(f"**AI 설명:** {record.description[:200]}...")

                with col_action:
                    delete_key = f"del_{record.drawing_id}"
                    confirm_key = f"confirm_{record.drawing_id}"

                    if st.session_state.get(confirm_key, False):
                        st.warning("삭제 확인")
                        col_y, col_n = st.columns(2)
                        with col_y:
                            if st.button("예", key=f"yes_{record.drawing_id}", type="primary"):
                                try:
                                    pipeline.delete_drawing(record.drawing_id)
                                    st.session_state[confirm_key] = False
                                    st.toast(f"'{record.file_name}' 삭제 완료")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"삭제 실패: {e}")
                        with col_n:
                            if st.button("아니오", key=f"no_{record.drawing_id}"):
                                st.session_state[confirm_key] = False
                                st.rerun()
                    else:
                        if st.button("삭제", key=delete_key, help="도면 삭제"):
                            st.session_state[confirm_key] = True
                            st.rerun()

    except Exception as e:
        st.error(f"레코드 조회 실패: {e}")


# ─────────────────────────────────────────────
# 페이지: 도면 등록
# ─────────────────────────────────────────────

def page_register():
    st.markdown(
        f'<div class="page-header">'
        f'<h1>{_icon("upload", 28)} 도면 등록</h1>'
        f'<p>도면 이미지를 업로드하면 자동으로 OCR, 임베딩, 분류가 수행됩니다.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 단건 등록 섹션 ──
    st.markdown(
        '<div class="section-card">'
        f'<h4 style="margin-top:0;color:#e2e8f0;display:flex;align-items:center;gap:8px;">{_icon("pin", 18)} 단건 등록</h4>',
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "도면 이미지 업로드",
        type=["png", "jpg", "jpeg", "tiff", "tif", "dxf"],
        help="지원 형식: PNG, JPG, TIFF, DXF (최대 50MB)",
    )

    col1, col2 = st.columns(2)

    # 카테고리 옵션: 기본 + YOLO 클래스
    reg_categories = ["", "engine", "chassis", "body", "electrical", "transmission", "other"]
    reg_labels = {
        "": "YOLO 자동 분류",
        "engine": "엔진",
        "chassis": "섀시",
        "body": "차체",
        "electrical": "전장",
        "transmission": "변속기",
        "other": "기타",
    }

    category = col1.selectbox(
        "카테고리",
        reg_categories,
        format_func=lambda x: reg_labels.get(x, x),
    )
    use_llm = col2.checkbox("AI 설명 생성", value=True, help="Ollama LLM으로 도면 설명을 생성합니다")

    if uploaded_file and st.button("등록 시작", type="primary"):
        safe_name = _sanitize_filename(uploaded_file.name)
        temp_path = _ALLOWED_UPLOAD_DIR / safe_name
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        if not str(temp_path.resolve()).startswith(str(_ALLOWED_UPLOAD_DIR)):
            st.error("잘못된 파일명입니다.")
            return
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        with st.spinner("도면 처리 중... (OCR → 임베딩 → 벡터 저장 → AI 분석)"):
            try:
                pipeline = get_pipeline()
                record = pipeline.register_drawing(
                    temp_path, category=category, use_llm=use_llm, copy_to_store=False,
                )
                st.success(f"도면 등록 완료! (ID: {record.drawing_id})")

                col_img, col_info = st.columns([1, 2])
                with col_img:
                    display_path = temp_path
                    if temp_path.suffix.lower() == ".dxf":
                        png_candidate = temp_path.with_suffix(".png")
                        if png_candidate.exists():
                            display_path = png_candidate
                    st.image(str(display_path), width=400)
                with col_info:
                    st.markdown(f"**파일명:** {record.file_name}")

                    # YOLO-cls 자동분류 결과 표시
                    if record.yolo_confidence > 0:
                        review_mark = " (검토 필요)" if record.yolo_needs_review else ""
                        st.markdown(
                            f"**자동분류:** `{record.category}` "
                            f"(신뢰도: {record.yolo_confidence:.1%}{review_mark})"
                        )
                        if record.yolo_top_k:
                            top_k_str = " | ".join(
                                f"{name} {conf:.1%}" for name, conf in record.yolo_top_k[:3]
                            )
                            st.caption(f"Top-3: {top_k_str}")
                    elif record.category:
                        st.markdown(f"**카테고리:** {record.category}")

                    st.markdown("**OCR 추출 텍스트:**")
                    st.code(record.ocr_text[:500] if record.ocr_text else "추출된 텍스트 없음")
                    st.markdown(f"**부품번호:** `{record.part_numbers}`")
                    st.markdown(f"**재질:** {record.materials}")
                    if record.description:
                        st.markdown("**AI 설명:**")
                        st.markdown(record.description)
            except Exception as e:
                st.error(f"등록 실패: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── 배치 등록 섹션 ──
    st.markdown(
        '<div class="section-card">'
        f'<h4 style="margin-top:0;color:#e2e8f0;display:flex;align-items:center;gap:8px;">{_icon("package", 18)} 배치 등록</h4>'
        '<p style="color:#64748b;font-size:0.85rem;margin-top:-4px;">디렉토리 내 모든 도면을 한번에 등록합니다.</p>',
        unsafe_allow_html=True,
    )

    batch_dir = st.text_input(
        "도면 디렉토리 경로",
        placeholder="./data/sample_drawings/engine",
    )

    if batch_dir and st.button("배치 등록 시작"):
        batch_path = _validate_batch_path(batch_dir)
        if batch_path is None:
            st.error("허용된 데이터 디렉토리(./data/) 내의 유효한 경로를 입력해주세요.")
            st.markdown('</div>', unsafe_allow_html=True)
            return

        supported = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".dxf"}
        image_files = sorted([
            f for f in batch_path.iterdir()
            if f.is_file() and f.suffix.lower() in supported
        ])

        if not image_files:
            st.warning("해당 디렉토리에 이미지 파일이 없습니다.")
            st.markdown('</div>', unsafe_allow_html=True)
            return

        total_files = len(image_files)
        st.info(f"{total_files}개 파일 발견")

        progress_bar = st.progress(0, text="배치 등록 준비 중...")
        status_text = st.empty()
        success_count = 0
        fail_count = 0

        try:
            pipeline = get_pipeline()
            for i, img_file in enumerate(image_files):
                progress_bar.progress(
                    (i + 1) / total_files,
                    text=f"처리 중: {img_file.name} ({i+1}/{total_files})"
                )
                try:
                    pipeline.register_drawing(img_file, use_llm=False, copy_to_store=False)
                    success_count += 1
                except Exception as e:
                    fail_count += 1
                    status_text.warning(f"{img_file.name} 실패: {e}")

            progress_bar.progress(1.0, text="완료!")

            if fail_count == 0:
                st.success(f"{success_count}건 전체 등록 완료!")
            else:
                st.warning(f"성공 {success_count}건 / 실패 {fail_count}건")
        except Exception as e:
            st.error(f"배치 등록 중 오류: {e}")

    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 페이지: 도면 검색
# ─────────────────────────────────────────────

def page_search():
    st.markdown(
        f'<div class="page-header">'
        f'<h1>{_icon("search", 28)} 도면 검색</h1>'
        f'<p>자연어 또는 이미지로 유사한 도면을 검색합니다.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    tab_text, tab_image, tab_part, tab_dxf = st.tabs(
        ["자연어 검색", "이미지 검색", "부품번호 검색", "DXF 구조 검색"]
    )

    # 자연어 검색
    with tab_text:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        query = st.text_input(
            "검색어 입력",
            placeholder="예: 터보차저 배기측 가스켓, brake pad, 실린더 헤드 볼트...",
        )
        col_cat, col_slider, col_btn = st.columns([2, 2, 1])
        with col_cat:
            cat_map = _get_category_map()
            cat_options = list(cat_map.keys())
            selected_cat = st.selectbox(
                "카테고리 필터",
                cat_options,
                format_func=lambda x: cat_map.get(x, x),
                key="text_search_cat",
            )
        with col_slider:
            top_k = st.slider("검색 결과 수", 1, 20, 5)
        with col_btn:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            search_clicked = st.button("검색", key="text_search", type="primary", use_container_width=True)

        if query and search_clicked:
            with st.spinner("검색 중..."):
                try:
                    st.session_state["_last_search_query"] = query
                    st.session_state["_last_search_type"] = "text"
                    pipeline = get_pipeline()
                    results = pipeline.search_by_text(
                        query, top_k=top_k, category=selected_cat,
                    )
                    if results:
                        filter_label = f" [{cat_map.get(selected_cat, selected_cat)}]" if selected_cat else ""
                        st.success(f"{len(results)}건의 결과를 찾았습니다.{filter_label}")
                        _display_search_results(results, pipeline)
                    else:
                        st.markdown(
                            f'<div class="empty-state">'
                            f'<div class="icon">{_icon("search", 48)}</div>'
                            f'<h3>검색 결과 없음</h3>'
                            f'<p>다른 키워드 또는 카테고리로 시도해보세요.</p>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                except Exception as e:
                    st.error(f"검색 실패: {e}")

        elif not query:
            # 빈 상태 안내
            st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(
                    f'<div class="feature-card"><div class="icon">{_icon("wrench", 36)}</div>'
                    f'<h4>부품명 검색</h4>'
                    f'<p>"기어", "베어링", "샤프트" 등 부품명으로 검색하세요</p></div>',
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f'<div class="feature-card"><div class="icon">{_icon("ruler", 36)}</div>'
                    f'<h4>규격 검색</h4>'
                    f'<p>"UCP205", "Ø50mm" 등 규격/치수로 검색하세요</p></div>',
                    unsafe_allow_html=True,
                )
            with c3:
                st.markdown(
                    f'<div class="feature-card"><div class="icon">{_icon("globe", 36)}</div>'
                    f'<h4>다국어 지원</h4>'
                    f'<p>한국어/영어 모두 지원합니다. 자유롭게 검색하세요</p></div>',
                    unsafe_allow_html=True,
                )

    # 이미지 검색
    with tab_image:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        search_image = st.file_uploader(
            "검색할 도면 이미지 업로드",
            type=["png", "jpg", "jpeg"],
            key="search_image",
        )

        col_yolo, col_cat_img = st.columns(2)
        with col_yolo:
            use_yolo_filter = st.checkbox("YOLO 카테고리 자동 필터", value=True, key="yolo_filter")
        with col_cat_img:
            cat_map_img = _get_category_map()
            manual_cat_img = st.selectbox(
                "카테고리 수동 필터",
                list(cat_map_img.keys()),
                format_func=lambda x: cat_map_img.get(x, x),
                key="img_search_cat",
            )

        top_k_img = st.slider("검색 결과 수", 1, 20, 5, key="top_k_img")

        if search_image and st.button("유사 도면 검색", key="img_search", type="primary"):
            safe_name = _sanitize_filename(search_image.name)
            temp_path = Path(tempfile.gettempdir()) / f"drawingllm_search_{uuid.uuid4().hex[:8]}_{safe_name}"
            with open(temp_path, "wb") as f:
                f.write(search_image.getbuffer())

            col_query, col_results = st.columns([1, 2])
            with col_query:
                st.image(str(temp_path), caption="검색 이미지", width=300)

                # YOLO 분류 결과 표시
                if use_yolo_filter:
                    try:
                        pipeline = get_pipeline()
                        yolo_detail = pipeline.classify_with_detail(temp_path)
                        if yolo_detail:
                            st.info(
                                f"YOLO 분류: **{yolo_detail.category}** "
                                f"({yolo_detail.confidence:.1%})"
                            )
                            if yolo_detail.top_k and len(yolo_detail.top_k) > 1:
                                with st.expander("Top-5 후보"):
                                    for cat_name, conf in yolo_detail.top_k[:5]:
                                        st.progress(conf, text=f"{cat_name}: {conf:.1%}")
                    except Exception:
                        pass

            with col_results:
                with st.spinner("유사 도면 검색 중..."):
                    try:
                        pipeline = get_pipeline()
                        results = pipeline.search_by_image(
                            temp_path,
                            top_k=top_k_img,
                            category=manual_cat_img,
                            use_yolo_filter=use_yolo_filter,
                        )
                        if results:
                            st.success(f"{len(results)}건의 유사 도면을 찾았습니다.")
                            _display_search_results(results, pipeline)
                        else:
                            st.warning("유사 도면을 찾지 못했습니다. 카테고리 필터를 해제해보세요.")
                    except Exception as e:
                        st.error(f"검색 실패: {e}")

            temp_path.unlink(missing_ok=True)

        elif not search_image:
            st.markdown(
                f'<div class="empty-state">'
                f'<div class="icon">{_icon("image", 48)}</div>'
                f'<h3>도면 이미지를 업로드하세요</h3>'
                f'<p>비슷한 구조의 도면을 AI가 자동으로 찾아드립니다.</p>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # 부품번호 검색
    with tab_part:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        pn_query = st.text_input(
            "부품번호 입력",
            placeholder="예: AB-1234, UCP205, SN3036...",
            key="part_number_query",
        )

        if pn_query and st.button("부품번호 검색", key="pn_search", type="primary"):
            with st.spinner("부품번호 검색 중..."):
                try:
                    pipeline = get_pipeline()
                    records = pipeline.search_by_part_number(pn_query)
                    if records:
                        st.success(f"{len(records)}건의 도면을 찾았습니다.")
                        for i, record in enumerate(records):
                            cat_label = _get_category_map().get(record.category, record.category or '미분류')
                            with st.expander(
                                f"#{i+1} — {record.file_name} | "
                                f"카테고리: {cat_label} | "
                                f"부품번호: {', '.join(record.part_numbers)}"
                            ):
                                col_img, col_info = st.columns([1, 2])
                                with col_img:
                                    try:
                                        resolved = _resolve_file_path(record.file_path)
                                        if resolved:
                                            st.image(str(resolved), width=300)
                                        else:
                                            st.info("이미지 없음")
                                    except Exception:
                                        st.info("이미지 로딩 실패")
                                with col_info:
                                    st.markdown(f"**파일명:** {record.file_name}")
                                    st.markdown(f"**카테고리:** :blue[{cat_label}]")
                                    st.markdown(f"**부품번호:** `{', '.join(record.part_numbers)}`")
                                    if record.dimensions:
                                        st.markdown(f"**치수:** {', '.join(record.dimensions)}")
                                    if record.materials:
                                        st.markdown(f"**재질:** {', '.join(record.materials)}")
                                    if record.ocr_text:
                                        st.markdown("**OCR 텍스트:**")
                                        st.code(record.ocr_text[:300])
                    else:
                        st.markdown(
                            f'<div class="empty-state">'
                            f'<div class="icon">{_icon("hashtag", 48)}</div>'
                            f'<h3>검색 결과 없음</h3>'
                            f'<p>다른 부품번호로 시도해보세요. 부분 일치를 지원합니다.</p>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                except Exception as e:
                    st.error(f"부품번호 검색 실패: {e}")

        elif not pn_query:
            st.markdown(
                f'<div class="empty-state">'
                f'<div class="icon">{_icon("hashtag", 48)}</div>'
                f'<h3>부품번호를 입력하세요</h3>'
                f'<p>도면의 부품번호(파트넘버)로 정확하게 검색합니다. 부분 일치를 지원합니다.</p>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # DXF 구조 검색
    with tab_dxf:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        dxf_file = st.file_uploader(
            "DXF 파일 업로드",
            type=["dxf"],
            key="search_dxf",
        )

        col_cat_dxf, col_topk_dxf = st.columns(2)
        with col_cat_dxf:
            cat_map_dxf = _get_category_map()
            selected_cat_dxf = st.selectbox(
                "카테고리 필터",
                list(cat_map_dxf.keys()),
                format_func=lambda x: cat_map_dxf.get(x, x),
                key="dxf_search_cat",
            )
        with col_topk_dxf:
            top_k_dxf = st.slider("검색 결과 수", 1, 20, 5, key="top_k_dxf")

        if dxf_file and st.button("구조 유사 도면 검색", key="dxf_search", type="primary"):
            safe_name = _sanitize_filename(dxf_file.name)
            temp_path = Path(tempfile.gettempdir()) / f"drawingllm_dxf_{uuid.uuid4().hex[:8]}_{safe_name}"
            with open(temp_path, "wb") as f:
                f.write(dxf_file.getbuffer())

            with st.spinner("DXF 구조 분석 및 검색 중..."):
                try:
                    pipeline = get_pipeline()
                    results = pipeline.search_by_dxf(
                        temp_path,
                        top_k=top_k_dxf,
                        category=selected_cat_dxf,
                    )
                    if results:
                        st.success(f"{len(results)}건의 구조적으로 유사한 도면을 찾았습니다.")
                        _display_search_results(results, pipeline)
                    else:
                        st.markdown(
                            f'<div class="empty-state">'
                            f'<div class="icon">{_icon("search", 48)}</div>'
                            f'<h3>검색 결과 없음</h3>'
                            f'<p>GNN 모델이 로드되지 않았거나 유사 도면이 없습니다.</p>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                except Exception as e:
                    st.error(f"DXF 검색 실패: {e}")

            temp_path.unlink(missing_ok=True)

        elif not dxf_file:
            st.markdown(
                f'<div class="empty-state">'
                f'<div class="icon">{_icon("drafting", 48)}</div>'
                f'<h3>DXF 파일을 업로드하세요</h3>'
                f'<p>DXF 파일의 기하학적 구조를 분석하여 유사한 도면을 GNN으로 검색합니다.</p>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _display_search_results(results: list, pipeline):
    """검색 결과 표시 (유사도 바 포함, 동일 파일 중복 제거)"""
    # 동일 파일명 중복 제거 (최고 점수만 유지)
    seen_files: set[str] = set()
    deduped: list = []
    for result in results:
        fname = result.metadata.get('file_name', result.drawing_id)
        if fname not in seen_files:
            seen_files.add(fname)
            deduped.append(result)
    results = deduped

    for i, result in enumerate(results):
        score = result.score
        score_pct = f"{score * 100:.1f}%"

        if score >= 0.8:
            bar_color = "linear-gradient(90deg, #22c55e, #16a34a)"
        elif score >= 0.6:
            bar_color = "linear-gradient(90deg, #3b82f6, #2563eb)"
        elif score >= 0.4:
            bar_color = "linear-gradient(90deg, #eab308, #ca8a04)"
        else:
            bar_color = "linear-gradient(90deg, #ef4444, #dc2626)"

        fname = result.metadata.get('file_name', result.drawing_id[:12])
        with st.expander(f"#{i+1} — {fname} | 유사도: {score_pct}"):
            st.markdown(
                f'<div class="score-bar-bg">'
                f'<div class="score-bar-fill" style="width:{max(score*100, 8):.0f}%;background:{bar_color};">'
                f'{score_pct}</div></div>',
                unsafe_allow_html=True,
            )

            col_img, col_info = st.columns([1, 2])

            with col_img:
                try:
                    raw_path = result.metadata.get("file_path", result.file_path)
                    resolved = _resolve_file_path(raw_path)
                    if resolved:
                        st.image(str(resolved), width=300)
                    else:
                        st.markdown(
                            f'<div style="background:#1e293b;border-radius:10px;padding:40px;'
                            f'text-align:center;color:#475569;">'
                            f'<div style="margin-bottom:8px;">{_icon("image", 32)}</div>'
                            f'이미지 없음</div>',
                            unsafe_allow_html=True,
                        )
                except Exception:
                    st.info("이미지 로딩 실패")

            with col_info:
                cat = result.metadata.get('category', '')
                dynamic_cat_map = _get_category_map()
                cat_label = dynamic_cat_map.get(cat, cat or '미분류')
                st.markdown(f"**파일명:** {fname}")
                st.markdown(f"**카테고리:** :blue[{cat_label}]")
                pn = result.metadata.get('part_numbers', '—')
                st.markdown(f"**부품번호:** `{pn}`")

                ocr_text = result.metadata.get("ocr_text", "")
                if ocr_text:
                    st.markdown("**OCR 텍스트:**")
                    st.code(ocr_text[:300])

                record = pipeline.get_record(result.drawing_id)
                if record and record.description:
                    st.markdown("**AI 설명:**")
                    st.markdown(record.description[:300])

            # ── 피드백 버튼 ──
            col_up, col_down, col_spacer = st.columns([1, 1, 4])
            with col_up:
                if st.button("\U0001f44d", key=f"up_{result.drawing_id}_{i}"):
                    try:
                        from core.feedback_store import FeedbackStore
                        _fb = _get_feedback_store_cached()
                        _fb.add_feedback(
                            query_text=st.session_state.get("_last_search_query", ""),
                            query_type=st.session_state.get("_last_search_type", "text"),
                            drawing_id=result.drawing_id,
                            score=score,
                            relevance=1,
                            category=cat,
                        )
                        st.success("감사합니다!")
                    except Exception:
                        st.warning("피드백 저장 실패")
            with col_down:
                if st.button("\U0001f44e", key=f"down_{result.drawing_id}_{i}"):
                    try:
                        from core.feedback_store import FeedbackStore
                        _fb = _get_feedback_store_cached()
                        _fb.add_feedback(
                            query_text=st.session_state.get("_last_search_query", ""),
                            query_type=st.session_state.get("_last_search_type", "text"),
                            drawing_id=result.drawing_id,
                            score=score,
                            relevance=0,
                            category=cat,
                        )
                        st.info("피드백이 저장되었습니다.")
                    except Exception:
                        st.warning("피드백 저장 실패")


def _get_feedback_store_cached():
    """FeedbackStore 싱글톤 (Streamlit 세션 캐시)."""
    if "_feedback_store" not in st.session_state:
        from core.feedback_store import FeedbackStore
        st.session_state["_feedback_store"] = FeedbackStore()
    return st.session_state["_feedback_store"]


# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# LLM 에러 가이드 헬퍼
# ─────────────────────────────────────────────

def _show_llm_error_guide(error_msg: str):
    """에러 메시지 내용에 따라 원인별 해결 가이드를 표시한다."""
    msg = error_msg.lower()
    if "연결할 수 없습니다" in error_msg or "connect" in msg:
        st.info(
            "**Ollama 서버 연결 실패**\n\n"
            "- Docker 환경: `docker compose ps`로 ollama 컨테이너 상태 확인\n"
            "- 로컬 환경: `ollama serve` 명령으로 서버 시작\n"
            "- 포트 확인: 기본 포트 11434가 사용 가능한지 확인"
        )
    elif "설치되어 있지 않습니다" in error_msg or "not found" in msg:
        st.info(
            "**모델 미설치**\n\n"
            f"- Docker: `docker compose exec ollama ollama pull {settings.ollama_model}`\n"
            f"- 로컬: `ollama pull {settings.ollama_model}`\n"
            "- 설치된 모델 확인: `ollama list`"
        )
    elif "시간 초과" in error_msg or "timeout" in msg:
        st.info(
            "**응답 시간 초과**\n\n"
            "- 모델 첫 로딩 시 수십 초가 소요될 수 있습니다. 잠시 후 재시도하세요.\n"
            "- 이미지 크기가 너무 크면 처리가 느려집니다 (50MB 이하 권장).\n"
            "- 시스템 메모리(RAM)가 충분한지 확인하세요 (8GB 이상 권장)."
        )
    elif "500" in msg or "internal server error" in msg:
        st.info(
            "**Ollama 서버 내부 오류 (500)**\n\n"
            "- 모델 로딩 중일 수 있습니다. 1~2분 후 재시도하세요.\n"
            "- 메모리 부족: `docker stats`로 리소스 사용량 확인\n"
            "- Ollama 로그 확인: `docker compose logs ollama`\n"
            "- 서버 재시작: `docker compose restart ollama`"
        )
    else:
        st.info("Ollama 서버가 실행 중인지 확인해주세요: `ollama serve`")


# 페이지: 도면 분석
# ─────────────────────────────────────────────

def page_analyze():
    st.markdown(
        f'<div class="page-header">'
        f'<h1>{_icon("robot", 28)} 도면 분석</h1>'
        f'<p>AI가 도면을 분석하여 설명, 분류, 질문 답변을 제공합니다.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "분석할 도면 업로드",
        type=["png", "jpg", "jpeg"],
        key="analyze_upload",
    )

    if not uploaded:
        # 빈 상태 안내 카드
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(
                f'<div class="feature-card"><div class="icon">{_icon("pencil", 36)}</div>'
                f'<h4>설명 생성</h4>'
                f'<p>AI가 도면의 구조와 특징을 자동으로 설명합니다</p></div>',
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f'<div class="feature-card"><div class="icon">{_icon("tag", 36)}</div>'
                f'<h4>자동 분류</h4>'
                f'<p>도면의 카테고리를 AI가 자동으로 판별합니다</p></div>',
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f'<div class="feature-card"><div class="icon">{_icon("chat", 36)}</div>'
                f'<h4>Q&A</h4>'
                f'<p>도면에 대해 자유롭게 질문하고 답변을 받으세요</p></div>',
                unsafe_allow_html=True,
            )
        return

    safe_name = _sanitize_filename(uploaded.name)
    temp_path = Path(tempfile.gettempdir()) / f"drawingllm_analyze_{uuid.uuid4().hex[:8]}_{safe_name}"
    try:
        with open(temp_path, "wb") as f:
            f.write(uploaded.getbuffer())
    except OSError as e:
        st.error(f"파일 저장 실패: {e}")
        return

    st.image(str(temp_path), caption="분석 대상 도면", width=500)

    tab_desc, tab_class, tab_qa = st.tabs(["설명 생성", "자동 분류", "Q&A"])

    try:
        pipeline = get_pipeline()
    except Exception as e:
        st.error(f"파이프라인 초기화 실패: {e}")
        temp_path.unlink(missing_ok=True)
        return

    with tab_desc:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("설명 생성 시작", key="gen_desc", type="primary"):
            try:
                # 스트리밍 응답: 토큰 단위로 즉시 표시
                llm = pipeline._llm
                if llm is None:
                    st.warning("[오류] LLM이 초기화되지 않았습니다.")
                else:
                    # 프롬프트: describe_drawing과 동일 (컨텍스트 없는 버전)
                    prompt = """You are an expert mechanical engineer analyzing an engineering drawing.
Please describe this technical drawing in detail, including:

1. **Part Type**: What type of component or assembly is shown?
2. **Key Features**: Main geometric features, holes, slots, chamfers, etc.
3. **Dimensions**: Notable dimensions or tolerances if visible.
4. **Material**: Material specification if indicated.
5. **Application**: Likely application or industry use.
6. **Drawing Standard**: Drawing projection method (1st/3rd angle), scale, etc.

Provide your analysis in both English and Korean (한국어).
Be specific and technical in your description."""

                    num_predict = settings.llm_num_predict_describe

                    output_area = st.empty()
                    full_text = ""
                    with st.spinner("AI가 도면을 분석하고 있습니다..."):
                        for token in llm._generate_stream(prompt, str(temp_path), num_predict):
                            if token.startswith("[오류]"):
                                st.warning(token)
                                _show_llm_error_guide(token)
                                break
                            full_text += token
                            output_area.markdown(full_text + "▌")
                    if full_text:
                        output_area.markdown(full_text)
            except Exception as e:
                st.error(f"설명 생성 실패: {e}")
                _show_llm_error_guide(str(e))

    with tab_class:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # ── YOLO 빠른 분류 ──
        if pipeline._classifier:
            if st.button("YOLO 빠른 분류 (~50ms)", key="yolo_cls", type="primary"):
                with st.spinner("YOLO-cls 분류 중..."):
                    try:
                        yolo_result = pipeline.classify_with_detail(temp_path)
                        if yolo_result and yolo_result.category:
                            st.success(
                                f"**{yolo_result.category}** "
                                f"(신뢰도: {yolo_result.confidence:.1%})"
                            )
                            if yolo_result.needs_review:
                                st.warning("신뢰도가 낮아 수동 검토를 권장합니다.")

                            # Top-5 신뢰도 바
                            if yolo_result.top_k:
                                st.markdown("**Top-5 후보:**")
                                for name, conf in yolo_result.top_k:
                                    st.progress(conf, text=f"{name} ({conf:.1%})")
                        else:
                            st.info("분류 결과가 없습니다.")
                    except Exception as e:
                        st.error(f"YOLO 분류 실패: {e}")

            st.divider()

        # ── LLM 분류 (기존) ──
        st.markdown("**LLM 상세 분류** (Ollama)")
        custom_categories = st.text_input(
            "카테고리 목록 (쉼표 구분, 비우면 자동)",
            placeholder="engine, chassis, body, electrical, transmission",
        )
        if st.button("LLM 분류 실행", key="gen_class"):
            categories = [c.strip() for c in custom_categories.split(",") if c.strip()] if custom_categories else None
            with st.spinner("LLM 분류 중..."):
                try:
                    result = pipeline._llm.classify_drawing(temp_path, categories)
                    if result.startswith("[오류]"):
                        st.warning(result)
                        _show_llm_error_guide(result)
                    else:
                        st.code(result, language="json")
                except Exception as e:
                    st.error(f"분류 실패: {e}")
                    _show_llm_error_guide(str(e))

    with tab_qa:
        if "qa_history" not in st.session_state:
            st.session_state.qa_history = []

        for msg in st.session_state.qa_history:
            with st.chat_message(msg["role"], avatar="human" if msg["role"] == "user" else "assistant"):
                st.markdown(msg["content"])

        question = st.chat_input(
            "도면에 대해 질문하세요 (예: 이 부품의 재질은?)",
            key="qa_chat_input",
        )

        if question:
            st.session_state.qa_history.append({"role": "user", "content": question})
            with st.chat_message("user", avatar="human"):
                st.markdown(question)

            with st.chat_message("assistant", avatar="assistant"):
                try:
                    llm = pipeline._llm
                    if llm is None:
                        st.warning("[오류] LLM이 초기화되지 않았습니다.")
                    else:
                        prompt = (
                            f"You are an expert mechanical engineer. "
                            f"Answer the following question about this engineering drawing. "
                            f"Answer in the same language as the question.\n\n"
                            f"Question: {question}"
                        )
                        output_area = st.empty()
                        full_text = ""
                        with st.spinner("답변 생성 중..."):
                            for token in llm._generate_stream(prompt, str(temp_path), settings.llm_num_predict_qa):
                                if token.startswith("[오류]"):
                                    st.warning(token)
                                    _show_llm_error_guide(token)
                                    full_text = token
                                    break
                                full_text += token
                                output_area.markdown(full_text + "▌")
                        if full_text and not full_text.startswith("[오류]"):
                            output_area.markdown(full_text)
                        st.session_state.qa_history.append({"role": "assistant", "content": full_text})
                except Exception as e:
                    err_msg = f"답변 생성 실패: {e}"
                    st.error(err_msg)
                    _show_llm_error_guide(str(e))
                    st.session_state.qa_history.append({"role": "assistant", "content": err_msg})

        if st.session_state.qa_history:
            if st.button("대화 초기화", key="clear_qa"):
                st.session_state.qa_history = []
                st.rerun()

    temp_path.unlink(missing_ok=True)


# ─────────────────────────────────────────────
# 페이지: 도구 (Tier-3)
# ─────────────────────────────────────────────

def page_tools():
    st.markdown(
        f'<div class="page-header">'
        f'<h1>{_icon("build", 28)} 도구</h1>'
        f'<p>BOM 추출, 치수 비교, DXF 비교, 버전 이력 등 고급 기능을 제공합니다.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    tab_bom, tab_dim, tab_dxf_diff, tab_version, tab_feedback = st.tabs(
        ["BOM 추출", "치수 비교", "DXF 비교", "버전 이력", "피드백 통계"]
    )

    try:
        pipeline = get_pipeline()
    except Exception as e:
        st.error(f"파이프라인 초기화 실패: {e}")
        return

    all_records = pipeline.get_all_records()
    record_options = {
        f"{r.drawing_id} — {r.file_name}": r.drawing_id
        for r in all_records
    }

    # ── BOM 추출 ──
    with tab_bom:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if not record_options:
            st.info("등록된 도면이 없습니다. 먼저 도면을 등록하세요.")
        else:
            selected_bom = st.selectbox(
                "도면 선택",
                list(record_options.keys()),
                key="bom_drawing",
            )
            use_llm_bom = st.checkbox("LLM 폴백 사용", key="bom_use_llm")
            if st.button("BOM 추출", key="btn_bom", type="primary"):
                drawing_id = record_options[selected_bom]
                with st.spinner("BOM 추출 중..."):
                    try:
                        result = pipeline.extract_bom(drawing_id, use_llm=use_llm_bom)
                        if result.get("error"):
                            st.error(result["error"])
                        elif result.get("entries"):
                            st.success(
                                f"BOM {len(result['entries'])}건 추출 "
                                f"(신뢰도: {result['confidence']:.0%}, "
                                f"소스: {result['source']})"
                            )
                            import pandas as pd
                            df = pd.DataFrame(result["entries"])
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.warning("BOM을 추출할 수 없습니다. OCR 텍스트에 테이블 구조가 없을 수 있습니다.")
                    except Exception as e:
                        st.error(f"BOM 추출 실패: {e}")

    # ── 치수 비교 ──
    with tab_dim:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if len(record_options) < 2:
            st.info("치수 비교를 위해 최소 2개의 도면이 필요합니다.")
        else:
            col1, col2 = st.columns(2)
            keys_list = list(record_options.keys())
            with col1:
                sel_a = st.selectbox("도면 A", keys_list, key="dim_a")
            with col2:
                sel_b = st.selectbox(
                    "도면 B",
                    keys_list,
                    index=min(1, len(keys_list) - 1),
                    key="dim_b",
                )
            if st.button("치수 비교", key="btn_dim", type="primary"):
                id_a = record_options[sel_a]
                id_b = record_options[sel_b]
                with st.spinner("치수 비교 중..."):
                    try:
                        result = pipeline.compare_dimensions(id_a, id_b)
                        if result.get("error"):
                            st.error(result["error"])
                        else:
                            sim = result.get("similarity", 0.0)
                            st.metric("치수 유사도", f"{sim:.1%}")

                            matched = result.get("matched", [])
                            changed = result.get("changed", [])
                            only_a = result.get("only_in_a", [])
                            only_b = result.get("only_in_b", [])

                            if matched:
                                st.markdown(f"**일치 ({len(matched)}건)**")
                                import pandas as pd
                                df_m = pd.DataFrame([
                                    {
                                        "타입": m["a"].get("dim_type", ""),
                                        "값_A": m["a"].get("value", ""),
                                        "값_B": m["b"].get("value", ""),
                                        "단위": m["a"].get("unit", ""),
                                    }
                                    for m in matched
                                ])
                                st.dataframe(df_m, use_container_width=True)

                            if changed:
                                st.markdown(f"**변경 ({len(changed)}건)**")
                                import pandas as pd
                                df_c = pd.DataFrame([
                                    {
                                        "타입": c["a"].get("dim_type", ""),
                                        "값_A": c["a"].get("value", ""),
                                        "값_B": c["b"].get("value", ""),
                                        "차이": c.get("diff", 0),
                                    }
                                    for c in changed
                                ])
                                st.dataframe(df_c, use_container_width=True)

                            if only_a:
                                st.markdown(f"**A에만 존재 ({len(only_a)}건)**")
                                import pandas as pd
                                st.dataframe(pd.DataFrame(only_a), use_container_width=True)

                            if only_b:
                                st.markdown(f"**B에만 존재 ({len(only_b)}건)**")
                                import pandas as pd
                                st.dataframe(pd.DataFrame(only_b), use_container_width=True)

                            if not matched and not changed and not only_a and not only_b:
                                st.info("비교할 치수가 없습니다.")
                    except Exception as e:
                        st.error(f"치수 비교 실패: {e}")

    # ── DXF 비교 ──
    with tab_dxf_diff:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            dxf_a = st.file_uploader("DXF 파일 A", type=["dxf"], key="dxf_diff_a")
        with col_b:
            dxf_b = st.file_uploader("DXF 파일 B", type=["dxf"], key="dxf_diff_b")

        if dxf_a and dxf_b:
            if st.button("DXF 비교", key="btn_dxf_diff", type="primary"):
                import tempfile as _tmpf
                tmp_a = Path(_tmpf.mktemp(suffix=".dxf", prefix="drawingllm_diff_"))
                tmp_b = Path(_tmpf.mktemp(suffix=".dxf", prefix="drawingllm_diff_"))
                try:
                    tmp_a.write_bytes(dxf_a.read())
                    tmp_b.write_bytes(dxf_b.read())
                    with st.spinner("DXF 비교 중..."):
                        result = pipeline.compare_dxf(str(tmp_a), str(tmp_b))
                        col_m, col_oa, col_ob = st.columns(3)
                        col_m.metric("일치 엔티티", result.get("matched_count", 0))
                        col_oa.metric("A에만 존재", result.get("only_in_a_count", 0))
                        col_ob.metric("B에만 존재", result.get("only_in_b_count", 0))

                        layer_diff = result.get("layer_diff", {})
                        if layer_diff:
                            st.markdown("**레이어 차이**")
                            import pandas as pd
                            layer_data = []
                            for k, v in layer_diff.items():
                                if isinstance(v, (list, set)):
                                    for item in v:
                                        layer_data.append({"구분": k, "레이어": item})
                                else:
                                    layer_data.append({"구분": k, "레이어": str(v)})
                            if layer_data:
                                st.dataframe(pd.DataFrame(layer_data), use_container_width=True)

                        summary = result.get("summary", {})
                        if summary:
                            st.markdown("**요약**")
                            for k, v in summary.items():
                                st.write(f"- **{k}**: {v}")
                except Exception as e:
                    st.error(f"DXF 비교 실패: {e}")
                finally:
                    tmp_a.unlink(missing_ok=True)
                    tmp_b.unlink(missing_ok=True)
        else:
            st.info("두 DXF 파일을 업로드하면 구조 차이를 비교합니다.")

    # ── 버전 이력 ──
    with tab_version:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        version_history = pipeline.get_version_history()
        if not version_history:
            st.info("버전 정보가 있는 부품번호가 없습니다.")
        else:
            # 부품번호 선택 (버전이 2개 이상인 것 먼저 표시)
            sorted_pns = sorted(
                version_history.keys(),
                key=lambda pn: (-version_history[pn], pn),
            )
            pn_labels = [f"{pn} ({version_history[pn]}건)" for pn in sorted_pns]

            pn_input = st.text_input(
                "부품번호 검색",
                placeholder="부품번호를 입력하세요...",
                key="version_pn_input",
            )

            if pn_input:
                filtered = [pn for pn in sorted_pns if pn_input.upper() in pn.upper()]
            else:
                filtered = sorted_pns[:50]  # 상위 50개

            if filtered:
                selected_pn = st.selectbox(
                    "부품번호 선택",
                    filtered,
                    format_func=lambda pn: f"{pn} ({version_history.get(pn, 0)}건)",
                    key="version_pn_select",
                )
                if selected_pn:
                    versions = pipeline.get_versions(selected_pn)
                    if versions:
                        st.markdown(f"**{selected_pn}** — {len(versions)}개 버전")
                        import pandas as pd
                        df = pd.DataFrame([
                            {
                                "버전": v.revision,
                                "Drawing ID": v.drawing_id,
                                "파일명": v.file_name,
                                "카테고리": v.category,
                                "등록 시각": v.registered_at or "—",
                            }
                            for v in versions
                        ])
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("해당 부품번호의 도면이 없습니다.")
            else:
                st.info("검색 결과가 없습니다.")

    # ── 피드백 통계 ──
    with tab_feedback:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        try:
            fb_store = _get_feedback_store_cached()
            stats = fb_store.get_feedback_stats()

            col_total, col_pos, col_neg = st.columns(3)
            col_total.metric("전체 피드백", stats["total"])
            col_pos.metric("관련 (👍)", stats["relevant"])
            col_neg.metric("무관 (👎)", stats["irrelevant"])

            if stats["total"] > 0 and (stats["relevant"] + stats["irrelevant"]) > 0:
                precision = stats["relevant"] / (stats["relevant"] + stats["irrelevant"])
                st.metric("검색 만족도", f"{precision:.1%}")

            # 카테고리별 통계
            by_cat = stats.get("by_category", {})
            if by_cat:
                st.markdown("**카테고리별 피드백**")
                import pandas as pd
                cat_data = []
                for cat_name, cat_stats in by_cat.items():
                    cat_data.append({
                        "카테고리": cat_name,
                        "전체": cat_stats["total"],
                        "관련": cat_stats["relevant"],
                        "무관": cat_stats["irrelevant"],
                    })
                st.dataframe(pd.DataFrame(cat_data), use_container_width=True)

            # 최근 피드백
            recent = fb_store.get_recent(limit=20)
            if recent:
                st.markdown("**최근 피드백**")
                import pandas as pd
                df_recent = pd.DataFrame(recent)
                display_cols = ["created_at", "query_text", "drawing_id", "relevance", "score"]
                available_cols = [c for c in display_cols if c in df_recent.columns]
                st.dataframe(df_recent[available_cols], use_container_width=True)

            # 내보내기 버튼
            col_exp_jsonl, col_exp_csv = st.columns(2)
            with col_exp_jsonl:
                if st.button("학습 데이터 내보내기 (JSONL)", key="export_jsonl"):
                    path = fb_store.export_training_pairs()
                    st.success(f"내보내기 완료: {path}")
            with col_exp_csv:
                if st.button("전체 피드백 내보내기 (CSV)", key="export_csv"):
                    path = fb_store.export_csv()
                    st.success(f"내보내기 완료: {path}")

        except Exception as e:
            st.error(f"피드백 통계 로딩 실패: {e}")


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────

def main():
    page = render_sidebar()

    if page == "대시보드":
        page_dashboard()
    elif page == "도면 등록":
        page_register()
    elif page == "도면 검색":
        page_search()
    elif page == "도면 분석":
        page_analyze()
    elif page == "도구":
        page_tools()


if __name__ == "__main__":
    main()
