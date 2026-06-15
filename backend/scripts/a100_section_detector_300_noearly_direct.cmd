@echo off
setlocal EnableExtensions

set "BASE=G:\lemon-aid\section_dataset_v2_panel_pseudo_a100"
set "PYTHON=G:\anaconda3\envs\lemonaid_project\python.exe"
set "TRAIN_SCRIPT=%BASE%\train_ultralytics_section_detector.py"
set "DATA=%BASE%\dataset.yaml"
set "PROJECT=%BASE%\runs"
set "MODEL=yolo26s.pt"
set "NAME=sec_v2_panel_pseudo_a100_yolo26s_300ep_noearly_52g_b070_cmdstart_v1"
set "MIN_FREE_MIB=52000"
set "LOG=%BASE%\train_%NAME%.log"
set "ERR=%BASE%\train_%NAME%.err"
set "STATE_LOG=%BASE%\queue_keeper.state.log"

for /f "usebackq tokens=*" %%A in (`nvidia-smi --query-gpu^=memory.free --format^=csv,noheader,nounits`) do (
    set "FREE_MIB=%%A"
    goto :got_free
)

:got_free
for /f "tokens=* delims= " %%A in ("%FREE_MIB%") do set "FREE_MIB=%%A"
if "%FREE_MIB%"=="" set "FREE_MIB=0"

if %FREE_MIB% LSS %MIN_FREE_MIB% (
    powershell.exe -NoProfile -Command "Add-Content -Path '%STATE_LOG%' -Encoding UTF8 -Value ((Get-Date -Format o) + ' WAIT_300_NOEARLY_CMDSTART name=%NAME% reason=insufficient_free_gpu_mib free_mib=%FREE_MIB% required_mib=%MIN_FREE_MIB%')"
    exit /b 3
)

cd /d "%BASE%"
powershell.exe -NoProfile -Command "Add-Content -Path '%STATE_LOG%' -Encoding UTF8 -Value ((Get-Date -Format o) + ' CMDSTART_LAUNCH_300_NOEARLY model=%MODEL% name=%NAME% min_free_mib=%MIN_FREE_MIB% free_mib=%FREE_MIB% epochs=300 patience=0 imgsz=1280 batch=0.70')"
"%PYTHON%" "%TRAIN_SCRIPT%" --data "%DATA%" --model "%MODEL%" --project "%PROJECT%" --name "%NAME%" --epochs 300 --patience 0 --imgsz 1280 --batch 0.70 --device 0 --workers 2 > "%LOG%" 2> "%ERR%"
set "EXIT_CODE=%ERRORLEVEL%"
powershell.exe -NoProfile -Command "Add-Content -Path '%STATE_LOG%' -Encoding UTF8 -Value ((Get-Date -Format o) + ' CMDSTART_EXIT_300_NOEARLY model=%MODEL% name=%NAME% code=%EXIT_CODE%')"
exit /b %EXIT_CODE%
