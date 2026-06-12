# -*- coding: utf-8 -*-
r"""
디텍터 최종 학습 — yolo26x → yolo11x 순차 (둘 다 학습 후 비교해서 승자 선택)
실행: python final_train.py
주의:
  - data 경로(fastv5_a100.yaml)를 본인 환경에 맞게 수정할 것.
  - 공유 GPU 서버는 workers=0 권장 (DataLoader 워커 hang 방지).
  - 백그라운드 권장(SSH 끊겨도 유지):
    Start-Process python -ArgumentList "final_train.py" -RedirectStandardOutput train_log.txt -WindowStyle Hidden
"""
from ultralytics import YOLO

CFG = dict(
    data=r"fastv5_a100.yaml",      # ← 본인 데이터셋 yaml 경로로 수정
    epochs=100, patience=30, batch=16, imgsz=640,
    lr0=0.001, optimizer="AdamW", cos_lr=True, warmup_epochs=5,
    mosaic=1.0, close_mosaic=15, mixup=0.1,      # mosaic 1.0 = ablation으로 결정된 값
    hsv_h=0.02, hsv_s=0.8, hsv_v=0.5, degrees=10, translate=0.1, scale=0.5,
    project=r"runs/detect", workers=0, cache=False, save=True, plots=True,
)

def main():
    for model_name, run_name in [("yolo26x.pt", "final_26x_640"), ("yolo11x.pt", "final_11x_640")]:
        try:
            print(f"\n===== TRAIN {model_name} -> {run_name} =====", flush=True)
            YOLO(model_name).train(name=run_name, exist_ok=True, **CFG)
        except Exception as e:
            print(f"!! {model_name} 실패: {e!r} -- 다음 모델로 진행", flush=True)

if __name__ == "__main__":
    main()
