import time
from typing import Dict, Any
from rich.console import Console

from ...llm.llm_client import AIForgeLLMClient
from ..prompt import AIForgePrompt
from .executor import TaskExecutor


class AIForgeTask:
    """AIForge 任务实例"""

    def __init__(
        self,
        task_id: str,
        llm_client: AIForgeLLMClient,
        max_rounds,
        optimization,
        max_optimization_attempts,
        task_manager,
        components: Dict[str, Any] = None,  # 新增 components 参数
    ):
        self.task_id = task_id
        self.task_manager = task_manager
        self.components = components or {}  # 保存 components 引用
        self.console = Console()

        # 使用拆分后的执行器，传递 components 参数
        self.executor = TaskExecutor(
            llm_client, max_rounds, optimization, max_optimization_attempts, components
        )

        self.instruction = None
        self.system_prompt = None
        self.max_rounds = max_rounds
        self.task_type = None

    def run(
        self,
        instruction: str | None = None,
        system_prompt: str | None = None,
        task_type: str | None = None,
        expected_output: Dict[str, Any] = None,
    ):
        """执行方法"""
        if instruction and system_prompt:
            self.instruction = instruction
            self.system_prompt = system_prompt
        elif instruction and not system_prompt:
            if "__result__" in instruction:
                # 用户明确指定生成代码prompt的
                self.instruction = "基于模板生成代码"
                self.system_prompt = instruction
            else:
                self.instruction = instruction
                self.system_prompt = AIForgePrompt.get_base_aiforge_prompt(
                    optimize_tokens=self.executor.optimization.get("optimize_tokens", True)
                )
        elif not instruction and system_prompt:
            self.instruction = "请根据系统提示生成代码"
            self.system_prompt = system_prompt
        elif not instruction and not system_prompt:
            return []

        self.task_type = task_type

        # 通过执行引擎设置期望输出（如果执行器有结果管理器的话）
        if hasattr(self.executor, "execution_engine") and hasattr(
            self.executor.execution_engine, "result_processor"
        ):
            if self.executor.execution_engine.result_processor:
                self.executor.execution_engine.result_processor.set_expected_output(expected_output)

        max_optimization_attempts = getattr(self.executor, "max_optimization_attempts", 3)

        self.console.print(
            f"[yellow]开始处理任务指令，最大尝试轮数{self.max_rounds}，单轮最大优化次数{max_optimization_attempts}[/yellow]",  # noqa501
            style="bold",
        )

        rounds = 1
        success = False
        final_result = None
        final_code = ""

        while rounds <= self.max_rounds:
            if rounds > 1:
                time.sleep(0.1)
                # 在新轮次开始时清理错误历史
                if hasattr(self.executor.client, "conversation_manager"):
                    self.executor.client.conversation_manager.error_patterns = []
                    # 清理历史中的错误反馈
                    self.executor.client.conversation_manager.conversation_history = [
                        msg
                        for msg in self.executor.client.conversation_manager.conversation_history
                        if not msg.get("metadata", {}).get("is_error_feedback")
                    ]

            self.console.print(f"\n[cyan]===== 第 {rounds} 轮执行 =====[/cyan]")

            round_success, round_result, round_code, fail_best = (
                self.executor.execute_single_round_with_optimization(
                    rounds,
                    max_optimization_attempts,
                    self.instruction,
                    self.system_prompt,
                    self.task_type,
                )
            )
            if round_success:
                success = True
                final_result = round_result
                final_code = round_code
                if fail_best:
                    self.console.print(
                        "🎉 全部轮次执行失败，返回最佳结果，执行结束！", style="bold yellow"
                    )
                else:
                    self.console.print(f"🎉 第 {rounds} 轮执行成功，任务完成！", style="bold green")
                break
            else:
                if rounds >= self.max_rounds:
                    self.console.print(
                        "⚠️ 全部轮次执行失败，未获取到有效结果，执行结束！", style="yellow"
                    )
                else:
                    self.console.print(
                        f"⚠️ 第 {rounds} 轮执行失败，进入下一轮重新开始", style="yellow"
                    )
                if hasattr(self.executor.client, "reset_conversation"):
                    self.executor.client.reset_conversation()

            rounds += 1

        if hasattr(self.executor, "execution_engine"):
            self.executor.execution_engine.format_execution_summary(
                rounds - 1 if not success else rounds,
                self.max_rounds,
                len(self.executor.task_execution_history),
                success,
            )

        return final_result, final_code, success

    def done(self):
        """标记任务完成"""
        self.task_manager.complete_task(self.task_id)
