FROM python:3.10-slim  

# 构建相关参数  
ARG INSTALL_WEB  
ARG AIFORGE_LOCALE  

WORKDIR /app  

# 设置环境变量  
ENV LANG=C.UTF-8  
ENV LC_ALL=C.UTF-8  
ENV PYTHONIOENCODING=utf-8  
ENV PYTHONPATH=/app/src  
ENV AIFORGE_DOCKER_MODE=true  

# 安装系统依赖  
RUN apt-get update && \  
    apt-get install -y --no-install-recommends \  
    curl \  
    && rm -rf /var/lib/apt/lists/* \  
    && apt-get clean  

# 复制依赖文件  
COPY pyproject.toml uv.lock ./  
COPY README_EN.md ./  

# 根据INSTALL_WEB参数决定是否安装web依赖  
RUN pip install uv && \  
    if [ "$INSTALL_WEB" = "true" ]; then \  
    env PYTHONIOENCODING=utf-8 uv sync --frozen --extra web; \  
    else \  
    env PYTHONIOENCODING=utf-8 uv sync --frozen; \  
    fi  

# 激活虚拟环境  
ENV PATH="/app/.venv/bin:$PATH"  

# 复制应用代码  
COPY src/ ./src/  

# 创建工作目录  
RUN mkdir -p /app/aiforge_work /app/logs  

# 健康检查脚本  
RUN if [ "$INSTALL_WEB" = "true" ]; then \  
    echo '#!/bin/bash\ncurl -f http://localhost:8000/health || exit 1' > /app/healthcheck.sh; \  
    else \  
    echo '#!/bin/bash\nps aux | grep -v grep | grep -q "sleep.*infinity" || exit 1' > /app/healthcheck.sh; \
    fi && \  
    chmod +x /app/healthcheck.sh  

# 健康检查  
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \  
    CMD /app/healthcheck.sh  

# 条件性端口暴露  
EXPOSE 8000  

# 启动命令  
ENTRYPOINT ["aiforge"]  
CMD ["--help"]