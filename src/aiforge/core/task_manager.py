import time
from rich.console import Console
from typing import Optional, List, Dict, Any

from ..llm.llm_manager import AIForgeLLMManager
from ..llm.llm_client import AIForgeLLMClient
from ..execution.executor import AIForgeExecutor
from ..optimization.feedback_optimizer import FeedbackOptimizer
from ..formatting.result_formatter import AIForgeResultFormatter
from ..execution.code_blocks import CodeBlockManager, CodeBlock
from ..prompts.enhanced_prompts import get_base_aiforge_prompt
from .result_manager import AIForgeResult


class AIForgeTask:
    """AIForge 任务执行器"""

    def __init__(
        self, llm_client: AIForgeLLMClient, max_rounds, optimization, max_optimization_attempts
    ):
        self.client = llm_client
        self.executor = AIForgeExecutor()
        self.console = Console()

        self.formatter = AIForgeResultFormatter(self.console)
        self.code_block_manager = CodeBlockManager()

        # 使用统一的结果管理器
        self.result_manager = AIForgeResult(self.console)

        self.instruction = None
        self.system_prompt = None
        self.max_rounds = max_rounds
        self.max_optimization_attempts = max_optimization_attempts
        self.optimization = optimization
        self.execution_history = []
        self.feedback_optimizer = (
            FeedbackOptimizer() if optimization.get("optimize_tokens", True) else None
        )

    def process_code_execution(self, code_blocks: List[str]) -> Optional[str]:
        """处理代码块执行并格式化结果"""
        results = []

        for i, code_text in enumerate(code_blocks):
            if not code_text.strip():
                continue

            block = CodeBlock(code=code_text, name=f"block_{i+1}", version=1)
            self.console.print(f"⚡ 开始执行代码块: {block.name}", style="dim white")

            start_time = time.time()
            result = self.executor.execute_python_code(code_text)
            execution_time = time.time() - start_time

            result["block_name"] = block.name
            result["execution_time"] = execution_time

            self.formatter.format_execution_result(code_text, result, block.name)

            execution_record = {
                "code": code_text,
                "result": result,
                "block_name": block.name,
                "timestamp": time.time(),
                "execution_time": execution_time,
                "success": self.result_manager.basic_execution_check(result),  # 使用ResultManager
            }
            self.execution_history.append(execution_record)

            # 代码执行失败时发送智能反馈
            if not result.get("success"):
                self.client.send_feedback(self.result_manager.get_intelligent_feedback(result))

            results.append(result)

            self.code_block_manager.add_block(block)
            self.code_block_manager.update_block_result(block.name, result, execution_time)
        return results

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
            self.instruction = instruction
            self.system_prompt = get_base_aiforge_prompt(
                optimize_tokens=self.optimization.get("optimize_tokens", True)
            )
        elif not instruction and system_prompt:
            self.instruction = "请根据系统提示生成代码"
            self.system_prompt = system_prompt
        elif not instruction and not system_prompt:
            return []

        self.task_type = task_type
        self.result_manager.set_expected_output(expected_output)

        max_optimization_attempts = getattr(self, "max_optimization_attempts", 3)

        self.console.print(
            f"[yellow]开始处理任务指令，最大尝试轮数{self.max_rounds}，单轮最大优化次数{max_optimization_attempts}[/yellow]",  # noqa 501
            style="bold",
        )

        rounds = 1
        success = False

        while rounds <= self.max_rounds:
            if rounds > 1:
                time.sleep(0.1)
                # 在新轮次开始时清理错误历史
                if hasattr(self.client, "conversation_manager"):
                    self.client.conversation_manager.error_patterns = []
                    # 清理历史中的错误反馈
                    self.client.conversation_manager.conversation_history = [
                        msg
                        for msg in self.client.conversation_manager.conversation_history
                        if not msg.get("metadata", {}).get("is_error_feedback")
                    ]

            self.console.print(f"\n[cyan]===== 第 {rounds} 轮执行 =====[/cyan]")

            round_success = self._execute_single_round_with_optimization(
                rounds, max_optimization_attempts
            )

            if round_success:
                success = True
                self.console.print(f"🎉 第 {rounds} 轮执行成功，任务完成！", style="bold green")
                break
            else:
                self.console.print(f"⚠️ 第 {rounds} 轮执行失败，进入下一轮重新开始", style="yellow")
                if hasattr(self.client, "reset_conversation"):
                    self.client.reset_conversation()

            rounds += 1

        self.formatter.format_execution_summary(
            rounds - 1 if not success else rounds,
            self.max_rounds,
            len(self.execution_history),
            success,
        )

        return self.execution_history

    def _execute_single_round_with_optimization(
        self, round_num: int, max_optimization_attempts: int
    ) -> bool:
        """执行单轮，包含内部优化循环"""
        optimization_attempt = 1

        while optimization_attempt <= max_optimization_attempts:
            self.console.print(
                f"🔄 第 {round_num} 轮，第 {optimization_attempt} 次尝试", style="dim cyan"
            )

            self.console.print("🤖 正在生成代码...", style="dim white")

            if optimization_attempt == 1:
                response = self.client.generate_code(self.instruction, self.system_prompt)
            else:
                minimal_instruction = "根据错误优化代码"
                response = self.client.generate_code(
                    minimal_instruction, self.system_prompt, use_history=True
                )

            if not response:
                self.console.print(f"[red]第 {optimization_attempt} 次尝试：LLM 未返回响应[/red]")
                optimization_attempt += 1
                continue

            code_blocks = self.executor.extract_code_blocks(response)
            if not code_blocks:
                self.console.print(
                    f"[yellow]第 {optimization_attempt} 次尝试：未找到可执行的代码块[/yellow]"
                )
                optimization_attempt += 1
                continue

            self.console.print(f"📝 找到 {len(code_blocks)} 个代码块")

            self.process_code_execution(code_blocks)

            if not self.execution_history:
                self.console.print(f"[red]第 {optimization_attempt} 次尝试：代码执行失败[/red]")
                optimization_attempt += 1
                continue

            last_execution = self.execution_history[-1]

            if not (
                last_execution["result"].get("success") and last_execution["result"].get("result")
            ):
                if not last_execution["result"].get("success"):
                    self.client.send_feedback(
                        self.result_manager.get_intelligent_feedback(last_execution["result"])
                    )

                self.console.print(f"[red]第 {optimization_attempt} 次尝试：代码执行出错[/red]")
                optimization_attempt += 1
                continue

            # 使用ResultManager处理执行结果
            processed_result = self.result_manager.process_execution_result(
                last_execution["result"].get("result"),
                self.instruction,
                getattr(self, "task_type", None),
            )
            last_execution["result"]["result"] = processed_result

            # 使用ResultManager验证执行结果
            is_valid, failure_reason, validation_details = (
                self.result_manager.validate_execution_result(
                    last_execution["result"],
                    self.instruction,
                    getattr(self, "task_type", None),
                    self.client,
                )
            )

            if is_valid:
                last_execution["success"] = True
                if hasattr(self, "executor") and self.executor.history:
                    for history_entry in reversed(self.executor.history):
                        if history_entry.get("code") == last_execution["code"]:
                            history_entry["success"] = True
                            break

                self.console.print(
                    f"✅ 第 {optimization_attempt} 次尝试验证通过！", style="bold green"
                )
                return True
            else:
                last_execution["success"] = False

                if optimization_attempt < max_optimization_attempts:
                    self.console.print(
                        f"⚠️ 第 {optimization_attempt} 次尝试验证失败: {failure_reason}，发送优化反馈",
                        style="yellow",
                    )
                    self.client.send_feedback(
                        self.result_manager.get_validation_feedback(
                            failure_reason, validation_details, optimization_attempt
                        )
                    )
                    optimization_attempt += 1
                else:
                    self.console.print(
                        f"❌ 第 {optimization_attempt} 次尝试验证失败，已达到最大优化次数，放弃当前轮",
                        style="red",
                    )
                    return False

        # 所有优化尝试都失败
        self.console.print(f"❌ 单轮内 {max_optimization_attempts} 次优化尝试全部失败", style="red")
        return False

    def done(self):
        """任务完成清理"""
        pass


class AIForgeManager:
    """AIForge任务管理器"""

    def __init__(self, llm_manager: AIForgeLLMManager):
        self.llm_manager = llm_manager
        self.tasks = []

    def new_task(
        self,
        instruction: str | None = None,
        client: AIForgeLLMClient = None,
    ) -> AIForgeTask:
        """创建新任务"""
        if not client:
            client = self.llm_manager.get_client()

        task = AIForgeTask(
            client,
            self.llm_manager.config.get_max_rounds(),
            self.llm_manager.config.get_optimization_config(),
            self.llm_manager.config.get_max_optimization_attempts(),
        )
        if instruction:
            task.instruction = instruction
        self.tasks.append(task)
        return task
