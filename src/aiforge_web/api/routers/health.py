import time
from fastapi import APIRouter, Depends
from ..dependencies import get_session_aware_engine

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/")
async def health_check():
    """基础健康检查"""
    return {"status": "healthy", "timestamp": time.time(), "service": "aiforge-web-api"}


@router.get("/detailed")
async def detailed_health_check(forge=Depends(get_session_aware_engine)):
    """详细健康检查"""
    try:
        # 检查引擎状态
        engine_status = "healthy" if forge else "unhealthy"

        # 检查组件状态
        components_status = "healthy"
        if forge and hasattr(forge, "component_manager"):
            components = forge.component_manager.components
            components_status = "healthy" if components else "unhealthy"

        return {
            "status": (
                "healthy"
                if engine_status == "healthy" and components_status == "healthy"
                else "unhealthy"
            ),
            "timestamp": time.time(),
            "details": {
                "engine": engine_status,
                "components": components_status,
                "version": "1.0.0",
            },
        }
    except Exception as e:
        return {"status": "unhealthy", "timestamp": time.time(), "error": str(e)}
