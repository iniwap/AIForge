import time
from typing import List, Dict, Any, Tuple
from rich.console import Console

from ...llm.llm_client import AIForgeLLMClient
from ...optimization.feedback_optimizer import FeedbackOptimizer


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
        """处理代码块执行并格式化结果 - 通过执行引擎统一处理"""
        results = []

        for i, code_text in enumerate(code_blocks):
            if not code_text.strip():
                continue

            # 通过执行引擎创建和管理代码块
            block_name = f"block_{i+1}"
            self.console.print(f"⚡ 开始执行代码块: {block_name}", style="dim white")

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
                "success": self.execution_engine.basic_execution_check(result),  # 通过执行引擎检查
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
            self.console.print(
                f"🔄 第 {round_num} 轮，第 {optimization_attempt} 次尝试", style="dim cyan"
            )

            self.console.print("🤖 正在生成代码...", style="dim white")

            if optimization_attempt == 1:
                # 首次生成，不使用历史
                response = self.client.generate_code(instruction, system_prompt, use_history=False)
            else:
                response = self.client.generate_code(
                    None,
                    system_prompt,
                    use_history=True,
                    context_type="feedback",
                )

            if not response:
                self.console.print(f"[red]第 {optimization_attempt} 次尝试：LLM 未返回响应[/red]")
                optimization_attempt += 1
                continue

            # 通过执行引擎提取代码块
            code_blocks = self.execution_engine.extract_code_blocks(response)
            if not code_blocks:
                self.console.print(
                    f"[yellow]第 {optimization_attempt} 次尝试：未找到可执行的代码块[/yellow]"
                )
                optimization_attempt += 1
                continue

            self.console.print(f"📝 找到 {len(code_blocks)} 个代码块")

            # 处理代码块执行
            self.process_code_execution(code_blocks)

            if not self.task_execution_history:
                self.console.print(f"[red]第 {optimization_attempt} 次尝试：代码执行失败[/red]")
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

                self.console.print(f"[red]第 {optimization_attempt} 次尝试：代码执行出错[/red]")
                optimization_attempt += 1
                continue

            # 通过执行引擎处理执行结果
            processed_result = self.execution_engine.process_execution_result(
                last_execution["result"].get("result"),
                instruction,
                task_type,
            )
            last_execution["result"]["result"] = processed_result

            # 通过执行引擎验证执行结果
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

                self.console.print(
                    f"✅ 第 {optimization_attempt} 次尝试验证通过！", style="bold green"
                )
                return (
                    True,
                    last_execution["result"].get("result"),
                    last_execution.get("code", ""),
                    False,
                )
            else:
                last_execution["success"] = False

                if optimization_attempt < max_optimization_attempts:
                    self.console.print(
                        f"⚠️ 第 {optimization_attempt} 次尝试验证失败（{validation_type}）: {failure_reason}",
                        style="yellow",
                    )
                    validation_feedback = self.execution_engine.get_validation_feedback(
                        failure_reason, validation_details
                    )
                    self.client.send_feedback(validation_feedback)
                    optimization_attempt += 1
                else:
                    self.console.print(
                        f"❌ 第 {optimization_attempt} 次尝试验证失败（{validation_type}）: {failure_reason}，已达到最大优化次数",  # noqa 501
                    )

                    # 尝试返回最佳可用结果
                    best_result = self._get_best_available_result()
                    if best_result:
                        # 查找对应的代码
                        best_code = ""
                        for execution in reversed(self.task_execution_history):
                            if execution.get("result", {}).get("result") == best_result:
                                best_code = execution.get("code", "")
                                break

                        last_execution["result"]["result"] = best_result
                        last_execution["success"] = True
                        return True, best_result, best_code, True

                    return False, None, "", False

        # 所有优化尝试都失败
        self.console.print(f"❌ 单轮内 {max_optimization_attempts} 次优化尝试全部失败", style="red")
        return False, None, "", False

    def _get_best_available_result(self):
        """获取质量最佳的可用结果 - 保持原有逻辑"""
        if not self.task_execution_history:
            return None

        best_result = None
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
                        # 过滤并返回有效数据
                        valid_data = []
                        for item in data:
                            if isinstance(item, dict):
                                title = item.get("title", "").strip()
                                content = item.get("content", "").strip()
                                if title and content and len(content) > 20:
                                    valid_data.append(item)

                        best_result = {
                            "data": valid_data,
                            "status": "success",
                            "summary": f"返回{len(valid_data)}条最佳结果",
                            "metadata": result.get("metadata", {}),
                        }

        return best_result
