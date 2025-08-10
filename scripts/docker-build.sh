#!/bin/bash  
set -e  
  
echo "构建 AIForge Docker 镜像..."  
  
# 构建镜像  
docker build -t aiforge:latest .  
docker build -t aiforge:$(git describe --tags --always) .  
  
echo "✅ Docker 镜像构建完成"  
echo "使用方式："  
echo "  docker-compose up -d    # 启动 Web API"  
echo "  docker run aiforge:latest cli --help  # CLI 模式"