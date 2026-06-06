# A100 원격 PaddleOCR 한국어 recognizer 본학습 가이드

이 머신(Apple Silicon, CPU-only)에서는 데이터셋·검증된 plan까지만 준비했다. 실제 본학습은
**NVIDIA A100 GPU 서버**에서 원격으로 실행한다. 이 문서는 그 end-to-end 절차다.

대상 산출물(이 repo, gitignored — git이 아닌 별도 전송):
- 데이터셋: `outputs/generated/supplement-learning/2026-06-05/operator-review/datasets/supplement-paddleocr-rec-crawling/v1/`
  (실사진 crop + CLOVA teacher 라벨, `rec/rec_gt_{train,val}.txt` + `train.txt`/`val.txt` + `dict.txt`)
- 검증된 plan: `outputs/.../reconciled/paddleocr-finetune-run-plan.recognition.crawling.json` (status: ok)
- 데이터셋 동봉 런북: `datasets/supplement-paddleocr-rec-crawling/RUN_ON_GPU.md`

> ⚠️ 데이터셋은 CLOVA teacher 텍스트(원문)를 포함하므로 `.gitignore` 처리됨 → **git push 금지**.
> A100로는 `rsync`/`scp`/오브젝트 스토리지(S3/GCS)로만 전송한다.

---

## 0. A100 서버 확보 (택1)
- 클라우드: AWS `p4d.24xlarge`(A100×8) / `p4de`, GCP `a2-highgpu-1g`(A100×1), Azure `NDv4`, Lambda Cloud, RunPod, Vast.ai, Paperspace.
- 단일 A100 40/80GB면 충분(이 데이터 규모). 멀티-GPU면 `--gpus 0,1,...`로 가속.
- OS: Ubuntu 22.04 + NVIDIA driver(≥535) + CUDA 12.x.

## 1. 데이터 전송 (git 아님)
로컬(이 머신)에서:
```bash
DS="outputs/generated/supplement-learning/2026-06-05/operator-review/datasets/supplement-paddleocr-rec-crawling/v1"
rsync -avz --progress "$DS/" a100:/workspace/rec_dataset/v1/
# (대안) tar czf rec_v1.tgz "$DS" && scp rec_v1.tgz a100:/workspace/ && ssh a100 'tar xzf /workspace/rec_v1.tgz -C /workspace/'
```
plan JSON도 전송:
```bash
scp outputs/.../reconciled/paddleocr-finetune-run-plan.recognition.crawling.json a100:/workspace/
```

## 2. A100 환경 구성
```bash
# (A100에서)
python3.12 -m venv /workspace/.venv-paddle && source /workspace/.venv-paddle/bin/activate
pip install -U pip
# GPU 빌드 (CUDA 12.x 예시; 서버 CUDA에 맞춰 인덱스 변경)
pip install paddlepaddle-gpu==3.* -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
pip install "paddleocr==3.6.*" "paddlex==3.6.*" rapidfuzz pillow matplotlib
python -c "import paddle; print('CUDA:', paddle.is_compiled_with_cuda(), 'gpus:', paddle.device.cuda.device_count())"
# PaddleOCR 학습 플러그인 설치 (모델 등록에 필요)
mkdir -p "$(python -c 'import paddlex,os;print(os.path.join(os.path.dirname(paddlex.__file__),"repo_manager","repos"))')"
paddlex --install PaddleOCR -y --platform github.com
# 플러그인 config를 PaddleX repo_apis 경로로 복사 (이 머신에서 적용했던 우회와 동일)
SP=$(python -c 'import paddlex,os;print(os.path.dirname(paddlex.__file__))')
mkdir -p "$SP/repo_apis/PaddleOCR_api/configs"
cp "$SP/repo_manager/repos/PaddleOCR/configs/rec/PP-OCRv5/multi_language/korean_PP-OCRv5_mobile_rec.yml" \
   "$SP/repo_apis/PaddleOCR_api/configs/korean_PP-OCRv5_mobile_rec.yaml"
```

## 3. 데이터셋 검증
```bash
python - <<'PY'
from paddlex.utils.config import get_config
from paddlex import build_dataset_checker
import paddlex, os
cfg=get_config(os.path.join(os.path.dirname(paddlex.__file__),"configs/modules/text_recognition/korean_PP-OCRv5_mobile_rec.yaml"),
  overrides=["Global.dataset_dir=/workspace/rec_dataset/v1","Global.mode=check_dataset","Global.device=gpu:0","Global.output=/workspace/_chk"])
print("check:", bool(build_dataset_checker(cfg).check()))
PY
```

## 4. 본학습 (A100)
PaddleX 직접(권장 — 이 머신에서 검증된 경로와 동일, device만 gpu):
```bash
python - <<'PY'
from paddlex.utils.config import get_config
from paddlex import build_trainer
import paddlex, os
cfg=get_config(os.path.join(os.path.dirname(paddlex.__file__),"configs/modules/text_recognition/korean_PP-OCRv5_mobile_rec.yaml"),
  overrides=[
    "Global.dataset_dir=/workspace/rec_dataset/v1",
    "Global.mode=train", "Global.device=gpu:0",          # 멀티: gpu:0,1,2,3
    "Global.output=/workspace/output/supplement_rec_crawling_v1",
    "Train.epochs_iters=100", "Train.batch_size=128",    # A100 80GB면 256까지
    "Train.learning_rate=0.0005", "Train.save_interval=1", "Train.eval_interval=1",
  ])
build_trainer(cfg).train()
PY
```
(대안) 검증된 plan을 그대로 실행:
```bash
PYTHONPATH=Nutrition-backend python scripts/run_paddleocr_finetune_plan.py \
  --plan /workspace/paddleocr-finetune-run-plan.recognition.crawling.json \
  --paddleocr-root "$SP/repo_manager/repos/PaddleOCR" --execute --timeout-seconds 86400
```
산출: `/workspace/output/supplement_rec_crawling_v1/best_accuracy/{best_accuracy.pdparams, inference/}`.

## 5. 재평가(누수 없는 holdout) → 95% 게이트
holdout 이미지(52장)는 별도 전송 필요(`ocr-ground-truth-review-bundle/images/`, gitignored). 그 후:
```bash
./.venv-paddle/bin/python scripts/paddleocr_clova_eval.py \
  --bundle-dir /workspace/ocr-ground-truth-review-bundle \
  --rec-model-dir /workspace/output/supplement_rec_crawling_v1/best_accuracy/inference \
  --det-box-thresh 0.15 --det-thresh 0.1 --det-unclip-ratio 2.0 \
  --output /workspace/eval-finetuned.json --observations-output /workspace/obs-finetuned.jsonl --apply
# 형식 게이트
PYTHONPATH=Nutrition-backend python scripts/merge_paddleocr_text_observations_into_benchmark.py \
  --benchmark-manifest <splits.assignment.json> --observations /workspace/obs-finetuned.jsonl --output /workspace/merged-ft.jsonl
PYTHONPATH=Nutrition-backend python scripts/build_paddleocr_text_extraction_eval_summary.py \
  --benchmark-manifest /workspace/merged-ft.jsonl --eval-split holdout --provider paddleocr_local \
  --leakage-check-passed --privacy-review-cleared --output /workspace/ft-eval-summary.json
PYTHONPATH=Nutrition-backend python scripts/gate_paddleocr_text_extraction_target.py \
  --eval-summary /workspace/ft-eval-summary.json --min-fixtures 30 --output /workspace/ft-target-gate.json
```
**`field_match_ratio` 및 게이트 통과(≥0.95) 확인.** 미달 시: epoch↑, 데이터 확대(`--max-images-per-product 6` 이미 적용 / 카테고리 추가), 라벨 노이즈 정제(길이/문자 필터, ingredient lexicon 후처리), det 튜닝 유지.

## 6. 하이퍼파라미터 / 운영 팁
- batch: A100 40GB→128, 80GB→256. AMP(`Global.use_amp=True` 지원 시) 권장.
- epochs: 50–100. eval_interval=1로 best 저장. early-stop은 norm_edit_dis/acc 정체 시.
- 멀티-A100: `Global.device=gpu:0,1,2,3` + `paddle.distributed.launch`(plan 커맨드가 이미 `--gpus` 사용).
- 예상 시간: 단일 A100, ~70K crop × 100 epoch ≈ 수 시간(모델이 mobile rec로 작음).
- 결과 모델 회수: `output/.../best_accuracy/inference/` 를 로컬로 rsync → 서비스 배포 검토(별도 promotion gate).

## 7. 보안/정책
- teacher 텍스트 데이터셋·holdout 이미지·.env·venv는 **git 금지**(이미 .gitignore 처리). A100 전송은 rsync/스토리지로만.
- 학습된 모델 가중치만 회수. 원문 텍스트/이미지는 A100에서 학습 후 정리(필요 시).
