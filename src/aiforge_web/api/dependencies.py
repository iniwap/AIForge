from fastapi import HTTPException
from aiforge import AIForgeEngine
from typing import Optional

# 全局引擎实例
_forge_instance: Optional[AIForgeEngine] = None


def set_forge_instance(forge: AIForgeEngine):
    """设置全局引擎实例"""
    global _forge_instance
    _forge_instance = forge


def get_forge_engine() -> AIForgeEngine:
    """获取 AIForge 引擎实例"""
    if _forge_instance is None:
        raise HTTPException(status_code=503, detail="AIForge 引擎未初始化，请检查配置")
    return _forge_instance


def get_forge_components():
    """获取 AIForge 组件"""
    forge = get_forge_engine()
    return forge.component_manager.components
