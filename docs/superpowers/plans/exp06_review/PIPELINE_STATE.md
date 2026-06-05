# PIPELINE_STATE — exp14 selectstar 완전활용 → balanced 진단 (자율 파이프라인)

> **목적**: selectstar 전수 per-image 분류 → 클린 하베스트(노이즈 정제 + OOD폴더서 grilled류 채굴) → balanced 데이터셋(cap1500 균등화, 부족클래스만 클린 selectstar로 채움, fallback박스 없음) → 학습 → wild 평가 → exp13 잠식 원인(개수 vs 다양성) 진단.
> **goal**: 전체 파이프라인을 완료까지 자율 진행. **토큰/rate-limit으로 멈춰도 이 파일 기준으로 재개.**

## 🔁 재개 프로토콜 (새 세션 / resume cron이 이 파일을 읽으면)
1. 아래 **단계 표**의 "완료체크"로 현재 위치 파악(맨 아래 "현재 상태"도 참고).
2. **중복 방지 — 먼저 실행 중인지 확인**:
   - 청크 워크플로 진행중? `/workflows` 또는 task 출력파일 크기(0B=진행중).
   - 학습 중? `nvidia-smi`(GPU 사용) + exp14 results.csv 최근 수정시간(수 분 내 = 진행중).
   - **실행 중이면 이번 tick은 아무것도 하지 말고 종료**(다음 tick/알림 때 재확인).
3. 멈춰 있으면 "다음 미완 단계"의 **재개 액션** 1개만 실행.
4. 전 단계 완료 시: 이 파일 "현재 상태"를 done으로 갱신 → `CronList`에서 resume cron 찾아 `CronDelete` → 사용자에 최종 보고. (goal 자동 해제)

## 경로 / ID
- 스크립트 폴더: `C:\Lemon-sin\docs\superpowers\plans\exp06_review\`
- venv python: `C:\Lemon-sin\backend\.venv\Scripts\python.exe`
- 청크 task 출력(휘발성 temp): `C:\Users\KDS11\AppData\Local\Temp\claude\C--Lemon-sin\6ba527d7-6323-4f74-8261-c65c844550f3\tasks\{id}.output`
- 청크 IDs: **chunk1** task=`wk7b9v0ca` run=`wf_57f2efe2-2a7` / **chunk2** task=`wwyym9cwb` run=`wf_bacf17b7-9a8` / **chunk3** task=`wfs4cqxax` run=`wf_316852ba-03b`
- 청크 스크립트: `_ssclassify_chunk{1,2,3}.wf.js` (재개 시 `Workflow({scriptPath, resumeFromRunId: 위 run id})` → 완료 에이전트 캐시 반환, 저렴)

## 단계 (S1→S6)
| 단계 | 완료체크 | 재개 액션 |
|---|---|---|
| **S1** per-image 분류 (3청크, 35,988장) | 3 청크 task출력에 `"count"` 포함(완료) | 미완 청크: `Workflow(scriptPath=_ssclassify_chunkN.wf.js, resumeFromRunId=wf_...)`. 완료 즉시 각 출력의 `result.rows`를 repo로 persist: `ss_classify_chunkN.json` |
| **S2** harvest | `ss_harvest_clean_list.tsv` + `ss_harvest_by_class.csv` 존재 | `python _harvest_ss_clean.py <c1.output> <c2.output> <c3.output>` (persist json 있으면 그걸로). gap-fill: `_ssclassify_missing.txt`>3000이면 그 목록으로 분류 워크플로 1회 추가, 적으면 무시 |
| **S3** build | `data/.../aihub_yolo_taxo59_exp14_balanced/data.yaml` + train img>60000 | `python _build_exp14_balanced.py` (GPU 박스생성 ~수십분) |
| **S4** train | `runs/food_yolo/exp14_balanced_pc1_*/weights/best.pt` + results.csv 50ep(또는 patience 조기종료) | PowerShell 백그라운드: `& C:\Lemon-sin\docs\superpowers\plans\exp14_balanced_run.ps1`. results.csv 갱신 중이면 대기 |
| **S5** eval | `_eval_exp14_wild.csv` 등 존재 | `_eval_exp13_full.py` 복제→`_eval_exp14_full.py`, MODELS에 exp14 추가(exp11/13/14 동시) → 실행. 3셋(AIHub val / selectstar held-out / wild 783) |
| **S6** 진단/보고/정리 | — | exp11 vs exp13 vs exp14 **wild** 비교 → 균등화가 잠식 막았나(전체↑·비보강군 안깎임=개수원인 / 여전히 잠식=다양성원인) 결론. memory 갱신. resume cron 삭제 |

## 핵심 설계 메모
- balanced = 모든 클래스 cap **1500**, AIHub<1500인 38클래스만 클린 selectstar로 1500까지 채움(초과 금지=개수균등). selectstar 박스 = exp11 모델 tight박스만, **fallback 없음**(no-box 이미지는 드롭).
- 채굴 핵심: BBQ→grilled-pork-belly(370)·grilled-beef(580), galbi(barbecue-ribs는 이미 cap). 둘 다 wild 0.000이라 최대 기회.
- 비교 기준: exp11(noSS, 부족클래스 방치) · exp13(11클래스 +800 초과→wild 잠식). wild 베이스라인 exp11 strict 0.350.

## 현재 상태 (2026-06-05, S4 학습 단계)
- **S1·S2·S3 완료**. 데이터셋 `aihub_yolo_taxo59_exp14_balanced`(train 68,713 = base 60,840 + selectstar 7,873, val 동일). 부족 클래스 1500 균등 충족, 채굴 grilled-pork-belly 370→601·grilled-beef 580→631. harvest/build 산출물 전부 repo에 존재.
- **S4 학습 실행중**: `exp14_balanced_run.ps1`(task=`b3wlstdzt`, 정상 시작 확인). run 폴더 `runs/food_yolo/exp14_balanced_pc1_s42_b16_w8_cache_disk_det_true`. ~50ep, 수 시간. ⚠️ps1은 UTF-8 BOM 필수(아니면 PS5.1 파싱 실패)—이미 수정됨.
- **재개 액션(S4)**: best.pt 없고 results.csv 갱신 안되면(학습 죽음) ps1 재실행(`& ...exp14_balanced_run.ps1`, 백그라운드). results.csv 갱신 중이면 **대기**(재실행 금지). best.pt 존재+50ep(또는 조기종료)면 **S5**.
- **S5 재개**: `_eval_exp14_full.py` **이미 생성됨**(exp11/exp13/exp14 3모델, FILLED/rest 분리 비교 포함). 그냥 `python _eval_exp14_full.py > /tmp/eval14.log 2>&1` 실행. 산출 `_eval_exp14_{wild,aihub_val,heldout}.csv`.
- **S6**: exp11 vs exp13 vs exp14 wild 비교 → 결론. memory 갱신. cron `4245b093` 삭제.
