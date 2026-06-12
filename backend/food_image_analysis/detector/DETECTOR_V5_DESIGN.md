# Detector v5.2 설계 (REVISED) — 최대 정확도 · 서버 배포 · 평가 착시 방지

> 박스 라벨 기준은 **ANNOTATION_GUIDE.md** 따른다 (전 소스·테스트셋 동일 기준 필수).

> 1-class food region 검출기. **recall 최우선(놓치지 마), precision 2순위.**
> 박스는 항상 그림 → 클래스 모르면 앱에서 "?" 표시. 판별(음식/비음식/종이컵/음료)은 classifier/후처리 몫.
> 배포 = 서버 API(Plan B) → 모바일 크기 제약 없음 → yolo11x 최대 정확도. 경량화는 별도 단계(distill/quantize).
> 상태: 실험·ablation 남음 → **REVISED / CANDIDATE** (LOCKED 아님).

---

## 1. 데이터 설계 (핵심)

### 소스 (전부 A100)
| 소스 | 수량 | 박스 | 역할 |
|---|---|---|---|
| v3 orig (실사진) | 3,949 | 사람라벨 | train (멀티음식 구조) |
| v3 rb (로보플로우) | 1,997 | 라벨 | train (멀티음식) |
| v3 fl (Florence 자동) | 9,694 | pseudo(노이즈) | **정제+감사 후, ablation 대상** |
| v3 kn (빈 식기) | 1,919 | 빈 라벨 | 배경 negative (FP·종이컵 헛검출 억제) |
| v3 f5k (비음식) | 2,016 | 빈 라벨 | 배경 negative |
| **296 Training** | 185,553 | 사람라벨 1박스 | **균형 서브셋 ~40k** |
| 296 Validation | 23,227 | 사람라벨 | **test 전용 (학습 금지)** |

### 설계 결정
- **296 서브셋 ~40k**: 800 음식종류에서 균형 샘플링(종류당 ~50장). 단일음식 도메인 강화용. 전량 185k는 v3를 묻어버려서 안 씀.
- **단순 파일수 merge 아님 — 도메인 균형 관리.** 296은 단일음식이라 그대로면 단일객체 편향. v3 orig/rb는 실제 멀티음식 구조 학습용으로 충분히 유지.
- **배경 유지**: kn+f5k(3,935) 빈 라벨 → 빈 그릇/종이컵/냅킨에 안 짖게.

### 권장 학습 구성 비율 (배치 도메인 기준, 파일수 아님)
| 데이터 그룹 | 권장 비율 |
|---|---|
| 296 single-food | 50~60% |
| v3 real/multi-food (orig+rb) | 25~35% |
| background negative (kn+f5k) | 10~15% |
| Florence pseudo | 최대 10~15% (ablation) |

> 296 test만 오르고 v3 val / Real App Test가 떨어지면 → 296 비중을 낮춘다.

---

## 2. 평가셋 (3종 분리 — 착시 방지)

| 평가셋 | 역할 |
|---|---|
| **v3 val** | 기존 실사진/멀티음식 in-domain 검증 |
| **296 Validation** | AIHub 296 **도메인 일반화** 성능, v4(0.44) 직결 비교 |
| **Real App Test Set** | 실제 앱 촬영 환경 독립 test |

- 296 Training을 일부 학습에 쓰므로, **296 Validation 성능 = "AIHub 296 도메인 성능"이지 "실전 앱 성능"이 아니다.** 과대해석 금지.
- **Real App Test Set** (신규 필수):
  - 최소 100장, 가능하면 300장
  - 직접 촬영 / 실제 사용 시나리오 기반
  - 멀티음식·단일음식·빈 그릇·종이컵·음료·수저·손·포장지·어두운·흔들린 사진 포함
  - 사람이 직접 food region box 라벨링
  - **학습/검증 절대 금지, 최종 정성·정량 평가에만**

---

## 3. 모델 설계
- 백본 **yolo11x** (56M, COCO pretrained) — 서버라 크기 무관, 최대 정확도
- imgsz **640**, batch ~16–24 (A100 28GB 여유), AdamW + cos_lr + warmup 5
- aug: **mosaic(ablation으로 결정)** + close_mosaic 15~20 + mixup 0.1 + hsv + scale 0.5 + multi_scale
- epochs 120 (patience 40)

### mosaic는 고정 X → ablation
- 296은 1이미지 1박스라 단일객체 편향 위험.
- mosaic은 단일음식을 조합해 다중객체 노출을 늘리는 **보강** 전략.
- 다만 mosaic은 실제 식탁의 공간관계·접시배치·occlusion·배경맥락을 **완전히 대체하지 못한다.**

| 실험 | mosaic |
|---|---|
| A | 0.5 |
| B | 0.7 |
| C | 1.0 |

기본 후보 mosaic 0.7~1.0 / close_mosaic 15~20. **선택 기준: 296 test만 보지 말고 v3 val + Real App Test의 recall/precision 함께 비교.**

---

## 4. Florence pseudo label — 정제 + 감사 + ablation

### 기하 정제 (유지)
- 너무 작은 박스(<면적 0.3%) 제거
- 극단 종횡비(>6:1) 제거
- 다른 박스에 80%+ 포함된 중첩 박스 제거

### 육안 감사 (추가)
- Florence pseudo 중 **300~500장 랜덤 샘플 육안 감사**
- 컵/접시/포장지/소스/비음식이 food로 잘못 잡힌 비율 기록

### 포함/제외 ablation
| 실험 | 구성 |
|---|---|
| Base | v3 사람라벨 + 296 subset + background |
| Pseudo | Base + Florence 정제 라벨 |
| Pseudo-light | Base + 품질 높은 Florence 일부만 |

> v3 val·296 test·Real App Test **모두** 좋아질 때만 pseudo 최종 포함. 296 test만 오르고 Real App precision 떨어지면 비중↓ 또는 제외.

---

## 5. Hard-negative mining (필수 단계)

실제 앱 precision을 위해 **선택이 아니라 필수.**
- 1차 학습 후 FP 많이 나는 이미지 수집 (컵·음료·빈 접시·식탁·손·수저·포장지·메뉴판·냄비·반찬통 등)
- 빈 라벨 이미지로 추가, 음식 포함 시 정확한 food box만 남김
- 2차 재학습 후 conf/NMS 튜닝

실행: 1차 학습 → 추론(v3 val/296 test/Real App) → FP 수집 → hard-neg **500~2,000장** 추가 → 2차 fine-tuning → conf/iou/max_det/NMS 튜닝

---

## 6. 평가 목표 (평가셋별 분리)

| 평가셋 | 목표 |
|---|---|
| 296 Validation | mAP50 ≥ 0.80, Recall@0.25 ≥ 0.85 |
| v3 val | v4 성능 유지 또는 개선 |
| **Real App Test** | Recall@0.25 **0.75~0.85**, Precision@0.25 **0.70~0.80** (1차 목표) |

- 296 Validation 성능을 실전 성능으로 **과대해석 금지.**
- 최종 앱 적용 판단은 **Real App Test의 FP/FN 패턴**까지 본다.
- recall 우선 모델 / precision 우선 threshold를 **따로 관리** 가능.

---

## 7. 실행 순서

1. 296 Training → YOLO 1-class 변환
2. 800 음식종류 균형으로 296 subset ~40k 샘플링
3. v3 fl Florence pseudo 기하 정제
4. Florence pseudo 300~500장 육안 감사
5. yolo_food_v5.1 조립
   - train: v3 train + 296 subset + background (+ optional Florence)
   - val: v3 val
   - test1: 296 Validation
   - test2: Real App Test Set
6. mosaic 0.5 / 0.7 / 1.0 ablation
7. pseudo 제외/포함 ablation
8. best candidate 선택
9. 1차 모델로 FP 수집
10. hard-negative 500~2,000장 추가
11. 2차 fine-tuning
12. 최종 평가 (v3 val / 296 Validation / Real App Test)
13. conf / NMS threshold 튜닝
14. 서버 API 배포 후보 확정

---

## 8. 절대 원칙
- 296 Validation은 **학습에 절대 사용 금지.**
- Real App Test Set도 **학습/검증에 절대 사용 금지.**
- 1-class food region detector 유지.
- 음식명/음료/비음식/종이컵 판별은 **classifier 또는 후처리** 담당.
- 빈 라벨 background 유지.
- pseudo label은 **성능을 올릴 때만** 사용.
- **296 test 성능만으로 최종 성공 판단 금지.**
- 실제 앱 적용은 **Real App Test의 FP/FN 패턴**까지 보고 결정.
- 서버 배포 기준 정확도 우선, 모바일 경량화는 별도 단계(distill/quantize).

---

## 9. 서빙 API 계약 (서버 배포)
- 엔드포인트: `POST /predict`, 입력: 이미지(multipart 또는 base64), 파라미터: `conf=0.25`(recall 우선) · `iou=0.5` · `imgsz=640` · `max_det=50`.
- Detector 출력 → 파이프라인 조합:
```
{ "model_version": "detv52_...",
  "detections": [
    { "bbox_xyxy": [x1,y1,x2,y2], "det_conf": 0.71,
      "classifier": {"top3": [{"code","name_ko","conf"}], "shown": "비빔밥" | "?"},
      "nutrition": { "kcal": ..., ... } } ] }
```
- 조합 순서: Detector 박스 → crop(1.2×) → Classifier(Top-3) → 저신뢰/비음식이면 `shown="?"` → nutrition_map_full 조회.
- 기본값: conf 0.25, NMS iou 0.5, max_det 50. **표시용 최소 conf·이미지당 최대 박스수**를 따로 둬서 "?" 박스 난립 방지.
- 응답에 model_version 태그 (실험 추적용).

## 10. 실험 · 실패 분류 체계
- **run 이름**: `detv52_{backbone}_{imgsz}_mos{0.5/0.7/1.0}_pseudo{on/off}_hn{0/1}_{date}`
- **run마다 로깅**: 학습 config + 3개 셋(v3 val / 296 / Real App) 각각 mAP50 · mAP50-95 · P@0.25 · R@0.25.
- **FP 카테고리** (Real App에서 카운트): 빈그릇·종이컵 / 식탁무늬 / 손·수저 / 포장지·메뉴판 / 배경음식 / 중복박스.
- **FN 카테고리**: 국물·탕 놓침 / 겹친음식 놓침 / 작은 반찬 놓침 / 어두운·흔들린 놓침 / 클로즈업 놓침.
- → hard-negative를 **FP 카테고리별로 타겟 수집** (어떤 걸 더 넣을지 데이터로 결정).

## v5 → v5.2 변경 요약 (왜 바꿨나)
1. **평가 착시 차단**: 296 Val은 "296 도메인 성능"일 뿐 → 실전용 Real App Test Set 신설.
2. **데이터 지배 방지**: 296 40k를 파일수 merge가 아니라 도메인 비율로 관리 (296이 v3 묻어버리는 위험).
3. **과한 가정 제거**: mosaic이 멀티음식을 대체한다는 단정 → ablation으로 검증.
4. **pseudo 리스크 관리**: Florence는 정제+육안감사+포함/제외 ablation, 성능 오를 때만 채택.
5. **precision 보강 필수화**: hard-negative mining을 선택 → 필수 단계로 승격.
6. **(v5.2) 박스 기준 통일**: ANNOTATION_GUIDE.md로 전 소스·테스트셋 라벨 정의 일원화 (mAP 무의미화 방지).
7. **(v5.2) 서빙 계약·실험/실패 분류 추가**: 출력 규격 고정 + FP/FN 카테고리화로 hard-negative 타겟팅.
