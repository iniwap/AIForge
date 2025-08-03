from typing import Dict, Any, List
from difflib import SequenceMatcher


class TaskClassifier:
    """任务分类器 - 负责任务类型分类和验证"""

    def __init__(self):
        # 完整保留原有的standardized_patterns
        self.standardized_patterns = {
            "data_fetch": {
                "keywords": [
                    "搜索",
                    "search",
                    "获取",
                    "fetch",
                    "查找",
                    "新闻",
                    "news",
                    "api",
                    "接口",
                    "爬取",
                    "crawl",
                    "信息",
                    "资讯",
                    "内容",
                ],
                "actions": ["search", "fetch", "get", "crawl"],
                "common_params": ["query", "topic", "time_range", "date"],
            },
            "data_process": {
                "keywords": [
                    "分析",
                    "analyze",
                    "处理",
                    "process",
                    "计算",
                    "统计",
                    "转换",
                    "transform",
                ],
                "actions": ["analyze", "process", "calculate", "transform"],
                "common_params": ["data_source", "method", "format"],
            },
            "file_operation": {
                "keywords": [
                    "文件",
                    "file",
                    "读取",
                    "read",
                    "写入",
                    "write",
                    "保存",
                    "save",
                    "批量",
                    "batch",
                    "复制",
                    "copy",
                    "移动",
                    "move",
                    "删除",
                    "delete",
                    "重命名",
                    "rename",
                    "压缩",
                    "compress",
                    "解压",
                    "extract",
                    "创建",
                    "create",
                    "目录",
                    "directory",
                    "文件夹",
                    "folder",
                ],
                "actions": [
                    "read",
                    "write",
                    "save",
                    "copy",
                    "move",
                    "delete",
                    "rename",
                    "compress",
                    "extract",
                    "create",
                    "process",
                ],
                "common_params": [
                    "file_path",
                    "source_path",
                    "target_path",
                    "format",
                    "encoding",
                    "recursive",
                    "force",
                    "operation",
                ],
                "exclude_keywords": [
                    "分析",
                    "analyze",
                    "统计",
                    "statistics",
                    "计算",
                    "calculate",
                    "处理数据",
                    "process data",
                    "清洗",
                    "clean",
                ],
            },
            "automation": {
                "keywords": [
                    "自动化",
                    "automation",
                    "定时",
                    "schedule",
                    "监控",
                    "monitor",
                    "任务",
                    "task",
                ],
                "actions": ["automate", "schedule", "monitor", "execute"],
                "common_params": ["interval", "condition", "action"],
            },
            "content_generation": {
                "keywords": [
                    "生成",
                    "generate",
                    "创建",
                    "create",
                    "写作",
                    "writing",
                    "报告",
                    "report",
                ],
                "actions": ["generate", "create", "write", "compose"],
                "common_params": ["template", "content", "style"],
            },
            "direct_response": {
                "keywords": [
                    # 问答类
                    "什么是",
                    "如何",
                    "为什么",
                    "解释",
                    "介绍",
                    "定义",
                    "概念",
                    "原理",
                    "区别",
                    "比较",
                    "what",
                    "how",
                    "why",
                    "explain",
                    "describe",
                    "define",
                    "concept",
                    # 创作类
                    "写一篇",
                    "写一个",
                    "创作",
                    "编写",
                    "起草",
                    "写作",
                    "撰写",
                    "write",
                    "compose",
                    "draft",
                    "create content",
                    # 翻译类
                    "翻译",
                    "translate",
                    "转换为",
                    "改写为",
                    "用...语言",
                    # 总结分析类（纯文本）
                    "总结",
                    "概括",
                    "归纳",
                    "分析这段",
                    "解读",
                    "summarize",
                    "analyze this text",
                    "interpret",
                    # 建议咨询类
                    "建议",
                    "推荐",
                    "意见",
                    "看法",
                    "评价",
                    "怎么看",
                    "suggest",
                    "recommend",
                    "opinion",
                    "advice",
                ],
                "exclude_keywords": [
                    # 时效性关键词
                    "今天",
                    "现在",
                    "最新",
                    "当前",
                    "实时",
                    "目前",
                    "天气",
                    "股价",
                    "新闻",
                    "汇率",
                    "价格",
                    "状态",
                ],
                "actions": ["respond", "answer", "create", "translate", "summarize", "suggest"],
                "common_params": ["content", "style"],
            },
        }

    def is_ai_analysis_valid(self, ai_analysis: Dict[str, Any]) -> bool:
        """验证AI分析结果的有效性 - 保持原有逻辑"""
        # 1. 检查必要字段
        required_fields = ["task_type", "action", "target"]
        if not all(field in ai_analysis for field in required_fields):
            return False

        # 2. 检查task_type是否有效
        task_type = ai_analysis.get("task_type")
        if not task_type or not isinstance(task_type, str) or not task_type.strip():
            return False

        # 3. 新增：检查是否使用了推荐的内置类型
        builtin_types = list(self.standardized_patterns.keys())
        is_builtin = task_type in builtin_types

        # 4. 如果不是内置类型，进行额外验证
        if not is_builtin:
            # 检查是否与现有类型过于相似
            if self._is_too_similar_to_existing_types(task_type, builtin_types):
                return False

        # 5. 注册新的任务类型和动作（如果有管理器）
        if hasattr(self, "task_type_manager") and self.task_type_manager:
            task_type = ai_analysis.get("task_type")
            action = ai_analysis.get("action", "")

            # 注册任务类型
            self.task_type_manager.register_task_type(task_type, ai_analysis)

            # 注册动态动作（新增）
            if action and task_type:
                self.task_type_manager.register_dynamic_action(action, task_type, ai_analysis)

            # 记录类型使用统计
            builtin_types = list(self.standardized_patterns.keys())
            is_builtin = task_type in builtin_types

        return True

    def _is_too_similar_to_existing_types(self, task_type: str, builtin_types: List[str]) -> bool:
        """检查是否与现有类型过于相似 - 保持原有逻辑"""
        try:
            for existing_type in builtin_types:
                similarity = SequenceMatcher(None, task_type.lower(), existing_type.lower()).ratio()
                if similarity > 0.8:  # 相似度阈值
                    return True
            return False
        except Exception:
            return False
