import os


def get_default_engine_config():
    """获取默认引擎配置"""
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("AIFORGE_API_KEY")
    provider = os.environ.get("AIFORGE_PROVIDER", "openrouter")

    return {"api_key": api_key, "provider": provider}
