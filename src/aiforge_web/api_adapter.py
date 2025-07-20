from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()


@router.post("/adapt-ui")
async def adapt_for_ui(result: Dict[str, Any], ui_type: str, aiforge_core):  # 依赖注入
    """为UI适配结果的API端点"""
    try:
        adapted_result = aiforge_core.adapt_result_for_ui(result, ui_type)
        return {
            "success": True,
            "adapted_result": adapted_result,
            "stats": aiforge_core.get_ui_adaptation_stats(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "fallback_result": result}
