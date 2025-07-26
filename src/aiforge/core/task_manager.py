import json
import time
import hashlib
from rich.console import Console
from typing import Optional, List, Dict, Any, Tuple

from ..llm.llm_manager import AIForgeLLMManager
from ..llm.llm_client import AIForgeLLMClient
from ..execution.executor import AIForgeExecutor
from ..optimization.feedback_optimizer import FeedbackOptimizer
from ..formatting.result_formatter import AIForgeResultFormatter
from ..execution.code_blocks import CodeBlockManager, CodeBlock
from ..prompts.enhanced_prompts import get_base_aiforge_prompt
from .enhanced_error_analyzer import EnhancedErrorAnalyzer
from ..validation.result_validator import IntelligentResultValidator


class AIForgeTask:
    """AIForge 任务执行器 - 专注于任务执行流程控制"""

    def __init__(
        self, llm_client: AIForgeLLMClient, max_rounds, optimization, max_optimization_attempts
    ):
        self.client = llm_client
        self.executor = AIForgeExecutor()
        self.console = Console()

        self.formatter = AIForgeResultFormatter(self.console)
        self.code_block_manager = CodeBlockManager()
        self.error_analyzer = EnhancedErrorAnalyzer()

        # 智能结果验证器
        self.result_validator = IntelligentResultValidator(llm_client)
        self.expected_output = None

        self.instruction = None
        self.system_prompt = None
        self.max_rounds = max_rounds
        self.max_optimization_attempts = max_optimization_attempts
        self.optimization = optimization
        self.execution_history = []
        self.feedback_optimizer = (
            FeedbackOptimizer() if optimization.get("optimize_tokens", True) else None
        )

    def set_expected_output(self, expected_output: Dict[str, Any]):
        """设置预期输出规则"""
        self.expected_output = expected_output

    def _basic_execution_check(self, result: Dict[str, Any]) -> bool:
        """基础执行检查"""
        if not result.get("success", False):
            return False

        result_content = result.get("result")
        if result_content is None:
            return False

        if isinstance(result_content, dict):
            status = result_content.get("status")
            if status == "error":
                return False
            elif status == "success":
                return True
            if "error" in result_content or "exception" in result_content:
                return False

        return True

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
                "success": self._basic_execution_check(result),
            }
            self.execution_history.append(execution_record)

            # 代码执行失败时发送智能反馈
            if not result.get("success"):
                self._send_intelligent_feedback(result)

            results.append(result)

            self.code_block_manager.add_block(block)
            self.code_block_manager.update_block_result(block.name, result, execution_time)
        return results

    def _send_intelligent_feedback(self, result: Dict[str, Any]):
        """使用 EnhancedErrorAnalyzer 发送精简但有效的反馈"""
        error_info = result.get("error", "")
        traceback_info = result.get("traceback", "")

        # 使用增强的错误分析器生成智能反馈
        feedback = self.error_analyzer.generate_execution_feedback(error_info, traceback_info)

        feedback_json = json.dumps(feedback, ensure_ascii=False)
        self.client.send_feedback(feedback_json)

    def _validate_execution_result_intelligent(
        self, result: Dict[str, Any], instruction: str, task_type: str = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """使用智能验证器验证执行结果"""
        if not self.expected_output:
            is_valid = self._basic_execution_check(result)
            if not is_valid:
                # 使用 EnhancedErrorAnalyzer 分析失败原因
                failure_reason = self.error_analyzer.analyze_basic_failure_reason(result)
                return False, failure_reason, {"validation_type": "basic"}
            return True, "", {}

        return self.result_validator.validate_execution_result(
            result, self.expected_output, instruction, task_type or "general"
        )

    def _send_validation_feedback(
        self, failure_reason: str, validation_details: Dict[str, Any], attempt_num: int
    ):
        """发送验证失败反馈"""
        # 使用 EnhancedErrorAnalyzer 分析验证失败
        feedback = self.error_analyzer.generate_validation_feedback(
            failure_reason, validation_details, attempt_num, self.expected_output
        )

        feedback_json = json.dumps(feedback, ensure_ascii=False)
        self.client.send_feedback(feedback_json)

    def _process_execution_result(self, result_content, instruction, task_type=None):
        """后处理执行结果，强制标准化格式"""
        from datetime import datetime

        task_type = task_type or "general"

        if not isinstance(result_content, dict):
            result_content = {
                "data": result_content,
                "status": "success" if result_content else "error",
                "summary": "执行完成" if result_content else "执行失败",
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "task_type": task_type,
                    "auto_wrapped": True,
                },
            }
        else:
            result_content.setdefault("status", "success")
            result_content.setdefault("summary", "操作完成")
            result_content.setdefault("metadata", {})
            result_content["metadata"].update(
                {
                    "timestamp": datetime.now().isoformat(),
                    "task_type": task_type,
                    "instruction_hash": hashlib.md5(instruction.encode()).hexdigest(),
                }
            )

        processed_result = self.formatter.format_task_type_result(result_content, task_type)
        return processed_result

    def run(
        self,
        instruction: str | None = None,
        system_prompt: str | None = None,
        task_type: str | None = None,
    ):
        """执行方法 - 支持单轮内有限次数优化"""
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
                    self._send_intelligent_feedback(last_execution["result"])

                self.console.print(f"[red]第 {optimization_attempt} 次尝试：代码执行出错[/red]")
                optimization_attempt += 1
                continue

            processed_result = self._process_execution_result(
                last_execution["result"].get("result"),
                self.instruction,
                getattr(self, "task_type", None),
            )
            last_execution["result"]["result"] = processed_result

            is_valid, failure_reason, validation_details = (
                self._validate_execution_result_intelligent(
                    last_execution["result"],
                    self.instruction,
                    getattr(self, "task_type", None),
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
                    self._send_validation_feedback(
                        failure_reason, validation_details, optimization_attempt
                    )
                    optimization_attempt += 1
                else:
                    # 已达到最大优化次数，放弃当前轮
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
