# 실환경(wild) 데이터 수집 에이전트 — 인수인계 (새 세션용)

> **목적**: 학습 데이터를 채울 **실환경 음식 이미지**를 모으는 에이전트를 새 세션에서 만들기 위한 완전 명세. *무엇을 / 얼마나 / 어디서 / 어떻게* 모으고, **이번까지의 실험에서 발견한 함정(누수·동질성)을 반복하지 않도록** 한다.
> **작성**: 2026-06-05 | 대상 모델: 한식 탐지 taxo59(59클래스).

---

## 0. 왜 wild 데이터인가 (3줄 진단 — 이게 전부의 근거)
1. **AIHub는 스튜디오 + 클래스당 음식코드가 적음**(cold-ramen=코드 1개×280장). 모델이 *개념*이 아니라 *그 몇 인스턴스*를 **암기**.
2. **train/val 누수**: 같은 음식코드가 train·val 양쪽 → studio val(0.895)은 **암기를 채점한 부풀린 수치**. (예: cold-ramen studio AP **0.986 → wild 0.000**)
3. **진짜 일반화 = wild**: 실환경 783 평가셋에서 studio 0.89 → **wild 0.35**, 그것도 박스는 잘 잡고(0.94) **분류가 안 됨**. → **클래스당 "서로 다른 실제 인스턴스(특히 wild 도메인)"를 채우는 것이 유일하게 일관된 처방.**

**핵심 교훈(에이전트가 반드시 지킬 것)**: "같은 요리 사진을 많이"가 아니라 **"서로 다른 실제 요리(인스턴스)를 다양하게"**. 그리고 분할은 **인스턴스/출처 단위**(이미지 단위 X — 그게 누수의 원인).

---

## 1. 에이전트의 미션 (한 줄)
**실환경 한식 사진을, 우선순위 클래스별로, 서로 다른 실제 인스턴스가 다양하게 모이도록 수집→필터→분류→중복제거→라벨→그룹분할 가능한 형태로 정리한다.** (자동, 사람검수 최소화)

---

## 2. 무엇을 모으나 — 우선순위 클래스

판정 기준: **wild 인식률(=실패도) 우선, AIHub 개수는 무관**. (전체 표는 §9 부록, 산출 스크립트 `_collect_priority` 로직 재현 가능)

> ⚠️ **핵심 정정 — "AIHub 1500 도달 ≠ wild 준비됨".** AIHub 개수(1500)는 *스튜디오 내 과적합*만 해결할 뿐, *스튜디오→wild 도메인 시프트*는 못 닫는다(전부 스튜디오라서). 증거: 1500 꽉 찬 클래스도 wild에서 **barbecue-ribs 0.00 · rice-noodle-soup 0.00 · japanese-ramen 0.10 · raw-fish 0.51**, **bread는 코드 45개인데도 0.33**. 1500인 ~28클래스 중 wild≥0.6은 pizza·돈가스·치킨뿐. → **수집 대상은 under-1500 빈약 클래스에 한정되지 않는다. 1500이어도 wild 인식률이 낮으면 동급 수집 대상.** "1500"은 exp14 학습셋 균형(잠식 방지) 기준이었지 "완료" 신호가 아님. 사실상 **pizza·pork-cutlet·fried-chicken 외 거의 전 클래스**가 wild 데이터를 필요로 함.

### 🔴 P0 — 최우선 (wild ≈0% + 데이터/다양성 빈약)
| 클래스 | 현보유 | 코드수 | wild인식 | 메모 |
|---|---|---|---|---|
| squid-dish | 111 | **1** | 0.00 | 오징어요리 |
| tteokbokki-jajang | 273 | **1** | 0.00 | 짜장떡볶이 |
| cold-ramen | 283 | **1** | 0.00 | 냉라멘(1코드=동질성 극심) |
| braised-pork-hock | 350 | 3 | 0.00 | 족발, selectstar 없음 |
| nagasaki-champon | 432 | **1** | 0.00 | 나가사끼짬뽕 |
| braised-chicken | 447 | 3 | 0.00 | 찜닭 |
| rice-soup | 462 | 3 | 0.00 | 국밥 |
| fish-cake | 482 | 2 | 0.00 | 어묵 |
| grilled-pork-belly | 601 | **1** | 0.00 | 삼겹살(채굴해도 1코드) |
| grilled-beef | 631 | 2 | 0.00 | 소고기구이 |
| seafood-jjim | 690 | 2 | 0.00 | 해물찜, SS 없음 |
| pork-cutlet-sauced | 888 | 3 | 0.00 | 소스돈가스 |
| **doenjang-jjigae** | 540 | 2 | (wild 0샘플) | 된장찌개 — wild 평가셋에도 없음, 즉시 필요 |

> **"1코드" 클래스**(squid-dish·tteokbokki-jajang·cold-ramen·nagasaki-champon·grilled-pork-belly·takoyaki)는 AIHub에 사실상 1개 요리뿐 → **group-split하면 학습 불가**. 다양한 실제 인스턴스 확보가 절대적으로 시급.

### 🟠 P1 — 차순위 (wild 0.1~0.4, ~25클래스)
black-bean-noodles, bulgogi, takoyaki, barbecue-ribs, rice-noodle-soup, hot-pot, japanese-ramen, spicy-mixed-noodles, seafood-spicy-tang, jjigae-red, noodle-plain, korean-clear-soup, savory-pancake, korean-red-soup, dumplings, udon, rice-bowl, salad, fried-food-platter, fried-rice 등. (전체·정확수치 §9)

### 🟢 P2 — 후순위 (wild ≥0.4): 이미 어느 정도 되는 클래스(pizza 0.96, fried-chicken 0.76 등). 후속.

---

## 3. 얼마나 / 다양성 기준 (가장 중요)

**개수가 아니라 "서로 다른 실제 인스턴스 수"가 목표 지표.**

- **클래스당 ≥30개의 서로 다른 실제 요리/출처**(다른 식당·다른 그릇·다른 촬영자), 각 2~4장 → **클래스당 ~80~120장**.
- **group-split 70/30**(train/test) 가능하도록 인스턴스 단위 분리 → train ~20+ 인스턴스, test ~10 인스턴스(누수 0).
- 1코드 클래스는 이걸로 **1 → 30+ 인스턴스**가 되어야 학습 의미가 생김.
- **1차 마일스톤**: P0 13클래스 × ~100장 ≈ **1,300장**(서로 다른 인스턴스 위주). 이후 P1.
- ❌ **금지**: 같은 요리/같은 출처 사진을 다량 복제·근접중복으로 채우기(= AIHub 동질성 재현). 새 정보 0.

---

## 4. 도메인 요건
- **실환경(wild)**: 휴대폰 촬영, 다양한 배경(식탁·식당·배달용기)·조명·각도. **스튜디오 단색배경 X**(그건 이미 AIHub로 충분, wild 갭을 못 닫음).
- **단일요리 우선**(평가셋과 정합). 다중요리도 받되 **per-dish 박싱** 전제로 태그.
- **출처/촬영자 메타 보존**(group-split·라이선스·PII 추적용).

---

## 5. 수집 소스 & 방법 (장단점 + 법적 주의)

| 소스 | 장점 | 주의 |
|---|---|---|
| **① 크라우드소싱**(지인·설문·앱) — 권장 | 라이선스·도메인 명확(실제 카톡사진), `friend_contributed` 방식 검증됨 | **PII 동의·익명화 필수**(과거 inbox_contributors.txt에 실명 있었음). 촬영자 코드만 보존, 실명 제거 |
| **② 웹 수집**(검색API·블로그·SNS) | 양 많음 | **저작권·ToS 위험** — 의료 제품이라 깨끗해야 함. CC 라이선스/허가된 데이터셋만, 출처·라이선스 기록 |
| **③ 공개 데이터셋** | 합법·라벨 일부 존재 | taxo59 매핑 필요, 도메인이 또 스튜디오일 수 있음(확인) |
| **④ 기존 백로그 채굴** | 즉시 가용 | `friend_contributed`에서 평가셋(783)으로 안 쓴 **multi/scene 1,688장**을 per-dish 박싱해 학습용 회수. selectstar 27k 클린도 일부 미사용분 |

> **권장 조합**: ④(즉시) + ①(주력, 합법·도메인 정확) 우선, ②는 라이선스 통제 하에 보조.

---

## 6. 에이전트 파이프라인 (단계별 — 새 세션에서 구현)

기존 워크플로 패턴 재사용(아래 §8 자산). 각 단계 LLM 비전/스크립트 조합:

1. **수집(acquire)**: 소스별 수집 + **출처/촬영자/획득시각 메타 기록**.
2. **필터(filter)**: 음식여부·단일요리·품질(블러·해상도). (기존 wild 필터 워크플로 `_filter_wild_full.wf.js` 패턴 = LLM 비전 per-image)
3. **분류(classify)**: LLM 비전으로 **taxo59 클래스 or none** 판정. (selectstar 분류 워크플로 `_gen_ss_classify_chunks.py` 패턴 그대로. 폴더명 안 믿고 이미지로)
4. **중복제거(dedup)**: perceptual hash로 근접중복 제거 **+ 같은 인스턴스 묶기**(group-id 부여). (해밍거리 임계, `_harvest_ss_clean.py`의 dHash 로직 참고)
5. **라벨(label)**: 박스 자동생성 — exp11/exp14 **모델 박스**(최고conf) 또는 **SAM2 마스크→박스**(fallback 박스 금지). 클래스는 ③의 결과.
6. **정리(organize)**: 클래스/인스턴스별 폴더 + 매니페스트 + YOLO 라벨 + **group-split 메타**(누가/언제/어느 인스턴스).
7. **QC**: ⓐ **wild 평가셋 783과 중복 금지**(pHash 대조), ⓑ PII 검사(실명·얼굴 등), ⓒ 라이선스 확인, ⓓ 클래스별 인스턴스 수 리포트.

---

## 7. 절대 지킬 제약 (이번 세션에서 깨달은 함정)
- [ ] **group-split by 인스턴스/출처** — 같은 요리/촬영자가 train·test 양쪽에 들어가면 **누수 재발**(cold-ramen 사건). 이미지 단위 무작위 분할 **금지**.
- [ ] **wild 평가셋 783 신성불가침** — 새 수집이 이걸 오염(중복)시키면 정직한 자(ruler)가 망가짐. 반드시 dedup 대조.
- [ ] **동질성 금지** — 인스턴스 다양성이 목표. 같은 dish 다량 X.
- [ ] **PII 익명화** — 실명·연락처·얼굴 제거(보안감사 지적: 과거 기여자 실명·작성자 이메일 노출). 촬영자는 anon 코드만.
- [ ] **라이선스 준수** — 웹 수집분은 출처·라이선스 기록, 불명확하면 학습 제외.

---

## 8. 재사용 자산 (이미 만들어진 것)
- **taxo59 클래스 목록(en+ko)**: §부록 / `docs/deliverables/A100-setup-and-experiments.md §9.1`.
- **LLM 비전 분류 워크플로 패턴**: `docs/superpowers/plans/exp06_review/_gen_ss_classify_chunks.py`(생성기), 결과 집계 `_harvest_ss_clean.py`(dHash dedup 포함).
- **wild 필터 워크플로**: `_filter_wild_full.wf.js`(단일요리/OOD 판정).
- **selectstar→taxo59 검증 매핑**: `ss_taxo59_mapping_verified.csv`.
- **자동라벨/박스**: `_build_exp14_balanced.py`(모델박스, fallback 없음). + SAM2 도입 검토(배경제거·tight박스).
- **평가**: `_eval_exp14_full.py`(3셋: AIHub val/selectstar held-out/wild 783).
- **모델**: `runs/food_yolo/exp11_..._taxo59bal1500_.../weights/best.pt`(범용), exp14(균형 보강).
- **기존 wild 자산**: `wild_keep_dedup_list.txt`(783 평가셋), `wild_classification_2026-06-04.csv`(2,471 전체 분류 — 미사용 multi/scene 채굴 후보).

---

## 9. 부록

### 9.1 산출물 포맷(권장)
```
data/wild_collected/
  <class>/<instance_id>/<img>.jpg        # instance_id = group-split 키
  labels/<img>.txt                       # YOLO (class cx cy w h)
  manifest.csv  # img,class,instance_id,source,license,phash,split(train|test|hold),collected_at
```
- `instance_id`로 group-split. `source`/`license`로 합법성, `phash`로 dedup·평가셋대조.

### 9.2 우선순위 표 재산출
`backend/.venv/Scripts/python.exe /tmp/collect_priority.py` 패턴: exp14 데이터 보유량 + `_eval_exp13_wild.csv`(wild 인식률) + bal1500 코드다양성 조인 → wild 낮은순 정렬. (이 문서의 P0/P1은 그 출력)

### 9.3 한 줄 목표
**"P0 13클래스부터, 클래스당 서로 다른 실제 요리 30+개를, wild 도메인으로, 인스턴스 단위 분할 가능하게, 라이선스·PII 깨끗하게 모은다."**

---
**다음 세션 시작 방법**: 이 문서를 읽고 → §6 파이프라인을 구현(기존 §8 워크플로 패턴 재사용) → ④백로그 채굴 + ①크라우드소싱으로 P0부터. wild 인식률이 단일 성공지표.
