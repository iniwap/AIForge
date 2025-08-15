@echo off  
chcp 65001  

setlocal enabledelayedexpansion  
  
REM 设置默认环境变量  
set "PYTHONWARNINGS=ignore::RuntimeWarning:runpy"  
set "PYTHONPATH=src"  
set "AIFORGE_LOCALE=zh"  
  
REM 解析命令行参数  
set "HOST=127.0.0.1"  
set "PORT=8000"  
set "RELOAD_FLAG=--reload"  
set "DEBUG_FLAG=--debug"  
set "API_KEY="  
  
:parse_args  
if "%~1"=="" goto :check_api_key  
if "%~1"=="--api-key" (  
    set "API_KEY=%~2"  
    shift  
    shift  
    goto :parse_args  
)  
if "%~1"=="--host" (  
    set "HOST=%~2"  
    shift  
    shift  
    goto :parse_args  
)  
REM ... 其他参数解析保持不变  
  
:check_api_key  
REM 如果通过参数提供了 API Key，则设置环境变量  
if not "%API_KEY%"=="" (  
    set "OPENROUTER_API_KEY=%API_KEY%"  
)  
  
REM 检查是否提供了 API Key  
if "%OPENROUTER_API_KEY%"=="" (  
    echo 错误: 请设置 OPENROUTER_API_KEY 环境变量或使用 --api-key 参数  
    echo 示例: aiforge-dev.bat --api-key sk-or-v1-your-key  
    exit /b 1  
)
  
python -m aiforge.cli.main web --host %HOST% --port %PORT% %RELOAD_FLAG% %DEBUG_FLAG%