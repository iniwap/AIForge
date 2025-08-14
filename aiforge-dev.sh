#!/bin/bash  
  
# 设置默认环境变量  
export PYTHONWARNINGS="ignore::RuntimeWarning:runpy"  
export PYTHONPATH="src"  
export AIFORGE_LOCALE="${AIFORGE_LOCALE:-zh}"  
  
# 默认参数  
HOST="127.0.0.1"  
PORT="8000"  
RELOAD_FLAG="--reload"  
DEBUG_FLAG="--debug"  
API_KEY=""  
  
# 显示帮助信息  
show_help() {  
    echo "AIForge 开发服务器启动脚本"  
    echo ""  
    echo "用法: $0 [选项]"  
    echo ""  
    echo "选项:"  
    echo "  --api-key KEY      OpenRouter API 密钥"  
    echo "  --host HOST        服务器地址 (默认: 127.0.0.1)"  
    echo "  --port PORT        服务器端口 (默认: 8000)"  
    echo "  --no-reload        禁用热重载"  
    echo "  --no-debug         禁用调试模式"  
    echo "  --help             显示此帮助信息"  
    echo ""  
    echo "环境变量:"  
    echo "  OPENROUTER_API_KEY  OpenRouter API 密钥 (必需)"  
    echo "  AIFORGE_LOCALE      界面语言 (默认: zh)"  
    exit 0  
}  
  
# 解析命令行参数  
while [[ $# -gt 0 ]]; do  
    case $1 in  
        --api-key)  
            API_KEY="$2"  
            shift 2  
            ;;  
        --host)  
            HOST="$2"  
            shift 2  
            ;;  
        --port)  
            PORT="$2"  
            shift 2  
            ;;  
        --no-reload)  
            RELOAD_FLAG=""  
            shift  
            ;;  
        --no-debug)  
            DEBUG_FLAG=""  
            shift  
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
  
# 如果通过参数提供了 API Key，则设置环境变量  
if [ -n "$API_KEY" ]; then  
    export OPENROUTER_API_KEY="$API_KEY"  
fi  
  
# 检查 API Key  
if [ -z "$OPENROUTER_API_KEY" ]; then  
    echo "错误: 请设置 OPENROUTER_API_KEY 环境变量或使用 --api-key 参数"  
    echo "示例: ./aiforge-dev.sh --api-key sk-or-v1-your-key"  
    exit 1  
fi  
  
# 启动服务器  
echo "启动 AIForge Web 服务器..."  
echo "地址: http://$HOST:$PORT"  
echo "语言: $AIFORGE_LOCALE"  
echo ""  
  
python -m aiforge.cli.main web --host "$HOST" --port "$PORT" $RELOAD_FLAG $DEBUG_FLAG