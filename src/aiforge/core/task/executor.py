import time
from typing import List, Dict, Any, Tuple
from rich.console import Console

from ...llm.llm_client import AIForgeLLMClient
from .feedback_optimizer import FeedbackOptimizer


class TaskExecutor:
    """任务执行器"""

    def __init__(
        self,
        llm_client: AIForgeLLMClient,
        max_rounds: int,
        optimization: Dict[str, Any],
        max_optimization_attempts: int,
        components: Dict[str, Any] = None,
    ):
        self.client = llm_client
        self.console = Console()

        self._i18n_manager = components.get("i18n_manager")
        self._shutdown_manager = components.get("shutdown_manager")

        # 通过components获取执行引擎，如果没有则创建新的
        if components and "execution_engine" in components:
            self.execution_engine = components["execution_engine"]
        else:
            # 如果没有提供执行引擎，需要导入并创建
            from ...execution.engine import AIForgeExecutionEngine

            self.execution_engine = AIForgeExecutionEngine(components)

        self.max_rounds = max_rounds
        self.max_optimization_attempts = max_optimization_attempts
        self.optimization = optimization

        # 任务级别的执行历史
        self.task_execution_history = []

        self.feedback_optimizer = (
            FeedbackOptimizer() if optimization.get("optimize_tokens", True) else None
        )

    def process_code_execution(self, code_blocks: List[str]) -> List[Dict[str, Any]]:
        """处理代码块执行并格式化结果"""
        results = []

        for i, code_text in enumerate(code_blocks):
            if not code_text.strip():
                continue

            # 通过执行引擎创建和管理代码块
            block_name = f"block_{i+1}"
            start_execution_message = self._i18n_manager.t(
                "executor.start_execution_block", block_name=block_name
            )
            self.console.print(f"⚡ {start_execution_message}", style="dim white")

            start_time = time.time()
            result = self.execution_engine.execute_python_code(code_text)
            execution_time = time.time() - start_time

            result["block_name"] = block_name
            result["execution_time"] = execution_time

            # 格式化执行结果
            self.execution_engine.format_execution_result(code_text, result, block_name)

            # 创建任务级别的执行记录
            execution_record = {
                "code": code_text,
                "result": result,
                "block_name": block_name,
                "timestamp": time.time(),
                "execution_time": execution_time,
                "success": self.execution_engine.basic_execution_check(result),
            }
            self.task_execution_history.append(execution_record)

            # 代码执行失败时发送智能反馈
            if not result.get("success"):
                feedback = self.execution_engine.get_intelligent_feedback(result)
                self.client.send_feedback(feedback)

            results.append(result)

            # 通过执行引擎管理代码块
            self.execution_engine.add_block(code_text, block_name, 1)
            self.execution_engine.update_block_result(block_name, result, execution_time)

        return results

    def execute_single_round_with_optimization(
        self,
        round_num: int,
        max_optimization_attempts: int,
        instruction: str,
        system_prompt: str,
        task_type: str = None,
    ) -> Tuple[bool, Any, str, bool]:
        """执行单轮，包含内部优化循环"""
        optimization_attempt = 1

        while optimization_attempt <= max_optimization_attempts:
            # 每次循环开始时检查停止信号
            if self._shutdown_manager.is_shutting_down():
                return False, None, "", False

            round_attempt_message = self._i18n_manager.t(
                "executor.round_attempt",
                round_num=round_num,
                optimization_attempt=optimization_attempt,
            )
            self.console.print(f"🔄 {round_attempt_message}", style="dim cyan")

            generating_code_message = self._i18n_manager.t("executor.generating_code")
            self.console.print(f"🤖 {generating_code_message}", style="dim white")

            # 生成代码前再次检查停止信号
            if self._shutdown_manager.is_shutting_down():
                return False, None, "", False

            if optimization_attempt == 1:
                response = self.client.generate_code(instruction, system_prompt, use_history=False)
            else:
                response = self.client.generate_code(
                    None,
                    system_prompt,
                    use_history=True,
                    context_type="feedback",
                )

            # 检查LLM响应是否因停止而返回None
            if not response:
                if self._shutdown_manager.is_shutting_down():
                    return False, None, "", False

                no_response_message = self._i18n_manager.t(
                    "executor.no_llm_response", optimization_attempt=optimization_attempt
                )
                self.console.print(f"[red]{no_response_message}[/red]")
                optimization_attempt += 1
                continue

            # 代码执行前检查停止信号
            if self._shutdown_manager.is_shutting_down():
                return False, None, "", False

            # 其余执行逻辑保持不变，但在关键点添加停止检查...
            code_blocks = self.execution_engine.extract_code_blocks(response)
            if not code_blocks:
                no_code_blocks_message = self._i18n_manager.t(
                    "executor.no_code_blocks_found", optimization_attempt=optimization_attempt
                )
                self.console.print(f"[yellow]{no_code_blocks_message}[/yellow]")
                optimization_attempt += 1
                continue

            found_blocks_message = self._i18n_manager.t(
                "executor.found_code_blocks", count=len(code_blocks)
            )
            self.console.print(f"📝 {found_blocks_message}")

            # 执行代码块前检查停止信号
            if self._shutdown_manager.is_shutting_down():
                return False, None, "", False

            # 处理代码块执行
            self.process_code_execution(code_blocks)

            # 验证前检查停止信号
            if self._shutdown_manager.is_shutting_down():
                return False, None, "", False

            # 其余验证逻辑...
            if not self.task_execution_history:
                execution_failed_message = self._i18n_manager.t(
                    "executor.code_execution_failed", optimization_attempt=optimization_attempt
                )
                self.console.print(f"[red]{execution_failed_message}[/red]")
                optimization_attempt += 1
                continue

            last_execution = self.task_execution_history[-1]

            if not (
                last_execution["result"].get("success") and last_execution["result"].get("result")
            ):
                if not last_execution["result"].get("success"):
                    feedback = self.execution_engine.get_intelligent_feedback(
                        last_execution["result"]
                    )
                    self.client.send_feedback(feedback)

                execution_error_message = self._i18n_manager.t(
                    "executor.code_execution_error", optimization_attempt=optimization_attempt
                )
                self.console.print(f"[red]{execution_error_message}[/red]")
                optimization_attempt += 1
                continue

            # 处理和验证结果...
            processed_result = self.execution_engine.process_execution_result(
                last_execution["result"].get("result"),
                instruction,
                task_type,
            )
            last_execution["result"]["result"] = processed_result

            # 验证前最后检查停止信号
            if self._shutdown_manager.is_shutting_down():
                return False, None, "", False

            is_valid, validation_type, failure_reason, validation_details = (
                self.execution_engine.validate_execution_result(
                    last_execution["result"],
                    instruction,
                    task_type,
                    self.client,
                )
            )

            if is_valid:
                last_execution["success"] = True
                # 同步更新执行引擎的代码级别历史
                if hasattr(self.execution_engine, "history") and self.execution_engine.history:
                    for history_entry in reversed(self.execution_engine.history):
                        if history_entry.get("code") == last_execution["code"]:
                            history_entry["success"] = True
                            break

                validation_passed_message = self._i18n_manager.t(
                    "executor.validation_passed", optimization_attempt=optimization_attempt
                )
                self.console.print(f"✅ {validation_passed_message}", style="bold green")
                return (
                    True,
                    last_execution["result"].get("result"),
                    last_execution.get("code", ""),
                    False,
                )
            else:
                last_execution["success"] = False

                if optimization_attempt < max_optimization_attempts:
                    # 检查停止信号
                    if self._shutdown_manager.is_shutting_down():
                        return False, None, "", False

                    validation_failed_message = self._i18n_manager.t(
                        "executor.validation_failed",
                        optimization_attempt=optimization_attempt,
                        validation_type=validation_type,
                        failure_reason=failure_reason,
                    )
                    self.console.print(f"⚠️ {validation_failed_message}", style="yellow")
                    validation_feedback = self.execution_engine.get_validation_feedback(
                        failure_reason, validation_details
                    )
                    self.client.send_feedback(validation_feedback)
                    optimization_attempt += 1
                else:
                    final_validation_failed_message = self._i18n_manager.t(
                        "executor.final_validation_failed",
                        optimization_attempt=optimization_attempt,
                        validation_type=validation_type,
                        failure_reason=failure_reason,
                    )
                    self.console.print(f"❌ {final_validation_failed_message}")

                    # 尝试返回最佳可用结果
                    best_result, best_code = self._get_best_available_result()
                    if best_result:
                        last_execution["result"]["result"] = best_result
                        last_execution["success"] = True
                        return True, best_result, best_code, True

                    return False, None, "", False

        # 所有优化尝试都失败
        all_attempts_failed_message = self._i18n_manager.t(
            "executor.all_attempts_failed", max_optimization_attempts=max_optimization_attempts
        )
        self.console.print(f"❌ {all_attempts_failed_message}", style="red")
        return False, None, "", False

    def _get_best_available_result(self):
        """获取质量最佳的可用结果"""
        if not self.task_execution_history:
            return None

        best_result = None
        best_code = ""
        max_valid_items = 0

        for execution in reversed(self.task_execution_history):
            result = execution.get("result", {}).get("result", {})
            if isinstance(result, dict):
                data = result.get("data", [])
                if isinstance(data, list):
                    # 统计有效数据项数量
                    valid_count = 0
                    for item in data:
                        if isinstance(item, dict):
                            title = item.get("title", "").strip()
                            content = item.get("content", "").strip()
                            if title and content and len(content) > 20:
                                valid_count += 1

                    if valid_count > max_valid_items:
                        max_valid_items = valid_count
                        best_code = execution.get("code", "")
                        # 过滤并返回有效数据
                        valid_data = []
                        for item in data:
                            if isinstance(item, dict):
                                title = item.get("title", "").strip()
                                content = item.get("content", "").strip()
                                if title and content and len(content) > 20:
                                    valid_data.append(item)

                        best_result_summary = self._i18n_manager.t(
                            "executor.best_result_summary", count=len(valid_data)
                        )
                        best_result = {
                            "data": valid_data,
                            "status": "success",
                            "summary": best_result_summary,
                            "metadata": result.get("metadata", {}),
                        }

        return best_result, best_code
