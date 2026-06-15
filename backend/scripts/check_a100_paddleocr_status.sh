#!/usr/bin/env bash
set -euo pipefail

# Query the Windows A100 PaddleOCR recognizer status without storing credentials.
# The SSH client prompts for the password, so the shared password never lands in
# this script, shell history as an argument, or repo-tracked files.

A100_HOST="${A100_HOST:-155.230.153.222}"
A100_USER="${A100_USER:-lemon-aid}"
A100_WORKSPACE_ROOT="${A100_WORKSPACE_ROOT:-G:\\lemon-aid\\paddleocr_rec_work}"
A100_RUN_SUFFIX="${A100_RUN_SUFFIX:-v2_low_lr_mix_20260610_stage3}"
A100_MODE="${A100_MODE:-full}"
A100_STATUS_SCRIPT="${A100_STATUS_SCRIPT:-G:\\lemon-aid\\paddleocr_rec_work\\Lemon-Aid\\backend\\scripts\\show_a100_paddleocr_windows_status.ps1}"

json_flag=()
if [[ "${A100_STATUS_JSON:-0}" == "1" ]]; then
  json_flag=(-Json)
fi

ssh "${A100_USER}@${A100_HOST}" \
  "powershell -NoProfile -ExecutionPolicy Bypass -File \"${A100_STATUS_SCRIPT}\" -WorkspaceRoot \"${A100_WORKSPACE_ROOT}\" -RunSuffix \"${A100_RUN_SUFFIX}\" -Mode \"${A100_MODE}\" ${json_flag[*]}"
