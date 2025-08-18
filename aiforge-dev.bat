@echo off  
chcp 65001 >nul
  
setlocal enabledelayedexpansion  
  
REM 设置默认环境变量  
set "PYTHONWARNINGS=ignore::RuntimeWarning:runpy"  
set "PYTHONPATH=src"  
set "AIFORGE_LOCALE=zh"  
  
REM 解析命令行参数  
set "COMMAND=web"  
set "HOST=127.0.0.1"  
set "PORT=8000"  
set "RELOAD_FLAG=--reload"  
set "DEBUG_FLAG=--debug"  
set "API_KEY="  
set "REMOTE_URL="  
  
:parse_args  
if "%~1"=="" goto :check_command  
if "%~1"=="gui" (  
    set "COMMAND=gui"  
    shift  
    goto :parse_args  
)  
if "%~1"=="--local" (  
    set "GUI_MODE=local"  
    shift  
    goto :parse_args  
)  
if "%~1"=="--remote" (  
    set "GUI_MODE=remote"  
    set "REMOTE_URL=%~2"  
    shift  
    shift  
    goto :parse_args  
)  
if "%~1"=="--api-key" (  
    set "API_KEY=%~2"  
    shift  
    shift  
    goto :parse_args  
)  
REM ... 其他参数解析  
  
:check_command  
if not "%API_KEY%"=="" (  
    set "OPENROUTER_API_KEY=%API_KEY%"  
)  
  
if "%OPENROUTER_API_KEY%"=="" (  
    echo 错误: 请设置 OPENROUTER_API_KEY 环境变量或使用 --api-key 参数  
    exit /b 1  
)  
  
if "%COMMAND%"=="gui" (  
    if "%GUI_MODE%"=="remote" (  
        python -m aiforge_gui.main --remote-url %REMOTE_URL%  
    ) else (  
        python -m aiforge_gui.main --local  
    )  
) else (  
    python -m aiforge.cli.main web --host %HOST% --port %PORT% %RELOAD_FLAG% %DEBUG_FLAG%  
)