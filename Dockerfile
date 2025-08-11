FROM python:3.11-slim

WORKDIR /app

# 设置环境变量以解决编码问题  
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONIOENCODING=utf-8

# 安装系统依赖  
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制依赖文件  
COPY pyproject.toml uv.lock ./
COPY README_EN.md ./ 

# 仅执行一次安装和同步步骤，并明确设置编码
RUN pip install uv && \
    env PYTHONIOENCODING=utf-8 uv sync --frozen


# 激活虚拟环境  
# ENV PATH="/app/.venv/bin:$PATH" 

# 复制应用代码  
COPY src/ ./src/
COPY scripts/ ./scripts/

# 创建工作目录  
RUN mkdir -p /app/aiforge_work /app/config /app/logs

# 设置环境变量  
ENV PYTHONPATH=/app/src
ENV AIFORGE_DOCKER_MODE=true

# 健康检查  
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口  
EXPOSE 8000

# 启动命令  
ENTRYPOINT ["python", "-m", "aiforge.cli"]
CMD ["web"]