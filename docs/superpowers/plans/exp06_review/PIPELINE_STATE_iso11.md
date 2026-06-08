# PIPELINE_STATE_iso11 — 11클래스 격리 실험(exp17) A/B/C 3-arm 자율 파이프라인

> 목표: selectstar 잠식이 "공존" 탓인지 + AIHub vs selectstar wild 전이 우위 측정. **수량 교란 제거**(B를 A와 매칭).
> - A=AIHub만(10210) / B=수량매칭 mix(10210, 50% AIHub+50% ss, per-class A와 동일) / C=selectstar만(8800). 모두 11클래스, 공통 AIHub val 940.
> - 핵심: **A vs C**(소스 단독 우위, 수량≈) / **B−A**(같은 양에서 절반을 ss로 바꾸면? = 순수 소스혼합 효과) / **B vs exp13**(격리효과)

## 🔁 재개 프로토콜 (새 세션/cron이 읽으면)
1. 단계표 완료체크로 위치 파악.
2. **이미 실행 중이면**(yolo.exe GPU 학습중 / 해당 results.csv 최근 갱신) **아무것도 말고 종료**.
3. 멈춰 있으면 다음 미완 단계 1개만 재개. **완료체크 = results.csv 50ep(또는 patience). best.pt는 매ep 갱신이라 완료신호 아님.**
4. S5 완료 시 이 파일 done + cron CronDelete + 보고 + 메모리 갱신.

## 경로
- venv: `C:\Lemon-sin\backend\.venv\Scripts\python.exe`
- 학습 ps1(파라미터화): `docs/superpowers/plans/exp15_taxo55_run.ps1 -Data <yaml> -RunName <name>`
- 빌드: `_build_iso11.py`(A/C) + `_build_iso11_Beq.py`(B 수량매칭 재빌드, 완료). 데이터셋 `iso11_A_aihub`(10210)/`iso11_B_both`(**10210 수량매칭** AIHub5105+ss5105)/`iso11_C_ss`(8800), val 940 공통.
- eval: `_eval_iso11.py` (준비완료, device=0 → 학습중 실행금지)

## 단계
| 단계 | 완료체크 | 재개 액션 |
|---|---|---|
| **S1 A 학습** | `runs/food_yolo/exp17a_iso11_aihub_s42_b16_w8_cache_disk_det_true/weights/best.pt` + results.csv 50ep | `& exp15_taxo55_run.ps1 -Data ...iso11_A_aihub\data.yaml -RunName exp17a_iso11_aihub` |
| **S2 B 학습** | `exp17b_iso11_both_*` results.csv 50ep | S1후: `... -Data ...iso11_B_both\data.yaml -RunName exp17b_iso11_both` |
| **S3 C 학습** | `exp17c_iso11_ss_*` results.csv 50ep | S2후: `... -Data ...iso11_C_ss\data.yaml -RunName exp17c_iso11_ss` |
| **S4 평가** | eval 로그 출력 | S3후 GPU여유시: `python _eval_iso11.py > /tmp/eval_iso11.log 2>&1` (A/B/C+exp11/exp13 × wild 11클래스, 부트스트랩) |
| **S5 진단/정리** | — | A vs C·B−A·B−C·vs exp13 해석. 메모리 갱신. cron 삭제 |

## ✅ DONE (2026-06-08) — S1~S5 완료, cron 삭제됨
- A(AIHub만)/B(매칭mix)/C(ss만) 학습 + S4 eval(`_eval_iso11.py`) 완료.
- **wild(193장,11클래스) strict: A 0.565 / B 0.850 / C 0.891 / exp11 0.332 / exp13 0.917**
- **핵심 반전: selectstar >> AIHub (wild).** paired(수량통제): **C−A +0.326[+0.254~+0.399] 유의** · B−A +0.285 유의 · B−C −0.041 노이즈(AIHub 추가무용) · B−exp13 −0.067(격리 불필요, 데이터많은 exp13↑).
- 결론: selectstar는 커버 클래스에 "거의 실데이터급" wild 전이. AIHub(고통제 스튜디오)는 wild 약함. 한계=커버리지(~26/50). 이전 "selectstar=studio라 wild 못품" 보정(per-class는 우수, 문제는 coverage+잠식).
- cron `c33a6627` CronDelete 완료. 산출: `_eval_iso11.py`, 로그 /tmp/eval_iso11.log.
