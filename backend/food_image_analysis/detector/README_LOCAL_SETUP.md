# 디텍터 인계 자료 — 로컬 배치 안내

> 출처: 팀원 인계 `detector_handoff.zip` (2026-06-12, v2 = 상대경로판). 상세 내용은 `DETECTOR_인계.md` 참조.
> 코드·문서만 커밋한다. 모델 가중치(.pt, 총 121MB)는 git 금지(2MB+ 규칙) — 이 폴더의 `.gitignore`(`*.pt`)가 보호.

## 모델 가중치 위치 — **이 폴더 (스크립트 옆)**

v2 데모 스크립트는 자기 폴더(`HERE`) 기준 상대경로로 모델을 찾는다. 다른 PC에서는
팀 파일공유로 .pt 3개를 이 폴더에 복사하면 바로 실행된다.

```
detector_best.pt   (18.3MB)  = v3 — 인계 문서의 "최종 설정" 기준 모델
fastv5_mos05.pt    (48.8MB)  = fast v5 mosaic0.5 (한상 mAP50 0.768)
fastv5_mos10.pt    (48.8MB)  = fast v5 mosaic1.0 (한상 mAP50 0.833, 현재 최강)
```

## 실행

```powershell
# 3모델 + CLIP 토글 비교 (브라우저)
C:\Lemon-sin\backend\.venv\Scripts\python.exe -m streamlit run backend\food_image_analysis\detector\compare_demo.py --server.port 8504

# 단일 디텍터 데모
C:\Lemon-sin\backend\.venv\Scripts\python.exe -m streamlit run backend\food_image_analysis\detector\detector_demo.py
```

## 평가셋 (handoff_eval.zip, 2026-06-12 수령)

이미지·라벨 실체는 git 밖 — `C:\Lemon-sin\data\food_images\raw\detector_eval\`:

```
realapp_jeongsik/   한상(정식) 8장 + 정밀 라벨        ← "한상 mAP50 0.833"의 근거 평가셋
real_app_test/      실전 39장 + 라벨 (강아지·빈그릇 등 네거티브 = 빈 라벨 포함)
```

yaml(`jeongsik_eval.yaml`·`realapp_eval.yaml`)은 이 폴더에 커밋돼 있고, 타 PC는 `path:` 한 줄만 수정.
(인계자 zip의 labels.cache는 타 PC 캐시라 제거함 — ultralytics가 자동 재생성)

평가 실행 예:

```powershell
C:\Lemon-sin\backend\.venv\Scripts\python.exe -c "from ultralytics import YOLO; print(YOLO(r'backend/food_image_analysis/detector/fastv5_mos10.pt').val(data='backend/food_image_analysis/detector/jeongsik_eval.yaml', verbose=False).box.map50)"
```

**아직 미수령**: `fastv5_a100.yaml` + "296+정제" 학습셋(final_train.py 재학습용), v3 val/296 test 셋.

## 주의

- ⚠️ **이 브랜치(develop 기반)의 루트 .gitignore에는 `*.pt`/`runs/` 규칙이 없다** —
  `git add -A`/`git add .` 금지, 항상 파일을 명시해서 add 할 것. (이 폴더 안의 .pt는 폴더 .gitignore가 방어)
- CLIP 필터(`food_filter.py`)는 `transformers` 필요(설치됨, 5.11.0). 첫 사용 시 CLIP 모델 ~600MB 자동 다운로드(1회, HF 캐시).
- 분류기(exp16b, 지원 40클래스)와는 **별개 모델**: 디텍터 = 음식 "위치"만(1-class),
  분류기 = 음식 "종류". 통합 시 디텍터 박스 → 분류기 crop 파이프라인 검토.
