# LEMON-AID 디텍터 인계 문서

> 음식 영역 검출(detector) 작업 인계. 1-class food region detector.
> 종류 판별은 분류기(별도), 디텍터는 "음식 위치 박스"만.

---

## 1. 모델 현황 (3개 후보)
| 모델 | 파일 | 학습 | 실전 한상 8장 mAP50 |
|---|---|---|---|
| v3 (옛날) | `음식\detector_best.pt` | 150ep, 296 없음 | 0.806 |
| fast v5 mos0.5 | `D:\runs\detect\fastv5_296\weights\best.pt` | 30ep, 296+정제 | 0.768 |
| **fast v5 mos1.0** | `D:\fastv5_mos10_best.pt` | 30ep, 296+정제, mosaic1.0 | **0.833 (최고)** |

- **현재 최강 = fast v5 mos1.0** (한상 mAP50 0.833 / R 0.841 / P 0.931)
- 단 전부 fast 실험(30ep)이라, **최종은 yolo26x @640 100ep로 재학습 예정** (A100 자리나면)

## 2. 평가 숫자 (mos1.0 기준)
| 평가셋 | mAP50 | 해석 |
|---|---|---|
| 296 test | 0.935 | in-domain 착시 (참고만) |
| v3 val | 0.781 | 반쯤 실사진 |
| **실전 한상 8장** | **0.833** | ← 진짜 성능 (팀원 정밀라벨 기준) |

## 3. 확인된 강점/약점
**강점:** 한식 한상(밥·국·반찬 종지까지) 잘 잡음, 박스 깔끔, 음료/빈그릇 대부분 거름
**약점:**
- 초밥/스시·핑거푸드(판 위 낱개) 약함 — **학습 데이터에 거의 없어서** (domain). 일식 커버하려면 데이터 보강 필요
- conf 낮음(0.3~0.6) — 30ep라 그럼. 최종 100ep면 올라감
- 종이컵·잔여물 등 일부 negative에서 헛박스 (이미지당 ~0.67개)

## 4. 최종 설정 (여러 사진 직접 테스트 후 확정)
태동이 한상·단일·음료·초밥 등 여러 사진을 compare_demo로 직접 비교해 정한 값:
```
모델     = v3 (detector_best.pt) 기준 — 검출력 가장 좋음
conf     = 0.30
NMS IoU  = 0.15      (다중박스 억제 — 낮춰서 겹친박스 합침)
agnostic_nms = True  (1-class라 효과 큼, 다중박스 잡는 핵심)
max_det  = 50
imgsz    = 512
CLIP 필터 = ON, food 임계값 0.25, crop padding 1.0
```
> 다중박스 문제는 NMS IoU 0.15 + agnostic NMS로 잡음. CLIP은 켜서 사용.
> (주의: IoU 0.15는 공격적 — 옆 음식 합쳐지는 케이스 보이면 0.3~0.45로 조정 여지)

## 6. 테스트 도구
- **`compare_demo.py`** — 3모델 + CLIP 토글 비교 (브라우저)
  ```
  python -m streamlit run compare_demo.py --server.port 8504
  ```
- **`detector_demo.py`** — 단일 디텍터 데모
- 평가셋 yaml: `jeongsik_eval.yaml`(한상8), `realapp_eval.yaml`(실전), `realapp_jeongsik`(이미지+라벨)

## 7. 남은 작업 (우선순위)
1. **A100 자리나면 최종 학습** — `final_train.py` (yolo26x→11x, @640, 100ep, mosaic1.0, **workers=0** 필수: 공유서버 hang 방지). 백그라운드 권장: `Start-Process python -ArgumentList "...final_train.py" -RedirectStandardOutput train_log.txt -WindowStyle Hidden`
2. **3종 평가**(296/v3val/한상)로 26x vs 11x 승자 선정
3. **hard-negative 2차** — 헛박스 나는 종이컵·잔여물·초밥 수집 → fine-tune
4. **초밥/일식 데이터 보강** (앱이 일식 커버할 경우)
5. **서버 API** (`POST /predict`) → 분류기와 결합

## 8. 핵심 데이터 위치
- 학습 데이터: `D:\yolo_food_v3`(정제됨) + `D:\food296_subset`(40k, 음료제외) / A100: `G:\lemon-aid\`
- 데이터 설정: `fastv5_a100.yaml` (A100용), `fastv5_data.yaml` (노트북용)
- 백업: `D:\v3_labels_train_backup.zip`
- 설계 문서: `DETECTOR_V5_DESIGN.md`, `ANNOTATION_GUIDE.md`
