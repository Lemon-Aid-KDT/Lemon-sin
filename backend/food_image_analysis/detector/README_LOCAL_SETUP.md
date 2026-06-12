# 디텍터 인계 자료 — 로컬 배치 안내

> 출처: 팀원 인계 `detector_handoff.zip` (2026-06-12 수령). 상세 내용은 `DETECTOR_인계.md` 참조.
> 이 폴더에는 **코드·문서만** 커밋한다. 모델 가중치(.pt, 총 121MB)는 git 금지(2MB+ 규칙)라 로컬 보관.

## 모델 가중치 위치 (git 외부)

```
C:\Lemon-sin\runs\detector\detector_best.pt   (18.3MB)  = v3 — 인계 문서의 "최종 설정" 기준 모델
C:\Lemon-sin\runs\detector\fastv5_mos05.pt    (48.8MB)  = fast v5 mosaic0.5 (한상 mAP50 0.768)
C:\Lemon-sin\runs\detector\fastv5_mos10.pt    (48.8MB)  = fast v5 mosaic1.0 (한상 mAP50 0.833, 현재 최강)
```

다른 PC에서 받으려면 팀 파일공유로 .pt 3개를 위 경로에 복사할 것.

## 주의

- `compare_demo.py` / `detector_demo.py` / `food_filter.py`는 인계자 PC 경로(`D:\runs\detect\...` 등)를
  참조할 수 있음 — 실행 전 모델 경로를 위 `runs\detector\` 경로로 수정 필요.
- 인계 문서가 언급하는 평가셋(`jeongsik_eval.yaml`, `realapp_eval.yaml`, 한상 8장 라벨)은
  zip에 미포함 — 필요 시 인계자에게 별도 요청.
- 분류기(exp16b, 지원 40클래스)와는 **별개 모델**: 디텍터 = 음식 "위치"만(1-class),
  분류기 = 음식 "종류". 통합 시 디텍터 박스 → 분류기 crop 파이프라인 검토.
