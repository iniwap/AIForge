FROM python:3.10-slim

# 从.env读取设置docker环境变量
ARG AIFORGE_LOCALE 
ARG OPENROUTER_API_KEY  
ARG DEEPSEEK_API_KEY 
ARG SEARXNG_ENABLED 
ARG SEARXNG_LOCAL_URL 
ARG SEARXNG_REMOTE_URL 
ARG SEARXNG_FALLBACK_TO_PUBLIC 

WORKDIR /app

# 设置环境变量以解决编码问题  
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONIOENCODING=utf-8

# 安装系统依赖    
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    gettext-base \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制依赖文件  
COPY pyproject.toml uv.lock ./
COPY README_EN.md ./ 

# 仅执行一次安装和同步步骤，并明确设置编码
RUN pip install uv && \
    env PYTHONIOENCODING=utf-8 uv sync --frozen --extra web


# 激活虚拟环境  
ENV PATH="/app/.venv/bin:$PATH" 

# 复制应用代码  
COPY src/ ./src/

# 创建工作目录  
RUN mkdir -p /app/aiforge_work /app/config /app/logs

# 复制模板文件并生成默认配置 
COPY docker/aiforge.toml.template /app/docker/aiforge.toml.template   
ENV AIFORGE_LOCALE=${AIFORGE_LOCALE:-en} 
ENV OPENROUTER_API_KEY=${OPENROUTER_API_KEY}     
ENV DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}    
ENV SEARXNG_ENABLED=${SEARXNG_ENABLED:-false}    
ENV SEARXNG_LOCAL_URL=${SEARXNG_LOCAL_URL}    
ENV SEARXNG_REMOTE_URL=${SEARXNG_REMOTE_URL}    
ENV SEARXNG_FALLBACK_TO_PUBLIC=${SEARXNG_FALLBACK_TO_PUBLIC:-true}  
RUN envsubst < /app/docker/aiforge.toml.template > /app/config/aiforge.toml

# 设置环境变量  
ENV PYTHONPATH=/app/src
ENV AIFORGE_DOCKER_MODE=true

# 健康检查  
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口  
EXPOSE 8000

# 启动命令  
ENTRYPOINT ["aiforge"]  
CMD ["web"]