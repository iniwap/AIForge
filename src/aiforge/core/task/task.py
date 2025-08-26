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
        components: Dict[str, Any] = None,
    ):
        self.task_id = task_id
        self.task_manager = task_manager
        self.components = components or {}
        self.console = Console()
        self._i18n_manager = self.components.get("i18n_manager")
        self._shutdown_manager = components.get("shutdown_manager")

        # 使用拆分后的执行器，传递 components 参数
        self.executor = TaskExecutor(
            llm_client, max_rounds, optimization, max_optimization_attempts, components
        )

        self.instruction = None
        self.system_prompt = None
        self.max_rounds = max_rounds
        self.task_type = None
        self._ai_forgePrompt = AIForgePrompt(self.components)

    def run(
        self,
        instruction: str | None = None,
        system_prompt: str | None = None,
        task_type: str | None = None,
        expected_output: Dict[str, Any] = None,
    ):
        """执行方法"""
        if self._shutdown_manager.is_shutting_down():
            return False, None, ""

        if instruction and system_prompt:
            self.instruction = instruction
            self.system_prompt = system_prompt
        elif instruction and not system_prompt:
            if "__result__" in instruction:
                # 用户明确指定生成代码prompt的
                self.instruction = self._i18n_manager.t("task.template_code_generation")
                self.system_prompt = instruction
            else:
                self.instruction = instruction
                self.system_prompt = self._ai_forgePrompt.get_base_aiforge_prompt(
                    optimize_tokens=self.executor.optimization.get("optimize_tokens", True)
                )
        elif not instruction and system_prompt:
            self.instruction = self._i18n_manager.t("task.system_prompt_generation")
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

        # 使用 i18n 的任务开始消息
        start_message = self._i18n_manager.t(
            "task.processing_start",
            max_rounds=self.max_rounds,
            max_optimization=max_optimization_attempts,
        )
        self.console.print(f"[yellow]{start_message}[/yellow]", style="bold")

        rounds = 1
        success = False
        final_result = None
        final_code = ""

        while rounds <= self.max_rounds:
            if self._shutdown_manager.is_shutting_down():
                break

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

            # 使用 i18n 的轮次执行消息
            round_message = self._i18n_manager.t("task.round_execution", round=rounds)
            self.console.print(f"\n[cyan]===== {round_message} =====[/cyan]")

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
                    best_result_message = self._i18n_manager.t("task.all_rounds_failed_best_result")
                    self.console.print(f"🎉 {best_result_message}", style="bold yellow")
                else:
                    success_message = self._i18n_manager.t(
                        "task.round_success_completed", round=rounds
                    )
                    self.console.print(f"🎉 {success_message}", style="bold green")
                break
            else:
                if self._shutdown_manager.is_shutting_down():
                    break

                if rounds >= self.max_rounds:
                    all_failed_message = self._i18n_manager.t("task.all_rounds_failed_no_result")
                    self.console.print(f"⚠️ {all_failed_message}", style="yellow")
                else:
                    round_failed_message = self._i18n_manager.t(
                        "task.round_failed_continue", round=rounds
                    )
                    self.console.print(f"⚠️ {round_failed_message}", style="yellow")
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
