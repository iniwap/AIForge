#!/bin/bash  
  
export PYTHONWARNINGS="ignore::RuntimeWarning:runpy"  
export PYTHONPATH="src"  
export AIFORGE_LOCALE="${AIFORGE_LOCALE:-zh}"  
  
# 默认参数  
COMMAND="web"  
HOST="127.0.0.1"  
PORT="8000"  
RELOAD_FLAG="--reload"  
WEB_DEBUG_FLAG="--debug"  
API_KEY=""  
PROVIDER=""  
GUI_MODE="local"  
REMOTE_URL=""  
DEBUG_MODE=""  
AUTO_REMOTE=false  
  
# 显示帮助信息  
show_help() {  
    echo "AIForge 开发服务器启动脚本"  
    echo ""  
    echo "用法: $0 [web|gui|deploy] [选项]"  
    echo ""  
    echo "命令:"  
    echo "  web                启动 Web 服务器 (默认)"  
    echo "  gui                启动 GUI 应用"  
    echo "  deploy             部署管理"  
    echo ""  
    echo "GUI 选项:"  
    echo "  --local            本地模式 (默认)"  
    echo "  --remote URL       远程模式，连接到指定服务器"  
    echo "  --auto-remote      自动启动远程模式（先启动web服务）"  
    echo ""  
    echo "Web 选项:"  
    echo "  --host HOST        服务器地址 (默认: 127.0.0.1)"  
    echo "  --port PORT        服务器端口 (默认: 8000)"  
    echo ""  
    echo "部署选项:"  
    echo "  docker start       启动 Docker 部署"  
    echo "  k8s deploy         Kubernetes 部署"  
    echo "  cloud aws deploy   云部署"  
    echo ""  
    echo "通用选项:"  
    echo "  --api-key KEY      OpenRouter API 密钥 (可选)"  
    echo "  --provider PROVIDER LLM 提供商 (openrouter/deepseek/ollama)"  
    echo "  --debug            启用调试模式"  
    echo "  --help             显示此帮助信息"  
    exit 0  
}  
  
# 解析命令行参数  
while [[ $# -gt 0 ]]; do  
    case $1 in  
        gui)  
            COMMAND="gui"  
            shift  
            ;;  
        web)  
            COMMAND="web"  
            shift  
            ;;  
        deploy)  
            COMMAND="deploy"  
            shift  
            # 将剩余参数传递给部署模块  
            exec python -m aiforge_deploy.cli.deploy_cli "$@"  
            ;;  
        --local)  
            GUI_MODE="local"  
            shift  
            ;;  
        --remote)  
            GUI_MODE="remote"  
            REMOTE_URL="$2"  
            shift 2  
            ;;  
        --auto-remote)  
            GUI_MODE="remote"  
            AUTO_REMOTE=true  
            REMOTE_URL="http://127.0.0.1:8000"  
            shift  
            ;;  
        --api-key)  
            API_KEY="$2"  
            shift 2  
            ;;  
        --provider)  
            PROVIDER="$2"  
            shift 2  
            ;;  
        --debug)  
            DEBUG_MODE="--debug"  
            shift  
            ;;  
        --host)  
            HOST="$2"  
            shift 2  
            ;;  
        --port)  
            PORT="$2"  
            shift 2  
            ;;  
        --help)  
            show_help  
            ;;  
        *)  
            echo "未知选项: $1"  
            echo "使用 --help 查看帮助信息"  
            exit 1  
            ;;  
    esac  
done  
  
# 设置 API Key（如果提供）  
if [ -n "$API_KEY" ]; then  
    export OPENROUTER_API_KEY="$API_KEY"  
fi  
  
# 移除强制 API 密钥检查 - 允许无密钥启动  
# 用户可以在界面中配置 API 密钥  
  
# 构建provider参数  
PROVIDER_ARG=""  
if [ -n "$PROVIDER" ]; then  
    PROVIDER_ARG="--provider $PROVIDER"  
fi  
  
# 启动相应服务  
if [ "$COMMAND" = "gui" ]; then  
    if [ "$GUI_MODE" = "remote" ]; then  
        if [ "$AUTO_REMOTE" = true ]; then  
            echo "🚀 自动启动远程模式..."  
            echo "📡 启动 Web 服务器..."  
              
            # 后台启动 web 服务  
            python -m aiforge.cli.main web --host "$HOST" --port "$PORT" $RELOAD_FLAG $DEBUG_MODE $PROVIDER_ARG &  
            WEB_PID=$!  
              
            # 等待 web 服务启动  
            echo "⏳ 等待 Web 服务启动..."  
            sleep 5  
              
            # 检查 web 服务是否启动成功  
            if ! curl -s "http://$HOST:$PORT/api/health" > /dev/null 2>&1; then  
                echo "❌ Web 服务启动失败"  
                kill $WEB_PID 2>/dev/null  
                exit 1  
            fi  
              
            echo "✅ Web 服务启动成功"  
            echo "🖥️  启动 GUI 应用..."  
            # 启动 GUI 连接到 web 服务  
            python -m aiforge.cli.main gui --remote-url "$REMOTE_URL" $DEBUG_MODE $PROVIDER_ARG  
              
            # GUI 关闭后清理 web 服务  
            echo "🧹 清理后台服务..."  
            kill $WEB_PID 2>/dev/null  
        else  
            if [ -z "$REMOTE_URL" ]; then  
                echo "错误: 远程模式需要指定服务器地址"  
                echo "示例: $0 gui --remote http://localhost:8000"  
                echo "或使用: $0 gui --auto-remote"  
                exit 1  
            fi  
            python -m aiforge.cli.main gui --remote-url "$REMOTE_URL" $DEBUG_MODE $PROVIDER_ARG  
        fi  
    else  
        python -m aiforge.cli.main gui $DEBUG_MODE $PROVIDER_ARG  
    fi  
elif [ "$COMMAND" = "deploy" ]; then  
    # 部署命令已经在参数解析中处理，这里不应该到达  
    echo "错误: 部署命令处理异常"  
    exit 1  
else  
    # 启动 Web 服务器  
    echo "🚀 启动 AIForge Web 服务器"  
    if [ "$HOST" = "0.0.0.0" ]; then  
        echo "📡 本地访问: http://127.0.0.1:$PORT"  
        echo "🌐 网络访问: http://$HOST:$PORT"  
    else  
        echo "🏠 访问地址: http://$HOST:$PORT"  
    fi  
      
    # 如果没有 API 密钥，显示提示信息  
    if [ -z "$API_KEY" ] && [ -z "$OPENROUTER_API_KEY" ] && [ -z "$AIFORGE_API_KEY" ]; then  
        echo "⚠️  未检测到 API 密钥，请在 Web 界面中配置"  
    fi  
      
    python -m aiforge.cli.main web --host "$HOST" --port "$PORT" $RELOAD_FLAG $DEBUG_MODE $PROVIDER_ARG  
fi