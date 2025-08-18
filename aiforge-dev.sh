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
GUI_MODE="local"  
REMOTE_URL=""  
DEBUG_MODE=""  
  
# 显示帮助信息  
show_help() {  
    echo "AIForge 开发服务器启动脚本"  
    echo ""  
    echo "用法: $0 [web|gui] [选项]"  
    echo ""  
    echo "命令:"  
    echo "  web                启动 Web 服务器 (默认)"  
    echo "  gui                启动 GUI 应用"  
    echo ""  
    echo "GUI 选项:"  
    echo "  --local            本地模式 (默认)"  
    echo "  --remote URL       远程模式，连接到指定服务器"  
    echo ""  
    echo "Web 选项:"  
    echo "  --host HOST        服务器地址 (默认: 127.0.0.1)"  
    echo "  --port PORT        服务器端口 (默认: 8000)"  
    echo ""  
    echo "通用选项:"  
    echo "  --api-key KEY      OpenRouter API 密钥"  
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
        --local)  
            GUI_MODE="local"  
            shift  
            ;;  
        --remote)  
            GUI_MODE="remote"  
            REMOTE_URL="$2"  
            shift 2  
            ;;  
        --api-key)  
            API_KEY="$2"  
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
  
# 设置 API Key  
if [ -n "$API_KEY" ]; then  
    export OPENROUTER_API_KEY="$API_KEY"  
fi  
  
if [ -z "$OPENROUTER_API_KEY" ]; then  
    echo "错误: 请设置 OPENROUTER_API_KEY 环境变量或使用 --api-key 参数"  
    exit 1  
fi  
  
# 启动相应服务  
if [ "$COMMAND" = "gui" ]; then  
    if [ "$GUI_MODE" = "remote" ]; then  
        if [ -z "$REMOTE_URL" ]; then  
            echo "错误: 远程模式需要指定服务器地址"  
            echo "示例: $0 gui --remote http://localhost:8000"  
            exit 1  
        fi  
        python -m aiforge.cli.main gui --remote-url "$REMOTE_URL" $DEBUG_MODE  
    else  
        python -m aiforge.cli.main gui $DEBUG_MODE  
    fi  
else  
    python -m aiforge.cli.main web --host "$HOST" --port "$PORT" $RELOAD_FLAG $DEBUG_MODE  
fi