import json
import hashlib
from typing import Dict, Any
from ...llm.llm_client import AIForgeLLMClient


class AIUIAdapter:
    """AI驱动的UI适配器"""

    def __init__(self, llm_client: AIForgeLLMClient):
        self.llm_client = llm_client
        self.cache = {}  # 简单的内存缓存

    def adapt_for_display(self, data: Dict[str, Any], ui_context: str) -> Dict[str, Any]:
        """根据UI上下文需求，让AI分析并转换数据格式"""
        # 生成缓存键
        cache_key = self._generate_cache_key(data, ui_context)

        # 检查缓存
        if cache_key in self.cache:
            return self.cache[cache_key]

        # AI分析
        prompt = self._build_adaptation_prompt(data, ui_context)

        try:
            response = self.llm_client.generate_code(prompt, "")
            adapted_result = self._parse_adaptation_result(response)

            # 缓存结果
            self.cache[cache_key] = adapted_result

            return adapted_result
        except Exception:
            # 失败时返回基础格式
            return self._create_fallback_format(data, ui_context)

    def _build_adaptation_prompt(self, data: Dict[str, Any], ui_context: str) -> str:
        """构建适配提示词"""
        return f"""
# 任务：数据格式适配
你需要将原始数据转换为适合特定界面展示的格式。

## 原始数据
{json.dumps(data, ensure_ascii=False, indent=2)}

## 目标界面类型
{ui_context}

## 输出要求
请返回以下JSON格式：
{{
    "display_items": [
        {{
            "type": "text|table|card|list|chart",
            "title": "显示标题",
            "content": "具体内容",
            "priority": 1-10
        }}
    ],
    "layout_hints": {{
        "layout_type": "vertical|horizontal|grid",
        "columns": 1-4,
        "spacing": "compact|normal|loose"
    }},
    "actions": [
        {{
            "label": "操作名称",
            "action": "refresh|export|detail",
            "data": {{}}
        }}
    ],
    "summary_text": "数据摘要文本"
}}

请严格按照JSON格式返回，不要包含其他解释文字。
"""

    def _parse_adaptation_result(self, response: str) -> Dict[str, Any]:
        """解析AI适配结果"""
        # 提取JSON内容
        import re

        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # 解析失败时返回默认结构
        return {
            "display_items": [
                {"type": "text", "title": "数据", "content": str(response)[:200], "priority": 5}
            ],
            "layout_hints": {"layout_type": "vertical", "columns": 1, "spacing": "normal"},
            "actions": [],
            "summary_text": "AI适配解析失败",
        }

    def _generate_cache_key(self, data: Dict[str, Any], ui_context: str) -> str:
        """生成缓存键"""
        content = f"{json.dumps(data, sort_keys=True)}_{ui_context}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _create_fallback_format(self, data: Dict[str, Any], ui_context: str) -> Dict[str, Any]:
        """创建回退格式"""
        return {
            "display_items": [
                {
                    "type": "text",
                    "title": "原始数据",
                    "content": json.dumps(data, ensure_ascii=False, indent=2),
                    "priority": 5,
                }
            ],
            "layout_hints": {"layout_type": "vertical", "columns": 1, "spacing": "normal"},
            "actions": [{"label": "刷新", "action": "refresh", "data": {}}],
            "summary_text": f"显示原始数据 ({ui_context})",
        }
