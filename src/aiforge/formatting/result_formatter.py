import json
import time
from typing import Dict, Any, List
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.rule import Rule
from rich.console import Group
from rich.table import Table


class AIForgeResultFormatter:
    """AIForge结果格式化器"""

    def __init__(self, console: Console):
        self.console = console

    def format_execution_result(
        self,
        code_block: str,
        result: Dict[str, Any],
        block_name: str | None = None,
        lang: str = "python",
    ) -> None:
        """格式化并显示代码执行结果"""

        # 检查是否有错误信息来决定是否显示行号
        line_numbers = "traceback" in result or "error" in result

        # 格式化代码块
        syntax_code = Syntax(code_block, lang, line_numbers=line_numbers, word_wrap=True)

        # 创建结果副本并移除冗余的code字段
        result_copy = result.copy()
        if "code" in result_copy:
            result_copy["code"] = "见上方代码块..."
            # 或者完全移除code字段
            # del result_copy["code"]

        # 格式化结果为JSON
        json_result = json.dumps(result_copy, ensure_ascii=False, indent=2, default=str)
        syntax_result = Syntax(json_result, "json", line_numbers=False, word_wrap=True)

        # 组合显示
        group = Group(syntax_code, Rule(), syntax_result)
        panel = Panel(group, title=block_name or "代码执行结果")
        self.console.print(panel)

    def format_structured_feedback(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成结构化的反馈消息"""
        return {
            "message": "以下是运行环境按执行顺序自动返回的代码块执行结果",
            "source": "Runtime Environment",
            "results": results,
        }

    def format_execution_summary(
        self, total_rounds: int, max_rounds: int, history_count: int, success: bool
    ) -> None:
        """格式化执行总结"""
        table = Table(title="执行总结", show_header=True, header_style="bold magenta")
        table.add_column("项目", style="cyan", no_wrap=True)
        table.add_column("值", style="green")

        table.add_row("总轮数", f"{total_rounds}/{max_rounds}")
        table.add_row("历史记录", f"{history_count} 条")
        table.add_row("任务状态", "完成" if success else "未完成")

        self.console.print(table)

    def format_task_type_result(self, result: Dict[str, Any], task_type: str) -> Dict[str, Any]:
        """补充元数据"""

        # 确保基本字段存在
        result.setdefault("status", "success")
        result.setdefault("summary", "操作完成")
        result.setdefault("metadata", {})
        result["metadata"].setdefault("task_type", task_type)
        result["metadata"].setdefault("timestamp", time.time())

        return result
