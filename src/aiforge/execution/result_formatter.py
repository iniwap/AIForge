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

    def __init__(self, console: Console, components: Dict[str, Any] = None):
        self.console = console
        self._i18n_manager = components.get("i18n_manager")

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
            code_placeholder = self._i18n_manager.t("formatter.code_placeholder")
            result_copy["code"] = code_placeholder

        # 格式化结果为JSON
        json_result = json.dumps(result_copy, ensure_ascii=False, indent=2, default=str)
        syntax_result = Syntax(json_result, "json", line_numbers=False, word_wrap=True)

        # 组合显示
        group = Group(syntax_code, Rule(), syntax_result)
        default_title = self._i18n_manager.t("formatter.execution_result_title")
        panel = Panel(group, title=block_name or default_title)
        self.console.print(panel)

    def format_structured_feedback(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成结构化的反馈消息"""
        feedback_message = self._i18n_manager.t("formatter.structured_feedback_message")
        return {
            "message": feedback_message,
            "source": "Runtime Environment",
            "results": results,
        }

    def format_execution_summary(
        self, total_rounds: int, max_rounds: int, history_count: int, success: bool
    ) -> None:
        """格式化执行总结"""
        summary_title = self._i18n_manager.t("formatter.execution_summary_title")
        table = Table(title=summary_title, show_header=True, header_style="bold magenta")

        item_column = self._i18n_manager.t("formatter.item_column")
        value_column = self._i18n_manager.t("formatter.value_column")
        table.add_column(item_column, style="cyan", no_wrap=True)
        table.add_column(value_column, style="green")

        total_rounds_label = self._i18n_manager.t("formatter.total_rounds_label")
        history_label = self._i18n_manager.t("formatter.history_label")
        task_status_label = self._i18n_manager.t("formatter.task_status_label")
        history_count_text = self._i18n_manager.t(
            "formatter.history_count_text", count=history_count
        )

        completed_text = self._i18n_manager.t("formatter.completed_text")
        incomplete_text = self._i18n_manager.t("formatter.incomplete_text")
        status_text = completed_text if success else incomplete_text

        table.add_row(total_rounds_label, f"{total_rounds}/{max_rounds}")
        table.add_row(history_label, history_count_text)
        table.add_row(task_status_label, status_text)

        self.console.print(table)

    def format_task_type_result(self, result: Dict[str, Any], task_type: str) -> Dict[str, Any]:
        """补充元数据"""

        default_summary = self._i18n_manager.t("formatter.operation_completed")

        # 确保基本字段存在
        result.setdefault("status", "success")
        result.setdefault("summary", default_summary)
        result.setdefault("metadata", {})
        result["metadata"].setdefault("task_type", task_type)
        result["metadata"].setdefault("timestamp", time.time())

        return result
