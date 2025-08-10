#!/bin/bash  
set -e  
  
# 配置文件处理  
CONFIG_FILE="/app/config/aiforge.toml"  
if [ ! -f "$CONFIG_FILE" ] && [ -f "/app/docker/aiforge.toml.template" ]; then  
    mkdir -p /app/config  
    envsubst < /app/docker/aiforge.toml.template > "$CONFIG_FILE"  
fi  
  
# 根据启动模式执行不同命令  
case "$1" in  
    "web")  
        echo "启动 AIForge Web API 服务..."  
        exec python -m aiforge.web.main --host 0.0.0.0 --port 8000  
        ;;  
    "cli")  
        echo "启动 AIForge CLI 模式..."  
        exec aiforge "${@:2}"  
        ;;  
    "gui")  
        echo "启动 AIForge Terminal GUI..."  
        exec python -m aiforge.gui.main  
        ;;  
    *)  
        echo "执行自定义命令: $@"  
        exec "$@"  
        ;;  
esac