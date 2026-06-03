# 디스크 정리 기록 — 2026-06-03

> **사유**: exp12 학습 시 디스크 부족(여유 43.7GB < cache 필요 106GB). 구 실험 `.npy` 캐시 정리.
> **방식**: `.npy` **캐시만** 삭제. 데이터셋 이미지·라벨·모델(runs/)은 **보존**. → 재학습 시 cache=disk가 자동 재생성하므로 데이터 손실 없음.

## 삭제 대상 (.npy 캐시만, 7개 superseded 데이터셋)
| 데이터셋 | .npy 크기 | 실험 | 데이터셋 재생성(필요시) |
|---|---|---|---|
| aihub_yolo_50 | 140.0 GB | exp01~05 (구 50클래스) | raw aihub → 50클래스 파이프라인(pre-exp06) |
| aihub_yolo_50_balanced_500 | 42.1 GB | exp03 | 〃 + balanced 다운샘플 |
| aihub_yolo_50_minority_aug_train500_val100 | 33.3 GB | exp04 | 〃 + minority 증강 |
| aihub_yolo_50_minority_dup_train500_val100 | 33.3 GB | exp05 | 〃 + minority 복제 |
| aihub_yolo_taxo63_bal500 | 39.3 GB | exp06~08 | `_build_taxo63.py` + `_build_balanced_taxo63.py` |
| aihub_yolo_taxo62_bal500 | 38.6 GB | exp09 | `_build_taxo62.py` + `_build_balanced_taxo62.py` |
| aihub_yolo_taxo59_bal500 | 37.5 GB | exp10 | `_build_taxo59.py` + `_build_balanced_taxo59.py` |
| **합계** | **~364 GB** | | (빌드 스크립트 전부 git 커밋됨) |

> ⚠️ **.npy만 삭제**이므로 위 데이터셋의 이미지/라벨은 그대로 남음 → 재학습 시 캐시만 다시 생성됨(rebuild 불필요).
> 혹시 디렉터리 통째로 지운다면(~390GB), 위 "재생성" 열의 빌드 스크립트로 복원.

## 보존 (현재 사용 중 — 절대 삭제 금지)
| 데이터셋 | 용도 |
|---|---|
| aihub_yolo_taxo59_exp12_takoyaki | **exp12 학습 중** |
| aihub_yolo_taxo59_bal1500 | exp11 모델 + exp12 평가 val |
| aihub_yolo_taxo59 | taxo59 빌드 소스 (.npy 0) |
| aihub_yolo_split | 424코드 원본 (모든 taxo 빌드 base, .npy 0) |
| selectstar | takoyaki held-out test 원본 |
| runs/ (655MB) | **학습 모델 전부 (exp01~12 best.pt)** |

## 검증 (삭제 전 확인 사항)
- 삭제 목록 7개에 **보존 데이터셋(exp12_takoyaki·bal1500·taxo59·split·selectstar) 미포함** 확인 ✅
- `*.npy`만 매칭 → 이미지(.jpg/.png)·라벨(.txt)·모델(.pt) 영향 없음 ✅
- exp12는 train 캐싱 비활성(디스크부족 자동감지) → 삭제와 무관 ✅

## .npy 정체 실증 (삭제 안전성 근거)
직접 열어 확인한 결과 — **모든 .npy는 `cache=disk` 이미지 캐시**:
- 위치: 전부 `images/` 폴더 (`taxo59_bal500` 기준 32,770개 전부, 다른 폴더 0)
- 내용: `shape=(640,640,3) uint8` = 640×640으로 디코딩·리사이즈된 이미지 배열
- 대응: 모든 .npy에 짝 `.jpg` 존재 (샘플 500개 중 누락 0)
- **결정적**: `np.load(.npy) == cv2.imread(.jpg)` (원본 BGR과 byte 단위 완전 일치)
- → 고유 데이터 0. 원본 `.jpg`에서 다음 `cache=disk` 학습 시 **자동 재생성**. 삭제 시 손실 전무.

## 사용 명령 (사용자 직접 실행)
```powershell
$base = "C:\Lemon-sin\data\food_images\processed"
@("aihub_yolo_50","aihub_yolo_50_balanced_500","aihub_yolo_50_minority_aug_train500_val100",
  "aihub_yolo_50_minority_dup_train500_val100","aihub_yolo_taxo63_bal500",
  "aihub_yolo_taxo62_bal500","aihub_yolo_taxo59_bal500") |
  ForEach-Object { cmd /c "del /f /q /s `"$base\$_\*.npy`"" }
"여유: {0:N1}GB" -f ((Get-PSDrive C).Free/1GB)
```
dry-run 검증(2026-06-03): 삭제 .npy 318,140개(~364GB) / 비-npy(이미지·라벨) 전부 보존 / 보존데이터셋 5개 미포함 확인.
