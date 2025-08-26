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
set "PROVIDER="  
set "REMOTE_URL="  
set "GUI_MODE=local"  
set "DEBUG_MODE="  
set "AUTO_REMOTE=false"  
  
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
if "%~1"=="deploy" (  
    set "COMMAND=deploy"  
    shift  
    REM 将剩余参数传递给部署模块  
    python -m aiforge_deploy.cli.deploy_cli %2 %3 %4 %5 %6 %7 %8 %9  
    exit /b %ERRORLEVEL%  
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
if "%~1"=="--auto-remote" (  
    set "GUI_MODE=remote"  
    set "AUTO_REMOTE=true"  
    set "REMOTE_URL=http://127.0.0.1:8000"  
    shift  
    goto :parse_args  
)  
if "%~1"=="--api-key" (  
    set "API_KEY=%~2"  
    shift  
    shift  
    goto :parse_args  
)  
if "%~1"=="--provider" (  
    set "PROVIDER=%~2"  
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
    echo 用法: %0 [web^|gui^|deploy] [选项]  
    echo.  
    echo 命令:  
    echo   web                启动 Web 服务器 (默认)  
    echo   gui                启动 GUI 应用  
    echo   deploy             部署管理  
    echo.  
    echo GUI 选项:  
    echo   --local            本地模式 (默认)  
    echo   --remote URL       远程模式，连接到指定服务器  
    echo   --auto-remote      自动启动远程模式（先启动web服务）  
    echo.  
    echo Web 选项:  
    echo   --host HOST        服务器地址 (默认: 127.0.0.1)  
    echo   --port PORT        服务器端口 (默认: 8000)  
    echo.  
    echo 部署选项:  
    echo   docker start       启动 Docker 部署  
    echo   k8s deploy         Kubernetes 部署  
    echo   cloud aws deploy   云部署  
    echo.  
    echo 通用选项:  
    echo   --api-key KEY      OpenRouter API 密钥 (可选)  
    echo   --provider PROVIDER LLM 提供商 (openrouter/deepseek/ollama)  
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
  
REM 移除强制 API 密钥检查 - 允许无密钥启动  
REM 用户可以在界面中配置 API 密钥  
  
REM 构建provider参数  
set "PROVIDER_ARG="  
if not "%PROVIDER%"=="" (  
    set "PROVIDER_ARG=--provider %PROVIDER%"  
)  
  
if "%COMMAND%"=="gui" (  
    if "%GUI_MODE%"=="remote" (  
        if "%AUTO_REMOTE%"=="true" (  
            echo 🚀 自动启动远程模式...  
            echo 📡 启动 Web 服务器...  
              
            REM 后台启动 web 服务  
            start /B python -m aiforge.cli.main web --host %HOST% --port %PORT% %RELOAD_FLAG% %DEBUG_MODE% %PROVIDER_ARG%  
              
            REM 等待 web 服务启动  
            echo ⏳ 等待 Web 服务启动...  
            timeout /t 5 /nobreak >nul  
              
            REM 检查 web 服务是否启动成功  
            curl -s "http://%HOST%:%PORT%/api/health" >nul 2>&1  
            if errorlevel 1 (  
                echo ❌ Web 服务启动失败  
                taskkill /f /im python.exe >nul 2>&1  
                exit /b 1  
            )  
              
            echo ✅ Web 服务启动成功  
            echo 🖥️  启动 GUI 应用...  
              
            REM 启动 GUI 连接到 web 服务  
            python -m aiforge.cli.main gui --remote-url %REMOTE_URL% %DEBUG_MODE% %PROVIDER_ARG%  
              
            REM GUI 关闭后清理 web 服务  
            echo 🧹 清理后台服务...  
            taskkill /f /im python.exe >nul 2>&1  
        ) else (  
            if "%REMOTE_URL%"=="" (  
                echo 错误: 远程模式需要指定服务器地址  
                echo 示例: %0 gui --remote http://localhost:8000  
                echo 或使用: %0 gui --auto-remote  
                exit /b 1  
            )  
            python -m aiforge.cli.main gui --remote-url %REMOTE_URL% %DEBUG_MODE% %PROVIDER_ARG%  
        )  
    ) else (  
        python -m aiforge.cli.main gui %DEBUG_MODE% %PROVIDER_ARG%  
    )  
) else (  
    REM 启动 Web 服务器  
    echo 🚀 启动 AIForge Web 服务器  
    if "%HOST%"=="0.0.0.0" (  
        echo 📡 本地访问: http://127.0.0.1:%PORT%  
        echo 🌐 网络访问: http://%HOST%:%PORT%  
    ) else (  
        echo 🏠 访问地址: http://%HOST%:%PORT%  
    )  
      
    REM 如果没有 API 密钥，显示提示信息  
    if "%API_KEY%"=="" (  
        if "%OPENROUTER_API_KEY%"=="" (  
            if "%AIFORGE_API_KEY%"=="" (  
                echo ⚠️  未检测到 API 密钥，请在 Web 界面中配置  
            )  
        )  
    )  
      
    if "%RELOAD_FLAG%"=="--reload" (  
        echo 🔄 热重载模式已启用  
    )  
    if "%DEBUG_MODE%"=="--debug" (  
        echo 🐛 调试模式已启用  
    )  
      
    python -m aiforge.cli.main web --host %HOST% --port %PORT% %RELOAD_FLAG% %DEBUG_MODE% %PROVIDER_ARG%  
)