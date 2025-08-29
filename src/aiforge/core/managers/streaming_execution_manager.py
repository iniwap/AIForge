import asyncio
import json
import time
from typing import Dict, Any, AsyncGenerator
from ...utils.progress_indicator import StreamingProgressEventHandler
from ..engine import AIForgeEngine


class AIForgeStreamingExecutionManager:
    """流式执行管理器 - 为界面提供实时进度反馈"""

    def __init__(self, components: Dict[str, Any], engine: AIForgeEngine = None):
        self.components = components
        self.engine = engine

    async def execute_with_streaming(
        self, instruction: str, ui_type: str = "web", context_data: Dict[str, Any] = None
    ) -> AsyncGenerator[str, None]:
        """流式执行指令并返回进度 - 支持进度级别控制"""

        # 获取进度级别设置，默认为详细模式
        progress_level = (
            context_data.get("progress_level", "detailed") if context_data else "detailed"
        )

        progress_queue = asyncio.Queue()
        execution_complete = asyncio.Event()
        execution_result = None
        execution_error = None

        async def progress_callback(message_data: Dict[str, Any]):
            """进度回调函数 - 根据进度级别过滤消息"""
            try:
                message_type = message_data.get("type", "progress")
                progress_type = message_data.get("progress_type", "info")

                # 根据进度级别决定是否发送消息
                should_send = False

                if progress_level == "none":
                    # 只发送结果、错误和完成消息
                    should_send = message_type in ["result", "error", "complete"]
                elif progress_level == "minimal":
                    # 只发送关键节点消息
                    should_send = message_type in [
                        "result",
                        "error",
                        "complete",
                    ] or progress_type in [
                        "task_start",
                        "task_complete",
                    ]
                else:  # detailed
                    # 发送所有消息
                    should_send = True

                if should_send:
                    await progress_queue.put(message_data)
            except Exception:
                pass

        # 替换进度指示器为 Web 流式版本
        progress_bus = self.components.get("progress_indicator")
        original_progress = progress_bus.get_handler()
        streaming_handler = StreamingProgressEventHandler(self.components, progress_callback)
        progress_bus.set_handler(streaming_handler)
        # 根据前端设置的进度级别来控制是否显示进度
        streaming_handler.set_show_progress(progress_level != "none")

        try:
            # 发送开始消息（根据进度级别决定是否发送）
            await progress_callback(
                {
                    "type": "progress",
                    "message": "🚀 开始执行指令...",
                    "progress_type": "task_start",
                    "timestamp": time.time(),
                }
            )

            # 后台执行任务
            async def execute_task():
                nonlocal execution_result, execution_error
                try:
                    # 准备输入数据（与同步端点保持一致）
                    raw_input = {
                        "instruction": instruction,
                        "method": "POST",
                        "user_agent": "AIForge-Web",
                        "ip_address": "127.0.0.1",
                        "request_id": context_data.get("session_id") if context_data else None,
                    }

                    result = await asyncio.to_thread(
                        self.engine.run_with_input_adaptation, raw_input, "web", context_data or {}
                    )
                    if result:
                        # 从结果的 metadata 中获取任务类型，回退到 context_data
                        task_type = result.task_type or context_data.get("task_type")
                        ui_result = await asyncio.to_thread(
                            self.engine.adapt_result_for_ui,
                            result,
                            "editor" if task_type == "content_generation" else None,
                            "web",
                        )
                        execution_result = {
                            "success": True,
                            "result": ui_result,
                            "metadata": {"source": "web", "processed_at": time.time()},
                        }
                    else:
                        execution_error = "执行失败：未获得结果"

                except Exception as e:
                    execution_error = f"执行错误: {str(e)}"
                    # 发送错误进度消息
                    await progress_callback(
                        {
                            "type": "progress",
                            "message": f"❌ 执行失败: {str(e)}",
                            "progress_type": "error",
                            "timestamp": time.time(),
                        }
                    )
                finally:
                    execution_complete.set()

            # 启动执行任务
            task = asyncio.create_task(execute_task())

            try:
                # 流式返回进度消息
                while not execution_complete.is_set():
                    try:
                        # 检查客户端是否断开连接
                        if hasattr(self, "_client_disconnected") and self._client_disconnected:
                            # 取消后台任务
                            task.cancel()
                            yield f"data: {json.dumps({'type': 'cancelled', 'message': '执行已被用户停止'})}\n\n"  # noqa 501
                            break

                        # 等待进度消息
                        message = await asyncio.wait_for(progress_queue.get(), timeout=0.5)
                        yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
                    except asyncio.TimeoutError:
                        # 发送心跳保持连接
                        yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"  # noqa 501
            except GeneratorExit:
                # 客户端断开连接时触发
                self._client_disconnected = True
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # 等待执行完成
            await task

            # 处理剩余进度消息
            while not progress_queue.empty():
                try:
                    message = progress_queue.get_nowait()
                    yield f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
                except asyncio.QueueEmpty:
                    break

            # 发送最终结果
            if execution_result:
                yield f"data: {json.dumps({'type': 'result', 'data': execution_result}, ensure_ascii=False)}\n\n"  # noqa 501
            elif execution_error:
                yield f"data: {json.dumps({'type': 'error', 'message': execution_error}, ensure_ascii=False)}\n\n"  # noqa 501

            # 发送完成信号
            print("🎉 任务执行完成，结果已发送...")
            yield f"data: {json.dumps({'type': 'complete', 'timestamp': time.time()})}\n\n"

        except Exception as e:
            # 发送错误信息
            error_message = f"流式执行错误: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'message': error_message}, ensure_ascii=False)}\n\n"  # noqa 501

        finally:
            # 恢复原始进度指示器
            if original_progress:
                progress_bus.set_handler(original_progress)
