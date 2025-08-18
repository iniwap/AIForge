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
set "WEB_DEBUG_FLAG=--debug"  
set "API_KEY="  
set "REMOTE_URL="  
set "GUI_MODE=local"  
set "DEBUG_MODE="  
  
:parse_args  
if "%~1"=="" goto :check_command  
if "%~1"=="gui" (  
    set "COMMAND=gui"  
    shift  
    goto :parse_args  
)  
if "%~1"=="web" (  
    set "COMMAND=web"  
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
if "%~1"=="--debug" (  
    set "DEBUG_MODE=--debug"  
    shift  
    goto :parse_args  
)  
if "%~1"=="--host" (  
    set "HOST=%~2"  
    shift  
    shift  
    goto :parse_args  
)  
if "%~1"=="--port" (  
    set "PORT=%~2"  
    shift  
    shift  
    goto :parse_args  
)  
if "%~1"=="--help" (  
    echo AIForge 开发服务器启动脚本  
    echo.  
    echo 用法: %0 [web^|gui] [选项]  
    echo.  
    echo 命令:  
    echo   web                启动 Web 服务器 (默认)  
    echo   gui                启动 GUI 应用  
    echo.  
    echo GUI 选项:  
    echo   --local            本地模式 (默认)  
    echo   --remote URL       远程模式，连接到指定服务器  
    echo.  
    echo Web 选项:  
    echo   --host HOST        服务器地址 (默认: 127.0.0.1)  
    echo   --port PORT        服务器端口 (默认: 8000)  
    echo.  
    echo 通用选项:  
    echo   --api-key KEY      OpenRouter API 密钥  
    echo   --debug            启用调试模式  
    echo   --help             显示此帮助信息  
    exit /b 0  
)  
REM 跳过未知参数  
shift  
goto :parse_args  
  
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
        if "%REMOTE_URL%"=="" (  
            echo 错误: 远程模式需要指定服务器地址  
            echo 示例: %0 gui --remote http://localhost:8000  
            exit /b 1  
        )  
        python -m aiforge.cli.main gui --remote-url %REMOTE_URL% %DEBUG_MODE%  
    ) else (  
        python -m aiforge.cli.main gui %DEBUG_MODE%  
    )  
) else (  
    python -m aiforge.cli.main web --host %HOST% --port %PORT% %RELOAD_FLAG% %DEBUG_MODE%  
)