FROM python:3.10-slim  

WORKDIR /app  

# 系统依赖安装（很少变化，可以充分利用缓存）  
RUN apt-get update && apt-get install -y \  
    curl \  
    git \  
    build-essential \  
    && rm -rf /var/lib/apt/lists/*  

# 先复制依赖配置文件（只有依赖变化时才重新构建这一层）  
COPY pyproject.toml ./  
COPY setup.py ./  

# 安装依赖（这一层只有在依赖文件变化时才重新构建）  
RUN pip install --no-cache-dir -e .[all]  

# 最后复制源代码（代码变更不会影响上面的依赖层）  
COPY . .  

# 其他配置  
RUN mkdir -p /app/aiforge_work  
COPY docker/entrypoint.sh /entrypoint.sh  
RUN chmod +x /entrypoint.sh  

EXPOSE 8000  

ENTRYPOINT ["/entrypoint.sh"]  
CMD ["web"]