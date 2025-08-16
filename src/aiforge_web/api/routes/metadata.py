from fastapi import APIRouter
from typing import Optional

router = APIRouter(prefix="/api/v1/metadata", tags=["metadata"])


@router.get("/task-types")
async def get_task_types():
    """获取支持的任务类型"""
    builtin_types = [
        {
            "id": "data_fetch",
            "name": "数据获取",
            "icon": "📊",
            "description": "从各种数据源获取信息",
        },
        {"id": "data_analysis", "name": "数据分析", "icon": "📈", "description": "分析和处理数据"},
        {
            "id": "content_generation",
            "name": "内容生成",
            "icon": "✍️",
            "description": "生成文本、文档等内容",
        },
        {
            "id": "code_generation",
            "name": "代码生成",
            "icon": "💻",
            "description": "生成和优化代码",
        },
        {"id": "search", "name": "搜索查询", "icon": "🔍", "description": "搜索和检索信息"},
        {"id": "direct_response", "name": "知识问答", "icon": "💬", "description": "直接回答问题"},
    ]
    future_types = [
        {
            "id": "file_operation",
            "name": "文件操作",
            "icon": "📁",
            "description": "文件管理和处理",
            "disabled": True,
            "reason": "需要客户端支持",
        },
        {
            "id": "automation",
            "name": "自动化任务",
            "icon": "🤖",
            "description": "自动化工作流程",
            "disabled": True,
            "reason": "需要系统权限",
        },
        {
            "id": "image_processing",
            "name": "图像处理",
            "icon": "🖼️",
            "description": "图像分析和处理",
            "disabled": True,
            "reason": "需要图像处理库支持",
        },
        {
            "id": "api_integration",
            "name": "API集成",
            "icon": "🔗",
            "description": "第三方API集成",
            "disabled": True,
            "reason": "需要外部服务配置",
        },
    ]

    return {
        "builtin_types": builtin_types,
        "future_types": future_types,
        "total_supported": len(builtin_types),
    }


@router.get("/ui-types")
async def get_ui_types():
    """获取支持的 UI 类型 - 返回语义化的基础类型"""
    ui_types = [
        {"id": "card", "name": "卡片视图", "description": "简洁的卡片展示"},
        {"id": "table", "name": "表格视图", "description": "结构化数据表格"},
        {"id": "dashboard", "name": "仪表板", "description": "数据分析仪表板"},
        {"id": "timeline", "name": "时间线", "description": "步骤和流程展示"},
        {"id": "progress", "name": "进度条", "description": "任务进度显示"},
        {"id": "editor", "name": "编辑器", "description": "内容编辑和展示"},
        {"id": "map", "name": "地图视图", "description": "地理位置数据展示"},
        {"id": "chart", "name": "图表视图", "description": "数据可视化图表"},
        {"id": "gallery", "name": "图片库", "description": "图片集合展示"},
        {"id": "calendar", "name": "日历视图", "description": "时间事件展示"},
        {"id": "list", "name": "列表视图", "description": "项目列表展示"},
        {"id": "text", "name": "文本输出", "description": "纯文本内容展示"},
    ]

    return {"ui_types": ui_types}


@router.get("/ui-recommendations")
async def get_ui_recommendations(
    task_type: str, data_structure: Optional[str] = None, context: str = "web"
):
    """获取 UI 类型推荐"""
    # 这里可以集成 UITypeRecommender 的逻辑
    # 返回基础类型推荐，由前端或Web应用层添加前缀
    recommendations = [
        {"ui_type": "card", "score": 8.5, "reason": "适合简单数据展示"},
        {"ui_type": "table", "score": 7.0, "reason": "适合结构化数据"},
    ]

    return {"recommendations": recommendations}
