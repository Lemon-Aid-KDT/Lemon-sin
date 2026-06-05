# A100 환경 세팅 & 실험 인수인계 — 한식 음식 탐지 (taxo59)

> **목적**: A100 서버에서 8GB 노트북으로 못 했던 실험(대형 모델·고해상도·대용량 배치·전체 데이터)을 수행하기 위한 **완전 인수인계 문서**. 이전 실험 전체 결과 + 환경 세팅 + 데이터 전송 + 평가 방법 + 실험 4종 + 함정 체크리스트.
> **작성**: 2026-06-05 | 로컬 머신: Windows 11, RTX 5060 Laptop **8GB VRAM**(이 VRAM이 모든 제약의 원인).

---

## 0. 한눈에 — 왜 A100인가

8GB가 강제한 제약 4가지 → A100(40/80GB)이 전부 해제:

| 제약(8GB) | 강제된 선택 | A100에서 가능 |
|---|---|---|
| VRAM 8GB | **yolo26s(소형 9.5M)만** | yolo26l/x(25~57M), RT-DETR, ViT-L |
| batch=16 (b32 스필오버→10배 둔화) | batch=16 고정 | batch 64~256 |
| imgsz=640 | 640 고정 | **imgsz 1280**(fine-grained 한식 판별) |
| 디스크/속도 | cap1500(데이터 일부만) | 전체 데이터 + cache=ram |

---

## 1. 프로젝트 컨텍스트 (1분 요약)

- **과제**: 한식 음식 **객체 탐지**(YOLO), **59클래스(taxo59)**. AIHub 음식이미지 라벨을 424코드→59클래스로 재설계.
- **목표**: 사진 1장 → 음식 인식 → 영양소·만성질환 맞춤(레몬헬스케어). 모델은 탐지까지 담당.
- **현재 최고 범용 모델**: **exp11**(yolo26s, taxo59, cap1500) **val mAP50 0.895**.
- **핵심 난제(진단됨)**: studio(AIHub) → **wild(실환경 카톡 사진)** 도메인갭. **studio 0.89 → wild 인식률 0.35**. 그런데 **박스는 잘 잡음(det 0.94), 못하는 건 분류** → 문제의 본질 = **분류 강건성**.

---

## 2. 이전 실험 전체 결과

### 2.1 실험 타임라인 (mAP50 = AIHub val 기준)

| exp | 모델 | 데이터/택소노미 | mAP50 | 핵심 |
|---|---|---|---|---|
| exp01 | yolov8n | 50cls baseline | ~0.846 | Phase0 |
| exp02 | yolo11s | 50cls | 0.697* | 미완(*절단) |
| exp03 | yolov8n | 50cls balanced | 0.790 | |
| exp04 | yolov8n | 50cls minority **aug** | 0.806 | 증강 |
| exp05 | yolov8n | 50cls minority **dup** | 0.804 | 복제 |
| exp06 | yolo11s | **taxo63** bal500 | 0.824 | Phase1 시작(택소노미 재설계) |
| exp07 | **yolo26s** | taxo63 bal500 | 0.849 | 모델 11s→26s **+0.019** |
| exp08 | yolo11s | taxo63 | 0.830 | 11s 비교군 |
| exp09 | yolo26s | **taxo62** bal500 | 0.837 | chicken-galbi 삭제 |
| exp10 | yolo26s | **taxo59** bal500 | 0.882 | 약점3 drop(mala·탕수육·제육) **+0.045** |
| exp11 | yolo26s | taxo59 **cap1500** | **0.895** | **최고 범용**. 과적합 완화 |
| exp12 | yolo26s | taxo59 + takoyaki SS | 0.887 | 파일럿(아래) |
| exp13 | yolo26s | taxo59 + 11cls SS | 0.875 | 일반화됐으나 불균형 잠식(아래) |
| exp14 | yolo26s | taxo59 **balanced SS** | (학습중) | 개수 균등 보강. 진단용 |

### 2.2 검증된 핵심 발견 (A100 실험 설계의 근거)

1. **증강·복제 무효(Phase0)**: exp04/05의 "+0.015"는 val-셋 아티팩트. 동일 val 재측정 시 baseline 0.826 > aug 0.806 > dup 0.805. **복제=새 정보 0**. 단 이건 studio→studio 측정이라 **studio→wild는 미검증(=Exp C 동기)**.
2. **택소노미 재설계가 진짜 레버**: 혼동군 분할(탕 0.56→0.84, 면 0.55→0.92), 라벨노이즈 감사로 **fried-chicken 0.670→0.896(+0.226)**(chicken-galbi가 닭갈비 0장인 3코드 오염→해체).
3. **과적합 확정**: exp10 **train mAP50 0.994 vs val 0.877(갭 0.117)**. 분류헤드만 과적합(box_loss 정상). cap1500으로 갭 0.097(val +0.018). **데이터양이 레버**.
4. **WILD 베이스라인(측정자)**: 실환경 783장(단일요리) 인식률 — exp11 **strict 0.350 / lenient 0.363 / det@0.10 0.944**. → **위치는 잘 잡고 분류를 못함**. studio 0.89 → wild 0.35.
5. **실데이터는 wild에 전이됨(단 균형 필수)**: exp13에서 11 selectstar 클래스는 wild 0.33→**0.92**(raw-fish n=93: 0.51→0.93, 실질). 그러나 보강 안 한 48클래스는 wild **0.36→0.16(잠식)** — 불균형 보강이 prior를 쏠리게 함. **교훈: 실데이터 보강은 효과적이나 클래스 균형 필수**.
6. **selectstar 완전 분류(2026-06-05)**: 35폴더 35,988장 per-image 비전 분류 → **27,472 클린/53클래스**. 폴더-이름 매핑이 못 한 2가지 달성: **채굴**(galbi→barbecue-ribs 666, BBQ→grilled-pork-belly 270·grilled-beef 66 = wild 0점 클래스), **정제**(sashimi 폴더 육회 혼입 제거 등).

### 2.3 여전히 부족한 클래스 = wild 수집 타깃 (selectstar로도 못 채움)

exp14 balanced(cap1500 균등 채움) 후에도 **31클래스 <1500**. 특히 **selectstar에 음식 자체가 없는 8개** = 신규 수집 1순위:
`braised-pork-hock, doenjang-jjigae, seafood-jjim, korean-blood-sausage, korean-red-soup, kalguksu, seafood-clear-tang` (+ 한식 특화 소수: squid-dish·tteokbokki-jajang·cold-ramen·nagasaki-champon).

---

## 3. 데이터셋 인벤토리 & 전송

> ⚠️ **`.npy`(cache=disk 산출물)는 전송 금지** — 이미지당 ~1.2MB, A100에서 자동 재생성됨. images(.jpg/.png) + labels(.txt) + data.yaml만 전송.

| 데이터셋 | 위치(로컬) | 규모 | 용도 | 전송? |
|---|---|---|---|---|
| `aihub_yolo_taxo59_bal1500` | C:\Lemon-sin\data\food_images\processed\ | train 60,840 / **val 4,970** | 표준 학습셋 + **공통 val** | ✅ 필수 |
| `aihub_yolo_taxo59_exp14_balanced` | 〃 | train 68,713 | balanced 보강셋 | ✅(또는 빌드스크립트로 재생성) |
| `aihub_yolo_taxo59` | 〃 | 424→59 소스 | 전체 데이터 빌드 소스(Exp D) | ✅(Exp D 시) |
| raw `selectstar` | C:\Lemon-sin\data\food_images\raw\selectstar\ | 92폴더 ~95k png | 보강·2스테이지 분류기(Exp B) | ✅(Exp B 시) |
| raw `friend_contributed` | **D:\Deeplearning\lemon\data\raw\friend_contributed\** | wild 2,471 / **eval 783** | **wild 평가셋** | ✅ 필수 |
| `manifests\class_nutrition_taxo59.csv` | C:\Lemon-sin\data\food_images\manifests\ | 59행 | 영양소(데모용) | 선택 |

**전송 예시(rsync, .npy 제외):**
```bash
rsync -av --exclude='*.npy' --exclude='labels.cache' --exclude='_archive_cache' \
  ./data/food_images/processed/aihub_yolo_taxo59_bal1500/ \
  a100:/workspace/lemon/data/processed/aihub_yolo_taxo59_bal1500/
# wild 평가셋(클린 리스트 + 원본):
rsync -av D:/Deeplearning/lemon/data/raw/friend_contributed/ a100:/workspace/lemon/data/wild/
```
평가용 매니페스트도 함께: `wild_keep_dedup_list.txt`(783, `folder/file\tclass`), `ss_harvest_clean_list.tsv`(27,472, `class\tfolder/file`), `exp13_selectstar_heldout.tsv`(1,100).

---

## 4. A100 환경 세팅 (step-by-step)

로컬 검증된 버전: **python 3.13.13 · torch 2.12.0.dev20260408+cu128 · ultralytics 8.4.51 · opencv 4.13.0 · numpy 2.4.4**.

```bash
# 1) env
conda create -n lemon python=3.13 -y && conda activate lemon

# 2) PyTorch — A100=sm_80, CUDA 12.x. 안정판 우선 시도:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
#   ※ 로컬은 dev빌드(2.12.0.dev+cu128). yolo26 로드/학습이 안 되면 로컬 버전 복제:
#   pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu124

# 3) ultralytics(yolo26 지원) + 의존성
pip install ultralytics==8.4.51 opencv-python pyyaml pandas numpy

# 4) (Exp B 2스테이지용) 분류기 백본
pip install timm torchvision pillow

# 5) ★검증 — yolo26 정상 로드 확인(필수)
python -c "from ultralytics import YOLO; m=YOLO('yolo26s.pt'); print('yolo26 OK,', sum(p.numel() for p in m.model.parameters()),'params')"
nvidia-smi   # A100 sm_80, 40/80GB 확인
```

**스모크 테스트(경로·환경 검증, 1 epoch):**
```bash
yolo detect train model=yolo26s.pt data=/workspace/lemon/data/processed/aihub_yolo_taxo59_bal1500/data.yaml \
  epochs=1 imgsz=640 batch=16 device=0 cache=disk name=smoke
```

---

## 5. 경로 적응 (Windows → Linux) — 놓치기 쉬움

로컬 산출물은 전부 `C:\...` / `D:\...` 하드코딩. A100(Linux)에서 반드시 수정:

1. **각 `data.yaml`의 `path:` 필드** — `C:/Lemon-sin/.../dataset` → `/workspace/lemon/data/processed/dataset`. (train/val은 상대경로라 path만 고치면 됨)
   ```bash
   sed -i 's#^path:.*#path: /workspace/lemon/data/processed/aihub_yolo_taxo59_bal1500#' .../data.yaml
   ```
2. **빌드/평가 스크립트의 절대경로**(`C:\Lemon-sin\...`, `D:\Deeplearning\...`) — 상단 상수만 Linux 경로로. 학습은 ps1 대신 **.sh**로 재작성(아래 §7 명령 그대로 사용).
3. **wild 평가**: `wild_keep_dedup_list.txt`의 항목은 `folder/file`이고 베이스가 `D:\...\inbox` → A100의 wild 디렉터리로 베이스 교체.

---

## 6. 평가 방법론 (3개 셋 — 반드시 동일하게)

모든 실험은 **같은 3셋**으로 비교(공정성). 스크립트: `_eval_exp14_full.py`(경로만 적응).

| 셋 | 내용 | 측정 | 의미 |
|---|---|---|---|
| ① **AIHub val** | bal1500 val **4,970(불변)** | per-class AP50, mAP50 (`model.val`) | studio 성능 |
| ② **selectstar held-out** | 1,100(11클래스×100) | top1==class 인식률(conf 0.10) | selectstar 도메인 |
| ③ **WILD 783** | 실환경 단일요리 | top1==matched_class (strict/lenient/det) | **도메인갭 측정자(핵심)** |

> **wild가 진짜 지표**. 어떤 실험이든 "wild 인식률(strict/lenient)이 exp11의 0.350을 넘었나, 비보강 클래스를 잠식하지 않았나"로 판정.

---

## 7. A100 실험 제안 4종 (+보너스) — 구체 config

> 공통: `seed=42`(여유 시 123·7 반복), val 불변, 끝나면 §6 3셋 평가. exp11(0.895/wild0.350)·exp14를 baseline으로 비교.

### Exp A (1순위) — 고해상도 + 대형 모델 ★최우선
**미개척 레버. fine-grained 한식 판별 + wild 분류갭을 동시에 침.**
```bash
yolo detect train model=yolo26l.pt \
  data=/workspace/lemon/data/processed/aihub_yolo_taxo59_exp14_balanced/data.yaml \
  epochs=80 imgsz=1280 batch=32 device=0 cache=ram workers=16 \
  optimizer=auto seed=42 patience=20 plots=false name=expA_yolo26l_1280
```
- 80GB면 yolo26l@1280 batch=32~48, 40GB면 batch=16~24 또는 yolo26m. OOM 시 batch↓.
- **비교군**: 같은 데이터로 yolo26s@640(=exp14 재현). 변수=모델크기·해상도.
- **기대**: studio mAP↑ + **wild 분류 개선**(640이 뭉개던 소스/텍스처를 1280이 살림).
- ablation: {yolo26s,m,l} × {640,1024,1280} 그리드.

### Exp B (2순위) — 2스테이지: 탐지기 + 무거운 분류기 ★wild 갭 정조준
**진단(wild det 0.94, recog 0.35)에 대한 정공법: 분류 전용 대형 백본.**
- **Stage1(탐지)**: exp11 best.pt를 **클래스 무시 음식 로컬라이저**로 사용(박스만). 또는 single-class "food" 탐지기 신규 학습.
- **Stage2(분류)**: `timm` **ConvNeXt-L / EVA-02-L / ViT-L** 59-way 분류기를 크롭으로 학습.
  - 학습 데이터: AIHub bal 크롭 + **selectstar 클린 27,472**(`ss_harvest_clean_list.tsv`) (+옵션 wild 일부).
  - 강증강(색·블러·원근)으로 도메인 강건.
- **평가**: wild 783 → 박스 크롭 → 분류 → GT 비교. (det는 이미 0.94이므로 recog가 핵심)
- 스켈레톤: `timm.create_model('convnext_large', pretrained=True, num_classes=59)`, 크롭 dataset(YOLO 라벨 박스로 crop), CE loss, AdamW, cosine. ultralytics 밖 커스텀 코드 필요.
- **기대**: wild 인식률을 0.35에서 크게 끌어올림(분류 용량·다양성).

### Exp C (3순위) — 도메인 강건 증강 (studio→wild)
**"증강 무효" 결론을 wild에서 재검증. 먹히면 수집량↓.**
```bash
yolo detect train model=yolo26l.pt \
  data=/workspace/lemon/data/processed/aihub_yolo_taxo59_bal1500/data.yaml \
  epochs=80 imgsz=640 batch=64 device=0 cache=ram seed=42 patience=20 plots=false \
  hsv_h=0.03 hsv_s=0.9 hsv_v=0.6 degrees=10 translate=0.2 scale=0.6 \
  perspective=0.0005 mosaic=1.0 mixup=0.2 cutmix=0.2 copy_paste=0.2 erasing=0.5 \
  name=expC_robustaug
```
- 변수=증강 강도만(모델·데이터 동일). **wild 평가가 핵심**(studio val은 오히려 떨어질 수 있음 — 정상).
- **기대**: 재학습 없이 신규수집 없이 wild 갭 일부 축소.

### Exp D (4순위) — 전체 데이터 + 클래스 균형 샘플링 (cap 해제)
**cap1500이 버린 데이터 회수. exp11에서 "증량=과적합 완화" 입증된 것의 상한.**
```bash
# 1) 전체 데이터셋 빌드(cap 없이 가용 AIHub 전부) — _build_*.py 변형(CAP 제거)
# 2) 큰 배치 학습
yolo detect train model=yolo26m.pt \
  data=/workspace/lemon/data/processed/aihub_yolo_taxo59_full/data.yaml \
  epochs=60 imgsz=640 batch=128 device=0 cache=ram seed=42 plots=false name=expD_fulldata
```
- **불균형 주의**(bread 11,820 : squid 100). 처리: ⓐ minority 오버샘플(빌드 시 복제) 또는 ⓑ 커스텀 weighted sampler. ultralytics 네이티브 per-class 가중은 없음 → 빌드단에서 처리 권장.
- **기대**: 풍부 클래스 과적합 완화, 데이터 스케일 상한 확인.

### 보너스 (싸니까) — 멀티시드 + 아키텍처 스윕
- **시드 2~3개**(42·123·7) 반복 → 드디어 run-noise 정량화(단일 run 변동 분리). 그동안 못 함.
- **패러다임 비교**: `rtdetr-l.pt`(트랜스포머 검출기, 무거워 A100 영역) vs yolo26l vs yolo11l. end-to-end vs NMS.
```bash
yolo detect train model=rtdetr-l.pt data=.../bal1500/data.yaml epochs=80 imgsz=640 batch=32 name=expE_rtdetr
```

**추천 순서**: A(고해상도·대형) → B(2스테이지 분류기). 둘 다 wild 분류갭을 직접 침. C·D는 병행 가능.

---

## 8. 놓치지 말 것 — 함정 체크리스트

- [ ] **yolo26 optimizer = MuSGD 자동선택**. 학습 시작 로그에서 실제 optimizer/lr 확인(auto가 MuSGD/AdamW 중 택1).
- [ ] **labels.cache 손상 hang**: 학습을 강제종료(kill)했으면 **재실행 전 train/val의 `labels.cache` 삭제**(불완전 기록→무한 hang). 빌드/실행 스크립트가 archive 이동하도록 돼 있음.
- [ ] **VAL 불변**: 모든 비교는 `aihub_yolo_taxo59_bal1500`의 **val 4,970 동일**. 실험마다 val 바꾸면 비교 무효(Phase0 아티팩트의 교훈).
- [ ] **off-by-one**: `predictions.json`의 `category_id`는 **COCO식 1-기반**. 수동 혼동분석 시 `cid-1`로 보정(이 버그로 과거 결론 1건 폐기됨). per-class AP는 ultralytics 내부계산이라 영향 없음.
- [ ] **cache**: A100 RAM이 데이터셋보다 크면 `cache=ram`(가장 빠름). 아니면 `cache=disk`(이미지당 ~1.2MB .npy, 60k면 ~70GB — 디스크 여유 확인).
- [ ] **wild GT는 VLM 파생**(고품질이나 사람검수 아님) → 절대값보다 **상대 비교**(exp간)에 사용.
- [ ] **Linux이므로 ps1 BOM 함정 무관**, .sh 사용. 대신 data.yaml `path:`·스크립트 절대경로 적응 필수(§5).
- [ ] **batch 스케일 시 lr**: 큰 batch면 lr 상향 고려(linear scaling). yolo26 auto가 어느 정도 처리하나 확인.

---

## 9. 부록

### 9.1 taxo59 클래스 (59개)
```
barbecue-ribs, black-bean-noodles, braised-chicken, braised-pork-hock, bread, bulgogi, cake,
cold-noodles, curry, dim-sum, dumplings, fish-cake, fried-chicken, fried-food-platter, fried-rice,
grilled-beef, grilled-fish, grilled-pork-belly, hamburger, hot-pot, korean-blood-sausage,
mixed-rice-bowl, pasta, pizza, raw-fish, rice-bowl, rice-porridge, rice-soup, salad, sandwich,
savory-pancake, seaweed-rice-roll, shrimp-dish, spicy-mixed-noodles, squid-dish, sushi, takoyaki,
udon, korean-clear-soup, korean-red-soup, western-cream-soup, japanese-ramen, korean-ramyeon-red,
cold-ramen, tteokbokki-red, tteokbokki-cream-rose, tteokbokki-jajang, pork-cutlet-dry,
pork-cutlet-sauced, seafood-spicy-tang, seafood-clear-tang, seafood-jjim, kalguksu,
rice-noodle-soup, noodle-plain, jjigae-red, doenjang-jjigae, jjamppong, nagasaki-champon
```

### 9.2 핵심 파일 위치 (로컬, 전송/참조용)
- 빌드: `docs/superpowers/plans/exp06_review/_build_exp14_balanced.py`(+ taxo59/bal 빌드들)
- 평가: `docs/superpowers/plans/exp06_review/_eval_exp14_full.py`(3모델×3셋)
- selectstar 분류 결과: `ss_classify_chunk{1,2,3}.json` + `ss_gapfill_chunk{1,2}.json` → harvest `ss_harvest_clean_list.tsv`, `ss_harvest_by_class.csv`
- selectstar→taxo59 검증 매핑: `ss_taxo59_mapping_verified.csv`
- wild 평가셋: `wild_keep_dedup_list.txt`(783), 전체분류 `wild_classification_2026-06-04.csv`
- 모델 가중치: `runs/food_yolo/exp11_..._taxo59bal1500_.../weights/best.pt`(범용 최고), exp13·exp14 동일 패턴
- 진행상태/재개 런북: `docs/superpowers/plans/exp06_review/PIPELINE_STATE.md`

### 9.3 현재 진행 중(로컬)
- **exp14 balanced**(yolo26s, count-balanced selectstar fill) 학습 중(~16/50 epoch, val mAP50 ~0.903). 완료 시 wild 평가로 "균등 보강이 잠식을 막았나" 진단 예정 → 그 결과를 A100 실험(특히 Exp A/D) 데이터 설계에 반영.

---
**문의/갱신**: 실험 결과가 나오면 §2 표와 §7 ablation에 추가. wild 인식률을 단일 기준 지표로 추적.
