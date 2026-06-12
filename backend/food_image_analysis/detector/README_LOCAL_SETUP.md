# 디텍터 인계 자료 — 로컬 배치 안내

> 출처: **`detector_FINAL.zip` (2026-06-12 18:41, 최종본)** — 인계자 지시로 이전 패키지
> (detector_handoff.zip v1/v2, handoff_eval.zip)는 전부 폐기함(구모델 2종·이전 평가셋 삭제).
> **권위 문서 = `README_디텍터_최종.md`** (최종 설정 §2, 추론 코드 예시 §4).

## 최종 구성 = v3 + CLIP

| 부품 | 파일 | 비고 |
|---|---|---|
| 디텍터 | `detector_best.pt` (18.3MB, v3) | **이 폴더에 로컬 보관** — git 금지(2MB+ 규칙), 폴더 `.gitignore`(`*.pt`)가 보호. 타 PC는 파일공유로 복사 |
| CLIP 필터 | `food_filter.py` | ⚠️ **`transformers<5` 필수**(5.x는 get_text_features 반환 타입 변경으로 비호환 — 4.57.6 설치됨). 첫 실행 시 CLIP 가중치 ~600MB 자동 다운로드(1회, 캐시됨) |

최종 설정(그대로 사용): `conf 0.30 · NMS IoU 0.15 · agnostic_nms · max_det 50 · imgsz 512 · CLIP 임계 0.25 · padding 1.0` — 상세·추론 예시는 `README_디텍터_최종.md`.

## 데모 실행

```powershell
# 디텍터 단독 (인계자 데모)
C:\Lemon-sin\backend\.venv\Scripts\python.exe -m streamlit run backend\food_image_analysis\detector\compare_demo.py --server.port 8504

# 통합 파이프라인: 디텍터(v3) → CLIP → 분류기(exp16b 지원 40클래스)  ← 한상(다중 음식) 대응
C:\Lemon-sin\backend\.venv\Scripts\python.exe -m streamlit run backend\food_image_analysis\detector\pipeline_demo.py --server.port 8505
```

⚠️ compare_demo는 3모델 비교용으로 작성됐으나 fast v5 모델 2종은 폐기됨 — **v3만 선택**할 것
(mos0.5/mos1.0 선택 시 파일 없음 에러).
pipeline_demo의 분류기는 `runs/food_yolo/exp16b_*/weights/best.pt` 참조(없으면 `EXP16B_WEIGHTS` 환경변수로 지정).

## 주의

- ⚠️ **이 브랜치(develop 기반)의 루트 .gitignore에는 `*.pt`/`runs/` 규칙이 없다** —
  `git add -A`/`git add .` 금지, 항상 파일을 명시해서 add 할 것.
- **정량 평가셋 현재 없음**: 이전 평가 패키지(한상 8장 등)는 인계자 지시로 폐기됨.
  성능 검증·재학습 비교가 필요해지면 인계자에게 확정본 평가셋을 재요청하거나,
  보유한 다중요리 실사진(friend multi 510장)을 `ANNOTATION_GUIDE.md` 기준으로 라벨링해 자체 구축.
- 분류기(exp16b, 지원 40클래스)와는 **별개 모델**: 디텍터 = 음식 "위치"만(1-class),
  분류기 = 음식 "종류". 통합 시 디텍터 박스 → CLIP 필터 → 분류기 crop 파이프라인 검토.
