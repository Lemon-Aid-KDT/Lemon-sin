"""
DrawingLLM 메인 파이프라인

도면 등록, 검색, 분석의 전체 워크플로우를 오케스트레이션한다.

흐름:
  도면 등록: 이미지 → OCR → 임베딩 생성 → 벡터 DB 저장 → LLM 메타데이터
  도면 검색: 쿼리 → 임베딩 → 벡터 DB 검색 → 결과 반환
  도면 분석: 이미지 → LLM → 설명/분류/Q&A
"""

import os
import json
import uuid
import shutil
from pathlib import Path
from dataclasses import dataclass, field

from loguru import logger

from core.ocr import DrawingOCR, OCRResult
from core.embeddings import ImageEmbedder, TextEmbedder
from core.vector_store import VectorStore, SearchResult
from core.llm import DrawingLLM, AnalysisContext
from core.classifier import DrawingClassifier, ClassificationResult
from core.detector import DrawingDetector, DetectionResult
from core.ocr import RegionOCRResult
from core.gnn import GNNEmbedder
from core.dxf_renderer import DXFRenderer
from core.reranker import CrossEncoderReranker
from core.record_store import RecordStore

# ─────────────────────────────────────────────
# 카테고리 → 대표 재질 매핑 (C-1 전략)
# ─────────────────────────────────────────────
# YOLO-cls 분류 결과(93.87% 정확도)를 기반으로
# OCR에서 재질을 추출하지 못한 경우 대표 재질을 추론한다.
# 값은 리스트이며, 첫 번째가 가장 대표적인 재질이다.
CATEGORY_MATERIAL_MAP: dict[str, list[str]] = {
    # ── 샤프트/축 ──
    "Shafts": ["S45C", "SUS304"],
    "Rotary_Shafts": ["S45C", "SUJ2"],
    "Rods": ["S45C", "SUS304"],
    # ── 베어링 계열 ──
    "Bearings_with_Holder": ["SUJ2"],
    "bearing_UCP": ["FC250", "SUJ2"],
    "bearing_UCF": ["FC250", "SUJ2"],
    "bearing_UCFC": ["FC250", "SUJ2"],
    "bearing_UCFL": ["FC250", "SUJ2"],
    "bearing_UCFS": ["FC250", "SUJ2"],
    "bearing_UCT": ["FC250", "SUJ2"],
    "bearing_UKP": ["FC250", "SUJ2"],
    "bearing_UKFC": ["FC250", "SUJ2"],
    "bearing_UKFL": ["FC250", "SUJ2"],
    "bearing_UKFS": ["FC250", "SUJ2"],
    "bearing_UKT": ["FC250", "SUJ2"],
    "bearing_H_ADAPTER": ["S45C"],
    "bearing_SN플러머블록": ["FC250", "SUJ2"],
    "bearing_TAKEUP": ["FC250", "SUJ2"],
    # ── 기어/전동 ──
    "Gears": ["S45C", "SCM415", "MC Nylon"],
    "Timing_Pulleys": ["S45C", "A5052"],
    "Sprockets_and_Chains": ["S45C", "SUS304"],
    "Flat_Belts_and_Round_Belts": ["Urethane", "Rubber"],
    # ── 리니어 모션 ──
    "Ball_Screws": ["SUS304", "SCM415"],
    "Ball_Splines": ["SUJ2", "SUS304"],
    "Linear_Bushings": ["SUJ2"],
    "Linear_Guides": ["SUS440C", "SUJ2"],
    "Slide_Rails": ["SUS304", "SPCC"],
    "Slide_Screws": ["SUS304"],
    # ── 체결/나사 ──
    "Screws": ["SCM435", "SUS304"],
    "Bolts_and_Nuts": ["SCM435", "SUS304"],
    "Washers": ["SUS304", "SPCC"],
    # ── 알루미늄 프레임 ──
    "Aluminum_Frames": ["A6063-T5"],
    "Brackets": ["A5052", "SPCC"],
    "Angles": ["A6063", "SS400"],
    "Ribs_and_Angle_Plates": ["SS400", "A5052"],
    # ── 위치결정/핀 ──
    "Locating_Pins": ["SUJ2", "SUS420J2"],
    "Locating_and_Guide_Components": ["SUJ2", "SUS304"],
    "Hinge_Pins": ["SUS304", "S45C"],
    "Plungers": ["SUS304", "S45C"],
    # ── 포스트/컬럼 ──
    "Posts": ["S45C", "SUS304"],
    "Set_Collars": ["S45C", "SUS304"],
    "Holders_for_Shaft": ["S45C", "A5052"],
    # ── 공압/실린더 ──
    "Cylinders": ["A6063", "SUS304"],
    "Manifolds": ["A5052", "SUS304"],
    "Fitting_and_Nozzles": ["SUS304", "Brass"],
    "Pipes_Fitting_Valves": ["SUS304", "SUS316"],
    "Pipe_Frames": ["SS400", "STKM"],
    # ── 스프링 ──
    "Springs": ["SWP-A", "SUS304-WPB"],
    # ── 수지/우레탄 ──
    "Urethanes": ["Urethane"],
    "Resin_Plates": ["POM", "MC Nylon"],
    # ── 컨베이어/스테이지 ──
    "Conveyors": ["A5052", "SUS304"],
    "Stages": ["A5052", "SUS304"],
    # ── 자동차 ──
    "Wheels": ["A6061-T6"],
    "Tires": ["Rubber"],
    "Suspension": ["S50C", "SUP"],
    "Brakes": ["FC250", "SUS304"],
    "Powertrain": ["SCM420", "S45C"],
    "Clutches": ["S45C", "SCM415"],
    "Pistons": ["AC8A", "A4032"],
    "Differential": ["SCM420"],
    "Turbocharger": ["Inconel", "SUS310S"],
    "Flanges": ["SS400", "SUS304"],
    "Housing": ["FC250", "ADC12"],
    "Airbag_Module": ["PA66", "SUS304"],
    # ── 기타 ──
    "Couplings": ["S45C", "A5052"],
    "Rollers": ["SUS304", "S45C"],
    "Casters": ["SUS304", "Rubber"],
    "Pulls": ["A5052", "SUS304"],
    "Levers": ["S45C", "SUS304"],
    "Clamps": ["S45C", "SUS304"],
    "Cover_Panels": ["SPCC", "A5052"],
    "Antivibration": ["Rubber", "Urethane"],
    "Simplified_Adjustment_Units": ["A5052"],
    "Actuator": ["A6063", "SUS304"],
    "Sanitary_Vacuum_Tanks": ["SUS316L"],
}


@dataclass
class DrawingRecord:
    """등록된 도면 레코드"""
    drawing_id: str
    file_path: str
    file_name: str
    ocr_text: str = ""
    part_numbers: list[str] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
    materials: list[str] = field(default_factory=list)
    category: str = ""
    description: str = ""
    metadata: dict = field(default_factory=dict)
    # YOLO-cls 분류 결과 (기본값이 있어 기존 records.json과 하위 호환)
    yolo_confidence: float = 0.0
    yolo_needs_review: bool = False
    yolo_top_k: list = field(default_factory=list)  # [(카테고리, 신뢰도), ...]
    # YOLO-det 영역 탐지 결과 (Phase 3, 하위 호환)
    detected_regions: list = field(default_factory=list)    # [{"class", "bbox", "confidence"}, ...]
    title_block_data: dict = field(default_factory=dict)    # 파싱된 표제란 (도번, 재질, 척도 등)
    parts_table_data: dict = field(default_factory=dict)    # 파싱된 부품표 (BOM)
    detection_enhanced: bool = False                        # 탐지 기반 OCR 적용 여부
    dxf_path: str = ""                                      # 연관 DXF 파일 경로 (GNN용)
    similar_drawings: list = field(default_factory=list)     # 유사도면 알림 [{drawing_id, score, file_name}]
    registered_at: str = ""                                  # ISO timestamp (등록 시각)
    revision: int = 1                                        # 동일 부품번호 내 버전


class DrawingPipeline:
    """도면 처리 메인 파이프라인"""

    def __init__(
        self,
        upload_dir: str = "./data/sample_drawings",
        vector_store_dir: str = "./data/vector_store",
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "qwen3.5:9b",
        clip_model: str = "ViT-L-14",
        clip_pretrained: str = "datacomp_xl_s13b_b90k",
        clip_finetuned_path: str = "",
        ocr_lang: str = "korean",
        ocr_fast_mode: bool = False,
        yolo_cls_model: str = "",
        yolo_cls_confidence: float = 0.5,
        yolo_cls_device: str = "",
        category_keywords_path: str = "",
        yolo_det_model: str = "",
        yolo_det_confidence: float = 0.3,
        yolo_det_iou: float = 0.5,
        yolo_det_device: str = "",
        yolo_cls_sha256: str = "",
        yolo_det_sha256: str = "",
        llm_rate_limit_rpm: int = 0,
        image_weight: float = 0.15,
        text_weight: float = 0.85,
        gnn_model: str = "",
        gnn_embedding_dim: int = 256,
        gnn_weight: float = 0.0,
        gnn_device: str = "",
        gnn_k_neighbors: int = 8,
        reranker_enabled: bool = False,
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        reranker_weight: float = 0.7,
        reranker_top_k_multiplier: int = 3,
        use_sqlite: bool = True,
        sqlite_db_path: str = "",
    ):
        self.upload_dir = Path(upload_dir)
        self._image_weight = image_weight
        self._text_weight = text_weight
        self._gnn_weight = gnn_weight
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        # 컴포넌트 초기화 (지연 로딩)
        self._ocr = DrawingOCR(lang=ocr_lang, fast_mode=ocr_fast_mode)
        self._image_embedder = ImageEmbedder(
            model_name=clip_model,
            pretrained=clip_pretrained,
            finetuned_path=clip_finetuned_path,
        )
        self._text_embedder = TextEmbedder()
        self._vector_store = VectorStore(persist_dir=vector_store_dir)
        self._llm = DrawingLLM(
            base_url=ollama_url, model=ollama_model,
            rate_limit_rpm=llm_rate_limit_rpm,
        )

        # YOLO-cls 분류기 (모델 경로가 있으면 초기화)
        self._classifier: DrawingClassifier | None = None
        if yolo_cls_model and Path(yolo_cls_model).exists():
            try:
                self._classifier = DrawingClassifier(
                    model_path=yolo_cls_model,
                    confidence_threshold=yolo_cls_confidence,
                    device=yolo_cls_device,
                    expected_sha256=yolo_cls_sha256,
                )
                logger.info(f"YOLO-cls 분류기 설정 완료: {yolo_cls_model}")
            except Exception as e:
                logger.warning(f"YOLO-cls 분류기 초기화 실패 (비활성): {e}")
                self._classifier = None
        else:
            if yolo_cls_model:
                logger.warning(f"YOLO-cls 모델 파일 없음 (비활성): {yolo_cls_model}")

        # 카테고리 키워드 로드 (검색 임베딩 보강용)
        self._category_keywords: dict[str, str] = {}
        if category_keywords_path:
            kw_path = Path(category_keywords_path)
            if kw_path.exists():
                try:
                    with open(kw_path, "r", encoding="utf-8") as f:
                        kw_data = json.load(f)
                    self._category_keywords = kw_data.get("keywords", {})
                    logger.info(
                        f"카테고리 키워드 로드 완료: {len(self._category_keywords)}개 카테고리"
                    )
                except Exception as e:
                    logger.warning(f"카테고리 키워드 로드 실패 (계속 진행): {e}")
            else:
                logger.warning(f"카테고리 키워드 파일 없음: {kw_path}")

        # YOLO-det 탐지기 (모델 경로가 있으면 초기화)
        self._detector: DrawingDetector | None = None
        if yolo_det_model and Path(yolo_det_model).exists():
            try:
                self._detector = DrawingDetector(
                    model_path=yolo_det_model,
                    confidence_threshold=yolo_det_confidence,
                    iou_threshold=yolo_det_iou,
                    device=yolo_det_device,
                    expected_sha256=yolo_det_sha256,
                )
                logger.info(f"YOLO-det 탐지기 설정 완료: {yolo_det_model}")
            except Exception as e:
                logger.warning(f"YOLO-det 탐지기 초기화 실패 (비활성): {e}")
                self._detector = None
        else:
            if yolo_det_model:
                logger.warning(f"YOLO-det 모델 파일 없음 (비활성): {yolo_det_model}")

        # GNN 구조 임베더 (DXF 구조 유사도 검색)
        self._gnn_embedder: GNNEmbedder | None = None
        if gnn_model and Path(gnn_model).exists():
            try:
                self._gnn_embedder = GNNEmbedder(
                    model_path=gnn_model,
                    embedding_dim=gnn_embedding_dim,
                    device=gnn_device,
                    k_neighbors=gnn_k_neighbors,
                )
                logger.info(f"GNN 임베더 설정 완료: {gnn_model}")
            except Exception as e:
                logger.warning(f"GNN 임베더 초기화 실패 (비활성): {e}")
                self._gnn_embedder = None
        else:
            if gnn_model:
                logger.warning(f"GNN 모델 파일 없음 (비활성): {gnn_model}")

        # Reranker (Cross-Encoder 2차 정렬)
        self._reranker: CrossEncoderReranker | None = None
        self._reranker_top_k_mult = reranker_top_k_multiplier
        if reranker_enabled:
            try:
                self._reranker = CrossEncoderReranker(
                    model_name=reranker_model,
                    reranker_weight=reranker_weight,
                )
                logger.info(f"Reranker 설정 완료: {reranker_model}")
            except Exception as e:
                logger.warning(f"Reranker 초기화 실패 (비활성): {e}")
                self._reranker = None

        # 도면 레코드 저장
        self._records: dict[str, DrawingRecord] = {}
        self._records_file = Path(vector_store_dir) / "records.json"
        self._use_sqlite = use_sqlite
        self._record_store: RecordStore | None = None

        # SQLite 모드: records.db가 존재하거나, 명시적으로 use_sqlite=True인 경우
        _sqlite_path = sqlite_db_path or str(Path(vector_store_dir) / "records.db")
        if self._use_sqlite:
            try:
                self._record_store = RecordStore(db_path=_sqlite_path)
                # DB에 레코드가 없고 records.json이 있으면 자동 마이그레이션
                if self._record_store.count() == 0 and self._records_file.exists():
                    logger.info("SQLite DB가 비어있음 — records.json에서 자동 마이그레이션")
                    self._load_records_json()
                    self._migrate_records_to_sqlite()
                else:
                    self._load_records_sqlite()
                logger.info(f"SQLite 레코드 저장소 활성: {_sqlite_path}")
            except Exception as e:
                logger.warning(f"SQLite 초기화 실패, JSON 폴백: {e}")
                self._use_sqlite = False
                self._record_store = None
                self._load_records_json()
        else:
            self._load_records_json()

        # 버전 관리 인덱스 (part_number → [drawing_id, ...])
        self._version_index: dict[str, list[str]] = {}
        self._build_version_index()

        # v5.4 통합 엔진 (lazy init)
        self._search_engine = None
        self._vlm_orchestrator = None
        self._comparison_engine = None
        self._universal_renderer = None

        logger.info("DrawingPipeline 초기화 완료")

    # ─────────────────────────────────────────────
    # 버전 관리
    # ─────────────────────────────────────────────

    def _build_version_index(self) -> None:
        """part_number → [drawing_id, ...] 인덱스를 빌드한다."""
        self._version_index = {}
        for did, rec in self._records.items():
            pns = rec.part_numbers if isinstance(rec, DrawingRecord) else (rec.get("part_numbers") or [])
            for pn in pns:
                if pn:
                    self._version_index.setdefault(pn, []).append(did)
        # 등록 시간순 정렬
        for pn in self._version_index:
            self._version_index[pn].sort(
                key=lambda d: (
                    self._records[d].registered_at
                    if isinstance(self._records.get(d), DrawingRecord)
                    else self._records.get(d, {}).get("registered_at", "")
                )
            )

    # ─────────────────────────────────────────────
    # 텍스트 보강
    # ─────────────────────────────────────────────

    def _build_rich_text(self, ocr_text: str, category: str) -> str:
        """임베딩용 보강 텍스트 생성 (OCR + 카테고리명 + 카테고리 키워드).

        카테고리 키워드(category_keywords.json)를 병합하여
        E5 텍스트 임베딩의 시맨틱 커버리지를 높인다.

        Args:
            ocr_text: OCR 추출 텍스트
            category: 카테고리 식별자 (예: "Shafts", "bearing_UCP")

        Returns:
            보강된 텍스트 문자열
        """
        parts: list[str] = []
        if ocr_text:
            parts.append(ocr_text[:500])
        if category:
            # 언더스코어를 공백으로 변환해 자연어화
            parts.append(category.replace("_", " "))
        # 카테고리 키워드 추가 (한영 혼합 시맨틱 키워드)
        kw = self._category_keywords.get(category, "")
        if kw:
            parts.append(kw)
        return " ".join(parts).strip()

    # ─────────────────────────────────────────────
    # Phase 4: LLM 분석 컨텍스트 빌더
    # ─────────────────────────────────────────────

    def _build_analysis_context(
        self,
        ocr_result: OCRResult,
        category: str,
        yolo_confidence: float,
        yolo_top_k: list,
        detected_regions: list,
        title_block_data: dict,
        parts_table_data: dict,
    ) -> AnalysisContext:
        """OCR/YOLO 결과를 AnalysisContext로 조립한다.

        Args:
            ocr_result: OCR 추출 결과
            category: YOLO-cls 분류 카테고리
            yolo_confidence: YOLO-cls 신뢰도
            yolo_top_k: YOLO-cls 상위 K 예측
            detected_regions: YOLO-det 탐지 영역 (dict 리스트)
            title_block_data: 표제란 파싱 결과
            parts_table_data: 부품표 파싱 결과

        Returns:
            AnalysisContext: LLM 프롬프트 주입용 컨텍스트
        """
        return AnalysisContext(
            yolo_category=category,
            yolo_confidence=yolo_confidence,
            yolo_top_k=yolo_top_k or [],
            detected_regions=[
                r.get("class", "") for r in (detected_regions or [])
            ],
            title_block_data=title_block_data or {},
            parts_table_data=parts_table_data or {},
            part_numbers=ocr_result.part_numbers,
            dimensions=ocr_result.dimensions,
            materials=ocr_result.materials,
            ocr_text=ocr_result.full_text[:300],
        )

    def _build_analysis_context_from_record(
        self, record: DrawingRecord
    ) -> AnalysisContext:
        """DrawingRecord에서 AnalysisContext를 구성한다.

        describe/ask 등 기존 레코드 기반 분석에서 사용한다.

        Args:
            record: 등록된 도면 레코드

        Returns:
            AnalysisContext: LLM 프롬프트 주입용 컨텍스트
        """
        return AnalysisContext(
            yolo_category=record.category,
            yolo_confidence=record.yolo_confidence,
            yolo_top_k=record.yolo_top_k,
            detected_regions=[
                r.get("class", "") for r in record.detected_regions
            ],
            title_block_data=record.title_block_data,
            parts_table_data=record.parts_table_data,
            part_numbers=record.part_numbers,
            dimensions=record.dimensions,
            materials=record.materials,
            ocr_text=record.ocr_text[:300],
        )

    # ─────────────────────────────────────────────
    # OCR 결과 병합 (영역 탐지 기반)
    # ─────────────────────────────────────────────

    def _merge_ocr_results(
        self,
        base_ocr: OCRResult,
        region_results: list[RegionOCRResult],
    ) -> OCRResult:
        """기본 OCR 결과에 영역별 OCR 결과를 병합한다.

        표제란 → 부품번호/재질 우선 추출
        치수 영역 → 치수 추가
        부품표 → BOM 데이터 보강

        Args:
            base_ocr: 전체 이미지 OCR 결과 (기존)
            region_results: 영역별 OCR 결과 리스트

        Returns:
            OCRResult: 보강된 OCR 결과
        """
        # 기존 결과 복사 (원본 보존)
        merged_parts = list(base_ocr.part_numbers)
        merged_dims = list(base_ocr.dimensions)
        merged_materials = list(base_ocr.materials)
        merged_text_parts = [base_ocr.full_text] if base_ocr.full_text else []

        for region_ocr in region_results:
            sd = region_ocr.structured_data

            if region_ocr.region_class == "title_block":
                # 표제란에서 추출한 부품번호가 기존에 없으면 추가
                # (서브스트링 + 리딩제로 정규화로 퍼지 중복 방지)
                tb_pn = sd.get("drawing_number", "")
                if tb_pn:
                    import re as _re
                    _pn_upper = tb_pn.strip().upper()
                    _pn_norm = _re.sub(r"(?<=[A-Z])0+(?=\d)", "", _pn_upper)
                    _dup = False
                    for ep in merged_parts:
                        _ep_upper = ep.strip().upper()
                        _ep_norm = _re.sub(r"(?<=[A-Z])0+(?=\d)", "", _ep_upper)
                        if (_pn_upper == _ep_upper
                                or _pn_norm == _ep_norm
                                or (len(_pn_upper) >= 4 and _pn_upper in _ep_upper)
                                or (len(_ep_upper) >= 4 and _ep_upper in _pn_upper)):
                            _dup = True
                            break
                    if not _dup:
                        merged_parts.insert(0, tb_pn)  # 표제란 도번 최우선
                # 재질
                tb_mat = sd.get("material", "")
                if tb_mat and tb_mat not in merged_materials:
                    merged_materials.insert(0, tb_mat)

            elif region_ocr.region_class == "dimension_area":
                # 치수 영역에서 추가 치수 추출
                for dim in sd.get("dimensions", []):
                    if dim not in merged_dims:
                        merged_dims.append(dim)

            elif region_ocr.region_class == "parts_table":
                # 부품표 텍스트 추가
                if region_ocr.text:
                    merged_text_parts.append(region_ocr.text)

        merged_full_text = " ".join(merged_text_parts).strip()

        return OCRResult(
            full_text=merged_full_text,
            text_blocks=base_ocr.text_blocks,
            part_numbers=merged_parts,
            dimensions=merged_dims,
            materials=merged_materials,
            regions=region_results,
            detection_enhanced=True,
        )

    # ─────────────────────────────────────────────
    # 도면 등록
    # ─────────────────────────────────────────────

    def register_drawing(
        self,
        image_path: str | Path,
        category: str = "",
        use_llm: bool = True,
        copy_to_store: bool = True,
    ) -> DrawingRecord:
        """
        도면을 시스템에 등록한다.

        처리 순서:
          1. 파일 복사 (선택)
          2. OCR 텍스트 추출
          3. 이미지 임베딩 생성 (CLIP)
          4. 텍스트 임베딩 생성 (OCR 텍스트)
          5. 벡터 DB 저장
          6. LLM 메타데이터 생성 (선택)

        Args:
            image_path: 도면 이미지 경로
            category: 수동 카테고리 지정 (빈 문자열이면 자동)
            use_llm: LLM으로 설명/분류 생성 여부
            copy_to_store: 파일을 저장소로 복사할지 여부

        Returns:
            DrawingRecord: 등록된 도면 레코드
        """
        image_path = Path(image_path)
        drawing_id = str(uuid.uuid4())[:8]

        logger.info(f"도면 등록 시작: {image_path.name} (ID: {drawing_id})")

        # 1. 파일 복사
        if copy_to_store:
            dest_path = self.upload_dir / f"{drawing_id}_{image_path.name}"
            try:
                shutil.copy2(image_path, dest_path)
                stored_path = str(dest_path)
            except (OSError, shutil.SameFileError) as e:
                logger.warning(f"파일 복사 실패 (원본 경로 사용): {e}")
                stored_path = str(image_path)
        else:
            stored_path = str(image_path)

        # 1.5. DXF → PNG 변환 (DXF 파일이면 자동 렌더링)
        dxf_stored_path = ""
        if image_path.suffix.lower() == ".dxf":
            try:
                renderer = DXFRenderer()
                png_path = Path(stored_path).with_suffix(".png")
                renderer.render_to_png(Path(stored_path), png_path)
                dxf_stored_path = stored_path  # 원본 DXF 경로 보존
                stored_path = str(png_path)    # 이후 OCR/임베딩은 PNG로
                logger.info(f"DXF → PNG 변환 완료: {png_path.name}")
            except Exception as e:
                logger.error(f"DXF → PNG 변환 실패: {e}")
                raise

        # 2. OCR 텍스트 추출
        try:
            ocr_result: OCRResult = self._ocr.extract(stored_path)
        except Exception as e:
            logger.warning(f"OCR 실패 (계속 진행): {e}")
            ocr_result = OCRResult(full_text="")

        # 2.5. YOLO-det 영역 탐지 + 영역별 OCR (탐지기 활성 시)
        detected_regions = []
        title_block_data = {}
        parts_table_data = {}
        detection_enhanced = False
        if self._detector:
            try:
                det_result = self._detector.detect(stored_path)
                if det_result.regions:
                    region_ocr_results: list[RegionOCRResult] = []
                    for region in det_result.regions:
                        try:
                            cropped = self._detector.crop_region(stored_path, region)
                            region_ocr = self._ocr.extract_region(
                                cropped, region.class_name
                            )
                            region_ocr.bbox = region.bbox
                            region_ocr_results.append(region_ocr)
                        except Exception as crop_e:
                            logger.warning(
                                f"영역 OCR 실패 ({region.class_name}): {crop_e}"
                            )

                    if region_ocr_results:
                        ocr_result = self._merge_ocr_results(
                            ocr_result, region_ocr_results
                        )

                    detected_regions = [
                        {
                            "class": r.class_name,
                            "bbox": list(r.bbox),
                            "confidence": r.confidence,
                        }
                        for r in det_result.regions
                    ]
                    title_block_data = next(
                        (
                            r.structured_data
                            for r in region_ocr_results
                            if r.region_class == "title_block"
                        ),
                        {},
                    )
                    parts_table_data = next(
                        (
                            r.structured_data
                            for r in region_ocr_results
                            if r.region_class == "parts_table"
                        ),
                        {},
                    )
                    detection_enhanced = True
                    logger.info(
                        f"영역 탐지 OCR 완료: {len(det_result.regions)}개 영역"
                    )
            except Exception as e:
                logger.warning(f"영역 탐지/OCR 실패 (기본 OCR 결과 유지): {e}")

        # 2.7. YOLO-cls 자동분류 (카테고리 미지정 시)
        yolo_confidence = 0.0
        yolo_needs_review = False
        yolo_top_k = []
        if not category and self._classifier:
            try:
                yolo_result = self._classifier.classify(stored_path)
                category = yolo_result.category
                yolo_confidence = yolo_result.confidence
                yolo_needs_review = yolo_result.needs_review
                yolo_top_k = yolo_result.top_k
                logger.info(
                    f"YOLO-cls 자동분류: {category} "
                    f"(신뢰도: {yolo_confidence:.2%}, "
                    f"검토필요: {yolo_needs_review})"
                )
            except Exception as e:
                logger.warning(f"YOLO-cls 분류 실패 (계속 진행): {e}")

        # 2.8. 파일명 기반 부품번호 2차 보충 (OCR + 영역 OCR 모두 실패 시)
        if not ocr_result.part_numbers:
            filename_parts = DrawingOCR.extract_part_number_from_filename(image_path)
            if filename_parts:
                ocr_result.part_numbers = filename_parts
                logger.info(f"파일명 기반 부품번호 보충 (pipeline): {filename_parts}")

        # 2.9. 카테고리 기반 재질 추론 (OCR에서 재질 미검출 시)
        if not ocr_result.materials and category:
            inferred = CATEGORY_MATERIAL_MAP.get(category, [])
            if inferred:
                ocr_result.materials = list(inferred)
                logger.info(
                    f"카테고리 기반 재질 추론: {category} → {inferred}"
                )

        # 3. 이미지 임베딩
        try:
            image_embedding = self._image_embedder.embed_image(stored_path)
        except Exception as e:
            logger.error(f"이미지 임베딩 실패: {e}")
            raise

        # 4. 텍스트 임베딩 (OCR 텍스트 + 카테고리 + 키워드, passage용)
        text_for_embedding = self._build_rich_text(ocr_result.full_text, category)
        text_embedding = None
        if text_for_embedding:
            try:
                text_embedding = self._text_embedder.embed_passage(text_for_embedding)
            except Exception as e:
                logger.warning(f"텍스트 임베딩 실패 (계속 진행): {e}")

        # 4.5. GNN 구조 임베딩 (DXF 파일이 있고 GNN 임베더가 활성인 경우)
        gnn_embedding = None
        effective_dxf_path = dxf_stored_path or (
            str(image_path) if image_path.suffix.lower() == ".dxf" else ""
        )
        if effective_dxf_path and self._gnn_embedder:
            try:
                gnn_embedding = self._gnn_embedder.embed_dxf(effective_dxf_path)
                logger.info("GNN 구조 임베딩 생성 완료")
            except Exception as e:
                logger.warning(f"GNN 임베딩 실패 (계속 진행): {e}")

        # 5. 메타데이터 구성
        metadata = {
            "file_path": stored_path,
            "file_name": image_path.name,
            "category": category,
            "ocr_text": ocr_result.full_text[:500],  # ChromaDB 메타데이터 크기 제한
            "part_numbers": str(ocr_result.part_numbers),
        }

        # 6. 벡터 DB 저장
        self._vector_store.add_drawing(
            drawing_id=drawing_id,
            image_embedding=image_embedding,
            text_embedding=text_embedding,
            gnn_embedding=gnn_embedding,
            metadata=metadata,
        )

        # 7. LLM 메타데이터 (선택, Phase 4: 컨텍스트 주입)
        description = ""
        if use_llm:
            try:
                analysis_context = self._build_analysis_context(
                    ocr_result, category, yolo_confidence, yolo_top_k,
                    detected_regions, title_block_data, parts_table_data,
                )
                description = self._llm.describe_drawing(
                    stored_path, context=analysis_context
                )
            except Exception as e:
                logger.warning(f"LLM 설명 생성 실패 (계속 진행): {e}")

        # 레코드 저장
        import datetime as _dt
        _registered_at = _dt.datetime.now().isoformat()

        # 같은 part_number의 기존 버전 확인 → revision 증가
        _revision = 1
        for pn in (ocr_result.part_numbers or []):
            if pn in self._version_index:
                existing_ids = self._version_index[pn]
                max_rev = max(
                    (self._records[d].revision if isinstance(self._records.get(d), DrawingRecord)
                     else self._records.get(d, {}).get("revision", 1))
                    for d in existing_ids
                    if d in self._records
                ) if existing_ids else 0
                _revision = max_rev + 1
                break

        record = DrawingRecord(
            drawing_id=drawing_id,
            file_path=stored_path,
            file_name=image_path.name,
            ocr_text=ocr_result.full_text,
            part_numbers=ocr_result.part_numbers,
            dimensions=ocr_result.dimensions,
            materials=ocr_result.materials,
            category=category,
            description=description,
            metadata=metadata,
            yolo_confidence=yolo_confidence,
            yolo_needs_review=yolo_needs_review,
            yolo_top_k=yolo_top_k,
            detected_regions=detected_regions,
            title_block_data=title_block_data,
            parts_table_data=parts_table_data,
            detection_enhanced=detection_enhanced,
            dxf_path=dxf_stored_path,
            registered_at=_registered_at,
            revision=_revision,
        )
        self._records[drawing_id] = record
        self._save_records(single_record=record)

        # 버전 인덱스 갱신
        for pn in (ocr_result.part_numbers or []):
            if pn:
                self._version_index.setdefault(pn, []).append(drawing_id)

        # ── 유사도면 알림: 등록 직후 유사 도면 자동 검색 ──
        try:
            from config.settings import settings as _settings
            threshold = _settings.similarity_alert_threshold
            if threshold > 0:
                similar_results = self._vector_store.hybrid_search(
                    image_embedding=image_embedding,
                    text_embedding=text_embedding,
                    gnn_embedding=gnn_embedding,
                    top_k=6,
                    image_weight=self._image_weight,
                    text_weight=self._text_weight,
                    gnn_weight=self._gnn_weight,
                )
                similar_list = []
                for sr in similar_results:
                    if sr.drawing_id != drawing_id and sr.score >= threshold:
                        similar_list.append({
                            "drawing_id": sr.drawing_id,
                            "score": round(sr.score, 4),
                            "file_name": sr.metadata.get("file_name", ""),
                            "file_path": sr.metadata.get("file_path", ""),
                        })
                record.similar_drawings = similar_list
                if similar_list:
                    logger.info(
                        f"유사도면 알림: {len(similar_list)}건 "
                        f"(threshold={threshold})"
                    )
                    # 유사도면 정보 업데이트 저장
                    self._save_records(single_record=record)
        except Exception as e:
            logger.warning(f"유사도면 검색 실패 (계속 진행): {e}")

        logger.info(f"도면 등록 완료: {drawing_id} ({image_path.name})")
        return record

    def register_batch(
        self,
        directory: str | Path,
        category: str = "",
        use_llm: bool = False,
    ) -> list[DrawingRecord]:
        """
        디렉토리 내 모든 도면을 일괄 등록한다.

        Args:
            directory: 도면 이미지 디렉토리
            category: 공통 카테고리
            use_llm: LLM 사용 여부 (배치에서는 비활성 권장)

        Returns:
            list[DrawingRecord]: 등록된 레코드 목록
        """
        directory = Path(directory)
        extensions = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".pdf", ".dxf"}
        image_files = [f for f in directory.iterdir() if f.suffix.lower() in extensions]

        logger.info(f"배치 등록 시작: {len(image_files)}건 ({directory})")

        records = []
        for i, img_path in enumerate(image_files):
            try:
                record = self.register_drawing(
                    img_path, category=category, use_llm=use_llm
                )
                records.append(record)
                logger.info(f"[{i+1}/{len(image_files)}] 등록 완료: {img_path.name}")
            except Exception as e:
                logger.error(f"[{i+1}/{len(image_files)}] 등록 실패 ({img_path.name}): {e}")

        logger.info(f"배치 등록 완료: {len(records)}/{len(image_files)}건 성공")
        return records

    # ─────────────────────────────────────────────
    # 도면 검색
    # ─────────────────────────────────────────────

    def search_by_text(
        self, query: str, top_k: int = 5, category: str = "",
    ) -> list[SearchResult]:
        """
        자연어 쿼리로 도면을 검색한다.
        CLIP 텍스트 인코더를 사용하여 이미지-텍스트 크로스모달 검색을 수행한다.

        Args:
            query: 자연어 검색 쿼리 (예: "터보차저 배기측 가스켓")
            top_k: 반환 결과 수
            category: 카테고리 필터 (빈 문자열이면 전체 검색)

        Returns:
            list[SearchResult]: 유사도 순 검색 결과
        """
        logger.info(f"텍스트 검색: '{query}' (카테고리: {category or '전체'})")

        # 한/영 동의어 확장 (한글 쿼리 → 영문 기술 용어 추가)
        from core.ko_en_dict import expand_query as _expand_ko
        expanded_query = _expand_ko(query)

        # CLIP 텍스트 임베딩 (이미지 공간 — 확장된 쿼리 사용)
        clip_text_embedding = self._image_embedder.embed_text(expanded_query)

        # 텍스트 임베딩 (카테고리 키워드 추가 병합)
        if category and category in self._category_keywords:
            kw = self._category_keywords[category]
            expanded_query = f"{expanded_query} {kw}"
        text_embedding = self._text_embedder.embed(expanded_query)

        # 카테고리 필터 구성
        where_filter = {"category": category} if category else None

        # 하이브리드 검색 (reranker 사용 시 더 넓게 요청)
        fetch_k = top_k * (self._reranker_top_k_mult if self._reranker else 3)
        results = self._vector_store.hybrid_search(
            image_embedding=clip_text_embedding,
            text_embedding=text_embedding,
            top_k=fetch_k,
            image_weight=self._image_weight,
            text_weight=self._text_weight,
            gnn_weight=self._gnn_weight,
            where_filter=where_filter,
        )

        # Reranker 2차 정렬 (활성화 시)
        if self._reranker and results:
            results = self._reranker.rerank(query, results, top_k=len(results))

        # 동일 파일 중복 제거 (최고 점수 우선)
        seen_files: set[str] = set()
        deduped: list[SearchResult] = []
        for r in results:
            fname = r.metadata.get("file_name", r.drawing_id)
            if fname not in seen_files:
                seen_files.add(fname)
                deduped.append(r)
            if len(deduped) >= top_k:
                break

        logger.info(f"검색 결과: {len(deduped)}건 (중복 제거: {len(results) - len(deduped)}건)")
        return deduped

    def search_by_image(
        self,
        image_path: str | Path,
        top_k: int = 5,
        category: str = "",
        use_yolo_filter: bool = False,
    ) -> list[SearchResult]:
        """
        이미지로 유사 도면을 검색한다.

        Args:
            image_path: 쿼리 도면 이미지 경로
            top_k: 반환 결과 수
            category: 카테고리 필터 (수동 지정)
            use_yolo_filter: True이면 YOLO 분류 결과로 자동 필터

        Returns:
            list[SearchResult]: 유사도 순 검색 결과
        """
        logger.info(f"이미지 검색: {Path(image_path).name} (카테고리: {category or '전체'})")
        image_embedding = self._image_embedder.embed_image(image_path)

        # YOLO 자동 필터: 쿼리 이미지 분류 → 카테고리 프리필터
        yolo_category = ""
        if use_yolo_filter and self._classifier and not category:
            try:
                yolo_result = self._classifier.classify(image_path)
                if yolo_result.confidence >= self._classifier.confidence_threshold:
                    yolo_category = yolo_result.category
                    logger.info(
                        f"YOLO 자동 필터: {yolo_category} "
                        f"(신뢰도: {yolo_result.confidence:.2%})"
                    )
            except Exception as e:
                logger.warning(f"YOLO 자동 필터 실패 (전수 검색): {e}")

        effective_category = category or yolo_category
        where_filter = {"category": effective_category} if effective_category else None

        results = self._vector_store.search_by_image(
            image_embedding, top_k=top_k * 3, where_filter=where_filter,
        )

        # 동일 파일 중복 제거
        seen_files: set[str] = set()
        deduped: list[SearchResult] = []
        for r in results:
            fname = r.metadata.get("file_name", r.drawing_id)
            if fname not in seen_files:
                seen_files.add(fname)
                deduped.append(r)
            if len(deduped) >= top_k:
                break

        logger.info(f"검색 결과: {len(deduped)}건 (중복 제거: {len(results) - len(deduped)}건)")
        return deduped

    def search_by_part_number(self, part_number: str) -> list[DrawingRecord]:
        """
        부품번호로 도면을 검색한다 (인메모리 레코드 부분 일치).

        Args:
            part_number: 검색할 부품번호 (부분 일치)

        Returns:
            list[DrawingRecord]: 일치하는 도면 레코드 목록
        """
        query = part_number.strip().upper()
        if not query:
            return []

        logger.info(f"부품번호 검색: '{part_number}'")
        results: list[DrawingRecord] = []
        for record in self._records.values():
            for pn in record.part_numbers:
                if query in pn.upper():
                    results.append(record)
                    break

        logger.info(f"부품번호 검색 결과: {len(results)}건")
        return results

    def search_by_dxf(
        self,
        dxf_path: str | Path,
        top_k: int = 5,
        category: str = "",
    ) -> list[SearchResult]:
        """
        DXF 파일로 구조적으로 유사한 도면을 검색한다.

        Args:
            dxf_path: 쿼리 DXF 파일 경로
            top_k: 반환 결과 수
            category: 카테고리 필터 (빈 문자열이면 전체 검색)

        Returns:
            list[SearchResult]: 유사도 순 검색 결과
        """
        if not self._gnn_embedder:
            logger.warning("GNN 임베더가 비활성 상태입니다. DXF 구조 검색을 수행할 수 없습니다.")
            return []

        logger.info(f"DXF 구조 검색: {Path(dxf_path).name} (카테고리: {category or '전체'})")

        try:
            gnn_embedding = self._gnn_embedder.embed_dxf(dxf_path)
        except Exception as e:
            logger.error(f"DXF 임베딩 실패: {e}")
            return []

        where_filter = {"category": category} if category else None

        results = self._vector_store.search_by_gnn(
            gnn_embedding, top_k=top_k * 5, where_filter=where_filter,
        )

        # 동일 파일 중복 제거
        seen_files: set[str] = set()
        deduped: list[SearchResult] = []
        for r in results:
            fname = r.metadata.get("file_name", r.drawing_id)
            if fname not in seen_files:
                seen_files.add(fname)
                deduped.append(r)

        # v5.3: 구조 프로파일 기반 리랭킹 (엔티티 분포/개수/종횡비 보정)
        try:
            from core.dxf_reranker import extract_dxf_profile, rerank_dxf_results
            query_profile = extract_dxf_profile(dxf_path)
            if query_profile.entity_count > 0:
                deduped = rerank_dxf_results(query_profile, deduped)
        except Exception as e:
            logger.debug(f"DXF 리랭킹 스킵: {e}")

        deduped = deduped[:top_k]
        logger.info(f"DXF 검색 결과: {len(deduped)}건")
        return deduped

    # ─────────────────────────────────────────────
    # 도면 분석
    # ─────────────────────────────────────────────

    def describe(self, image_path: str | Path, drawing_id: str = "") -> str:
        """도면 설명 생성

        Args:
            image_path: 도면 이미지 경로
            drawing_id: 기존 레코드 ID (있으면 컨텍스트 자동 구성)

        Returns:
            str: 도면 설명 텍스트
        """
        context = None
        if drawing_id and (record := self.get_record(drawing_id)):
            context = self._build_analysis_context_from_record(record)
        return self._llm.describe_drawing(image_path, context=context)

    def classify(self, image_path: str | Path, categories: list[str] | None = None) -> str:
        """도면 분류

        카테고리 목록 지정 시 → Ollama LLM (기존 유지)
        미지정 시 → YOLO 우선, 실패 시 LLM 폴백
        """
        # 카테고리 지정 시 LLM 분류 (유연한 카테고리 처리)
        if categories:
            return self._llm.classify_drawing(image_path, categories)

        # YOLO-cls 빠른 분류 (미지정 시)
        if self._classifier:
            try:
                result = self._classifier.classify(image_path)
                if result.category:
                    return result.category
            except Exception as e:
                logger.warning(f"YOLO-cls 분류 실패, LLM 폴백: {e}")

        # LLM 폴백
        return self._llm.classify_drawing(image_path, categories)

    def classify_with_detail(
        self, image_path: str | Path
    ) -> ClassificationResult | None:
        """YOLO-cls 상세 분류 결과 반환 (Top-K 포함)

        Returns:
            ClassificationResult 또는 분류기 미설정 시 None
        """
        if not self._classifier:
            return None
        try:
            return self._classifier.classify(image_path)
        except Exception as e:
            logger.warning(f"YOLO-cls 상세 분류 실패: {e}")
            return None

    def ask(self, image_path: str | Path, question: str, drawing_id: str = "") -> str:
        """도면 Q&A

        Args:
            image_path: 도면 이미지 경로
            question: 사용자 질문
            drawing_id: 기존 레코드 ID (있으면 컨텍스트 자동 구성)

        Returns:
            str: 답변 텍스트
        """
        context = None
        if drawing_id and (record := self.get_record(drawing_id)):
            context = self._build_analysis_context_from_record(record)
        return self._llm.answer_question(image_path, question, context=context)

    # ─────────────────────────────────────────────
    # 유틸리티
    # ─────────────────────────────────────────────

    def delete_drawing(self, drawing_id: str) -> bool:
        """도면 삭제 (벡터 DB + 레코드)

        Returns:
            True: 삭제 성공, False: 해당 ID의 레코드 없음
        """
        # 벡터 DB에서 삭제 (존재하지 않아도 에러 없음)
        self._vector_store.delete_drawing(drawing_id)

        # 레코드에서 삭제
        deleted = False
        if drawing_id in self._records:
            del self._records[drawing_id]
            deleted = True

        if self._use_sqlite and self._record_store is not None:
            deleted = self._record_store.delete(drawing_id) or deleted
        elif deleted:
            self._save_records_json()

        if deleted:
            logger.info(f"도면 삭제 완료: {drawing_id}")
            return True

        logger.warning(f"삭제 대상 레코드 없음: {drawing_id}")
        return False

    def get_record(self, drawing_id: str) -> DrawingRecord | None:
        """도면 레코드 조회"""
        return self._records.get(drawing_id)

    def get_all_records(self) -> list[DrawingRecord]:
        """전체 도면 레코드 목록"""
        return list(self._records.values())

    def get_stats(self) -> dict:
        """시스템 통계"""
        vs_stats = self._vector_store.get_stats()
        stats = {
            "total_drawings": len(self._records),
            "vector_store": vs_stats,
            "ollama_healthy": self._llm.check_health_sync(),
        }

        # YOLO-cls 분류기 상태
        if self._classifier:
            healthy, msg = self._classifier.check_health()
            stats["yolo_classifier"] = {
                "enabled": True,
                "healthy": healthy,
                "message": msg,
                "num_classes": self._classifier.num_classes if healthy else 0,
            }
        else:
            stats["yolo_classifier"] = {
                "enabled": False,
                "healthy": False,
                "message": "YOLO-cls 분류기 미설정",
                "num_classes": 0,
            }

        # YOLO-det 탐지기 상태
        if self._detector:
            det_healthy, det_msg = self._detector.check_health()
            stats["yolo_detector"] = {
                "enabled": True,
                "healthy": det_healthy,
                "message": det_msg,
                "num_classes": self._detector.num_classes if det_healthy else 0,
            }
        else:
            stats["yolo_detector"] = {
                "enabled": False,
                "healthy": False,
                "message": "YOLO-det 탐지기 미설정",
                "num_classes": 0,
            }

        # GNN 임베더 상태
        stats["gnn_embedder"] = {
            "enabled": self._gnn_embedder is not None,
            "weight": self._gnn_weight,
        }

        # 카테고리 목록 + 건수
        from collections import Counter
        cat_counter = Counter(
            getattr(r, "category", "") for r in self._records.values()
            if getattr(r, "category", "")
        )
        stats["categories"] = sorted(cat_counter.keys())
        stats["category_counts"] = dict(cat_counter.most_common(20))

        return stats

    def _save_records(self, single_record: DrawingRecord | None = None):
        """레코드를 저장한다.

        SQLite 모드에서는 개별 레코드만 저장하고,
        JSON 폴백 모드에서는 전체를 덤프한다.
        """
        if self._use_sqlite and self._record_store is not None:
            if single_record is not None:
                self._record_store.add(
                    single_record.drawing_id,
                    self._record_to_dict(single_record),
                )
            else:
                # 전체 저장 (드물게 필요한 경우)
                for rid, record in self._records.items():
                    self._record_store.add(rid, self._record_to_dict(record))
            return

        # JSON 폴백 (기존 로직)
        self._save_records_json()

    def _save_records_json(self):
        """레코드를 JSON 파일로 저장 (원자적 쓰기: 임시 파일 -> rename)"""
        data = {}
        for rid, record in self._records.items():
            data[rid] = self._record_to_dict(record)
        try:
            self._records_file.parent.mkdir(parents=True, exist_ok=True)
            tmp_file = self._records_file.with_suffix(f".json.{os.getpid()}.tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tmp_file.replace(self._records_file)
        except Exception as e:
            logger.error(f"레코드 저장 실패 (기존 파일 보존): {e}")
            tmp_file = self._records_file.with_suffix(f".json.{os.getpid()}.tmp")
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except OSError:
                    pass

    @staticmethod
    def _record_to_dict(record: "DrawingRecord") -> dict:
        """DrawingRecord를 딕트로 변환한다."""
        return {
            "drawing_id": record.drawing_id,
            "file_path": record.file_path,
            "file_name": record.file_name,
            "ocr_text": record.ocr_text,
            "part_numbers": record.part_numbers,
            "dimensions": record.dimensions,
            "materials": record.materials,
            "category": record.category,
            "description": record.description,
            "yolo_confidence": record.yolo_confidence,
            "yolo_needs_review": record.yolo_needs_review,
            "yolo_top_k": record.yolo_top_k,
            "detected_regions": record.detected_regions,
            "title_block_data": record.title_block_data,
            "parts_table_data": record.parts_table_data,
            "detection_enhanced": record.detection_enhanced,
            "dxf_path": record.dxf_path,
            "similar_drawings": getattr(record, "similar_drawings", []),
            "registered_at": record.registered_at,
            "revision": record.revision,
        }

    def _load_records_json(self):
        """records.json에서 레코드를 로드한다."""
        if not self._records_file.exists():
            return
        try:
            with open(self._records_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for rid, rdata in data.items():
                # 하위 호환: Phase 3 이전 레코드에 없는 필드는 기본값으로
                rdata.setdefault("detected_regions", [])
                rdata.setdefault("title_block_data", {})
                rdata.setdefault("parts_table_data", {})
                rdata.setdefault("detection_enhanced", False)
                rdata.setdefault("dxf_path", "")
                rdata.setdefault("registered_at", "")
                rdata.setdefault("revision", 1)
                self._records[rid] = DrawingRecord(**rdata)
            logger.info(f"기존 레코드 {len(self._records)}건 로드 완료")
        except Exception as e:
            logger.warning(f"레코드 로드 실패: {e}")

    def _load_records_sqlite(self):
        """SQLite에서 레코드를 인메모리 캐시로 로드한다."""
        if self._record_store is None:
            return
        all_data = self._record_store.get_all()
        for rid, rdata in all_data.items():
            rdata.setdefault("detected_regions", [])
            rdata.setdefault("title_block_data", {})
            rdata.setdefault("parts_table_data", {})
            rdata.setdefault("detection_enhanced", False)
            rdata.setdefault("dxf_path", "")
            rdata.setdefault("registered_at", "")
            rdata.setdefault("revision", 1)
            rdata.setdefault("similar_drawings", [])
            # DrawingRecord에 없는 키 제거
            valid_keys = {f.name for f in DrawingRecord.__dataclass_fields__.values()}
            filtered = {k: v for k, v in rdata.items() if k in valid_keys}
            self._records[rid] = DrawingRecord(**filtered)
        logger.info(f"SQLite 레코드 {len(self._records)}건 로드 완료")

    def _migrate_records_to_sqlite(self):
        """인메모리 _records를 SQLite로 마이그레이션한다."""
        if self._record_store is None:
            return
        records_dict: dict[str, dict] = {}
        for rid, record in self._records.items():
            records_dict[rid] = self._record_to_dict(record)
        count = self._record_store.add_batch(records_dict, batch_size=1000)
        logger.info(f"records.json -> SQLite 자동 마이그레이션 완료: {count}건")

    # ─────────────────────────────────────────────
    # 버전 관리 API
    # ─────────────────────────────────────────────

    def get_versions(self, part_number: str) -> list[DrawingRecord]:
        """특정 부품번호의 전 버전을 반환한다."""
        drawing_ids = self._version_index.get(part_number, [])
        results = []
        for did in drawing_ids:
            rec = self._records.get(did)
            if rec is not None:
                results.append(rec)
        return results

    def get_version_history(self) -> dict[str, int]:
        """모든 부품번호의 버전 수를 반환한다. {part_number: count}"""
        return {pn: len(ids) for pn, ids in self._version_index.items()}

    # ─────────────────────────────────────────────
    # Tier-3 도구: 치수 비교 / BOM 추출 / DXF 비교
    # ─────────────────────────────────────────────

    def compare_dimensions(self, drawing_id_1: str, drawing_id_2: str) -> dict:
        """두 도면의 치수를 비교한다."""
        from core.dimension_parser import parse_dimensions, compare_dimensions as _cmp

        rec1 = self._records.get(drawing_id_1)
        rec2 = self._records.get(drawing_id_2)
        if not rec1 or not rec2:
            return {"error": "도면을 찾을 수 없습니다."}

        dims_a = parse_dimensions(rec1.ocr_text)
        dims_b = parse_dimensions(rec2.ocr_text)
        diff = _cmp(dims_a, dims_b)
        return {
            "matched": [
                {"a": vars(a), "b": vars(b)} for a, b in diff.matched
            ],
            "changed": [
                {"a": vars(a), "b": vars(b), "diff": d}
                for a, b, d in diff.changed
            ],
            "only_in_a": [vars(d) for d in diff.only_in_a],
            "only_in_b": [vars(d) for d in diff.only_in_b],
            "similarity": diff.similarity,
        }

    def extract_bom(self, drawing_id: str, use_llm: bool = False) -> dict:
        """도면에서 BOM을 추출한다."""
        from core.bom_extractor import BOMExtractor

        rec = self._records.get(drawing_id)
        if not rec:
            return {"error": "도면을 찾을 수 없습니다."}

        extractor = BOMExtractor(
            ollama_base_url=self._llm.base_url if use_llm else "",
            ollama_model=self._llm.model if use_llm else "",
        )
        bom_result = extractor.extract_from_text(
            text=rec.ocr_text,
            use_llm=use_llm,
        )
        return {
            "entries": [vars(e) for e in bom_result.entries],
            "confidence": bom_result.confidence,
            "source": bom_result.source,
        }

    def compare_dxf(self, dxf_path_a: str, dxf_path_b: str) -> dict:
        """두 DXF 파일을 비교한다."""
        from core.dxf_diff import compare_dxf as _compare_dxf

        result = _compare_dxf(dxf_path_a, dxf_path_b)
        return {
            "matched_count": len(result.matched),
            "only_in_a_count": len(result.only_in_a),
            "only_in_b_count": len(result.only_in_b),
            "layer_diff": result.layer_diff,
            "summary": result.summary,
        }

    # ─────────────────────────────────────────────
    # v5.4 통합 엔진 접근자 (lazy init)
    # ─────────────────────────────────────────────

    @property
    def search_engine(self):
        """UnifiedSearchEngine 인스턴스 (lazy init)."""
        if self._search_engine is None:
            from core.search_engine import UnifiedSearchEngine
            self._search_engine = UnifiedSearchEngine(self)
        return self._search_engine

    @property
    def vlm_orchestrator(self):
        """VLMOrchestrator 인스턴스 (lazy init)."""
        if self._vlm_orchestrator is None:
            from core.vlm_orchestrator import VLMOrchestrator
            self._vlm_orchestrator = VLMOrchestrator(self._llm)
        return self._vlm_orchestrator

    @property
    def comparison_engine(self):
        """ComparisonEngine 인스턴스 (lazy init)."""
        if self._comparison_engine is None:
            from core.comparison_engine import ComparisonEngine
            self._comparison_engine = ComparisonEngine(self)
        return self._comparison_engine

    @property
    def renderer(self):
        """UniversalRenderer 인스턴스 (lazy init)."""
        if self._universal_renderer is None:
            from core.renderer import UniversalRenderer
            self._universal_renderer = UniversalRenderer()
        return self._universal_renderer
