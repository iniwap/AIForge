import os
import time
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

router = APIRouter(prefix="/api/v1/config", tags=["config"])


@router.get("/status")
async def get_config_status():
    """获取配置状态"""
    # 检测配置类型
    if os.environ.get("AIFORGE_DOCKER_MODE") == "true":
        config_type = "docker"
        configured = os.path.exists("/app/config/aiforge.toml")
    elif os.environ.get("OPENROUTER_API_KEY"):
        config_type = "openrouter_env"
        configured = True
    elif os.environ.get("DEEPSEEK_API_KEY"):
        config_type = "deepseek_env"
        configured = True
    elif os.path.exists("aiforge.toml"):
        config_type = "config_file"
        configured = True
    else:
        config_type = "unknown"
        configured = False

    return {
        "configured": configured,
        "config_type": config_type,
        "timestamp": time.time(),
    }


@router.post("/update")
async def update_config(config_data: Dict[str, Any]):
    """更新配置"""
    try:
        # 这里可以实现配置更新逻辑
        # 例如：验证API密钥、更新配置文件等

        if "api_key" in config_data and "provider" in config_data:
            # 验证API密钥
            # api_key = config_data["api_key"]
            provider = config_data["provider"]

            # 这里可以添加实际的验证逻辑

            return {
                "success": True,
                "message": "配置更新成功",
                "config_type": f"{provider}_api_key",
            }

        return {"success": False, "message": "无效的配置数据"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"配置更新失败: {str(e)}")


@router.get("/providers")
async def get_available_providers():
    """获取可用的 LLM 提供商"""
    return {
        "providers": [
            {
                "id": "openrouter",
                "name": "OpenRouter",
                "description": "多模型访问平台",
                "supported_models": ["gpt-4", "claude-3", "llama-2"],
                "api_key_format": "sk-or-*",
                "website": "https://openrouter.ai",
            },
            {
                "id": "deepseek",
                "name": "DeepSeek",
                "description": "经济高效的AI提供商",
                "supported_models": ["deepseek-chat", "deepseek-coder"],
                "api_key_format": "sk-*",
                "website": "https://platform.deepseek.com",
            },
            {
                "id": "ollama",
                "name": "Ollama",
                "description": "本地模型执行",
                "supported_models": ["llama2", "codellama", "mistral"],
                "api_key_format": "不需要API密钥",
                "website": "https://ollama.ai",
            },
        ]
    }
