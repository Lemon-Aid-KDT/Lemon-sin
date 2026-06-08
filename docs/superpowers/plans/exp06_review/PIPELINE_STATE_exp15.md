# PIPELINE_STATE — taxo50 2-run (drop/merge효과 + 실데이터효과) 자율 파이프라인

> **2026-06-07 전환**: taxo55 → **taxo50**으로 분류 정제. exp15(taxo55)는 exp15a만 완료하고 **exp15b는 SKIP(taxo55 superseded)**. 이제 taxo50 2-run(exp16a/b)로 진행.
> - exp16a = taxo50 AIHub만 (drop/merge 효과, vs exp11 taxo59 / exp15a taxo55)
> - exp16b = taxo50 AIHub + realworld (실데이터 순효과, vs exp16a)

## taxo50 정의 (taxo59 기준 순변경)
- DROP(6): cold-ramen, nagasaki-champon, tteokbokki-jajang, tteokbokki-cream-rose (taxo55때) **+ hot-pot(전골), korean-clear-soup(맑은국)**
- MERGE(3): korean-red-soup→jjigae-red, noodle-plain→kalguksu, pork-cutlet-sauced→pork-cutlet-dry
- 빌드: `_build_taxo50.py`. 데이터셋:
  - `aihub_yolo_taxo50` (exp16a): train **56020** / val **4600**, nc50
  - `aihub_taxo50_plus_realworld` (exp16b): train 56020+realworld **1177**=**57197** / val 4600

## 🔁 재개 프로토콜 (새 세션/cron이 읽으면)
1. 단계 표 완료체크로 위치 파악.
2. **이미 실행 중이면**(yolo.exe GPU 사용 / 해당 results.csv 최근 갱신) **이번엔 아무것도 말고 종료**.
3. 멈춰 있으면 다음 미완 단계 1개만 재개.
4. S4 완료 시 이 파일 done 갱신 + CronList서 cron `5afa6910` CronDelete + 보고 + 메모리 갱신.

## 경로
- venv py: `C:\Lemon-sin\backend\.venv\Scripts\python.exe`
- 학습 ps1(BOM, 파라미터화): `C:\Lemon-sin\docs\superpowers\plans\exp15_taxo55_run.ps1 -Data <data.yaml> -RunName <name>`
- eval: `docs/superpowers/plans/exp06_review/_eval_taxo55.py` (name기반 — taxo50 모델도 동작. MODELS에 exp16a/b 경로 추가 필요)

## 단계
| 단계 | 완료체크 | 재개 액션 |
|---|---|---|
| ~~exp15a(taxo55)~~ | ✅ DONE (drop-4 데이터포인트로 보존) | — |
| ~~exp15b(taxo55+real)~~ | ⏭️ SKIP (taxo50로 대체) | 실행하지 말 것 |
| **S1' exp16a 학습** | `runs/food_yolo/exp16a_taxo50_aihub_pc1_s42_b16_w8_cache_disk_det_true/weights/best.pt` + results.csv 완료 | 멈췄으면 `& exp15_taxo55_run.ps1 -Data ...aihub_yolo_taxo50\data.yaml -RunName exp16a_taxo50_aihub_pc1` |
| **S2' exp16b 학습** | `runs/food_yolo/exp16b_taxo50_aihubreal_pc1_s42_b16_w8_cache_disk_det_true/weights/best.pt` + results.csv 완료 | S1' 완료 후: `& exp15_taxo55_run.ps1 -Data ...aihub_taxo50_plus_realworld\data.yaml -RunName exp16b_taxo50_aihubreal_pc1` |
| **S3' 평가** | `_eval_taxo50_wild.csv` 존재 | **준비완료** `_eval_taxo50.py` 실행(merge GT 정규화·DROP50 제외, exp11/15a/16a/16b × wild+realworld val, name기반). **exp16b 학습완료·GPU여유 시에만**(device=0) |
| **S4' 진단/정리** | — | drop/merge효과(exp16a vs exp15a vs exp11)·실데이터효과(exp16b vs exp16a)·회복클래스(jjigae-red·kalguksu·pork-cutlet-dry 병합 수혜, japanese-ramen·udon). 메모리 갱신. cron 삭제 |

## ✅ DONE (2026-06-08) — S1'~S4' 전부 완료, cron 삭제됨
- **S1' exp16a**(taxo50 AIHub) / **S2' exp16b**(taxo50+realworld) 둘 다 50ep 완주.
- **S3' eval 완료**(`_eval_taxo50.py`, 부트스트랩 CI). 결과:
  - **WILD(739, 교차출처 정직지표) strict**: exp16a 0.369[0.336~0.405] → **exp16b 0.479[0.441~0.517]**
  - **paired 실데이터 순효과 exp16b−exp16a = +0.109 [+0.080~+0.139], P=1.00 → 유의(CI가 0 밖, 멀티시드 불필요)**
  - realworld val(367, 동일출처라 낙관): exp16a 0.401 → exp16b **0.627**(+0.226)
  - 분류체계 효과: exp16a−exp15a +0.004 / exp16a−exp11 −0.008 = **둘다 노이즈(0 포함)** → taxo50 정리는 wild 무효과(정리/해석 가치만)
- **S4' 진단**: 도메인갭 가설 입증 — 실데이터 2%(1,177장)만 섞어도 wild +30% 상대. **데이터가 lever 확정.** 단일시드지만 효과가 CI 밖이라 robust.
- cron `5afa6910` **CronDelete 완료**. 산출: `_eval_taxo50.py`, `_eval_taxo50_wild.csv`.
