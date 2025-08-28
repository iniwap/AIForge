import requests
import time
import threading
from rich.console import Console
from typing import Dict, Any, Set
from .conversation_manager import ConversationManager
from .adapters.adapter_factory import AdapterFactory


class AIForgeLLMClient:
    """AIForge LLM 客户端"""

    def __init__(
        self,
        name: str,
        api_key: str,
        base_url: str | None = None,
        model: str = "gpt-3.5-turbo",
        timeout: int = 30,
        max_tokens: int = 8192,
        client_type: str = "openai",
        components: Dict[str, Any] = None,
    ):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.console = Console()
        self.client_type = client_type

        # 请求会话管理
        self._session = requests.Session()
        self._active_requests: Set[requests.Response] = set()
        self._request_lock = threading.Lock()
        self._is_cancelled = threading.Event()

        self._shutdown_manager = components.get("shutdown_manager")
        # 注册到全局关闭管理器
        self._shutdown_manager.register_cleanup_callback(self.shutdown)

        self.conversation_manager = ConversationManager()
        self.usage_stats = {"total_tokens": 0, "rounds": 0}
        self.components = components or {}
        self._i18n_manager = self.components.get("i18n_manager")
        self.adapter = AdapterFactory.create_adapter(
            {"type": client_type, "api_key": api_key, "model": model, "base_url": base_url}
        )
        self._progress_indicator = components.get("progress_indicator")

    def shutdown(self):
        """统一的关闭方法"""
        self._is_cancelled.set()
        with self._request_lock:
            try:
                self._session.close()
            except Exception:
                pass

    def is_usable(self) -> bool:
        """检查客户端是否可用"""
        if hasattr(self, "client_type") and self.client_type == "ollama":
            return bool(self.model and self.base_url)
        return bool(self.api_key and self.model)

    def generate_code(
        self,
        instruction: str,
        system_prompt: str | None = None,
        use_history: bool = True,
        max_retries: int = 2,
        context_type: str = "generation",
    ) -> str | None:
        """生成代码 - 支持取消"""

        # 检查是否已被取消
        if self._is_cancelled.is_set() or self._shutdown_manager.is_shutting_down():
            return None

        self._progress_indicator.emit("llm_request", provider=self.name)
        for attempt in range(max_retries):
            # 每次重试前检查取消状态
            if self._is_cancelled.is_set() or self._shutdown_manager.is_shutting_down():
                return None

            try:
                if attempt == 0:
                    self._progress_indicator.emit("llm_generating")

                # 准备消息
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})

                if use_history:
                    context_messages = self.conversation_manager.get_context_messages()
                    messages.extend(context_messages)

                if instruction:
                    messages.append({"role": "user", "content": instruction})

                # 基础payload
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": self.max_tokens,
                }

                # 使用适配器准备请求
                adapted_payload, headers = self.adapter.prepare_request(messages, payload)
                endpoint = self.adapter.get_endpoint(self.base_url)

                # 发送请求 - 使用会话以支持取消
                response = self._session.post(
                    endpoint,
                    headers=headers,
                    json=adapted_payload,
                    timeout=self.timeout,
                )

                # 检查请求是否在处理过程中被取消
                if self._is_cancelled.is_set() or self._shutdown_manager.is_shutting_down():
                    return None

                if response.status_code == 200:
                    self._progress_indicator.emit("llm_complete")
                    result = response.json()

                    # 使用适配器解析响应
                    assistant_response = self.adapter.parse_response(result)

                    # 记录到对话历史
                    if use_history:
                        self.conversation_manager.add_message("user", instruction)
                        self.conversation_manager.add_message("assistant", assistant_response)

                    # 更新使用统计
                    if "usage" in result:
                        usage = result["usage"]
                        self.usage_stats["total_tokens"] += usage.get("total_tokens", 0)
                    self.usage_stats["rounds"] += 1

                    return assistant_response
                else:
                    can_retry, error_msg = self.adapter.handle_error(
                        response.status_code, response.json() if response.content else {}
                    )

                    if can_retry and attempt < max_retries - 1:
                        if response.status_code == 429:
                            wait_time = (2**attempt) * 5  # 5秒基础间隔
                        else:
                            wait_time = (2**attempt) * 1

                        self.console.print(f"[yellow]{error_msg}，{wait_time}秒后重试...[/yellow]")

                        # 等待时也要检查取消状态
                        for _ in range(wait_time * 10):  # 0.1秒间隔检查
                            if (
                                self._is_cancelled.is_set()
                                or self._shutdown_manager.is_shutting_down()
                            ):
                                return None
                            time.sleep(0.1)
                        continue
                    else:
                        self.console.print(f"[red]{error_msg}[/red]")
                        return None

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if self._is_cancelled.is_set() or self._shutdown_manager.is_shutting_down():
                    return None
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    return None
            except Exception as e:
                if self._is_cancelled.is_set() or self._shutdown_manager.is_shutting_down():
                    return None
                error_message = self._i18n_manager.t(
                    "llm_client.request_failed", name=self.name, error=str(e)
                )

                self.console.print(f"[red]{error_message}[/red]")
                return None

        return None

    def __del__(self):
        """析构函数 - 清理资源"""
        self._shutdown_manager.unregister_cleanup_callback(self.shutdown)
        self.shutdown()

    def send_feedback(self, feedback: str, is_error: bool = True, metadata: Dict[str, Any] = None):
        """发送反馈信息，使用特殊的历史管理"""
        if not feedback:
            return

        if not metadata:
            metadata = {}

        metadata["is_error_feedback"] = is_error
        metadata["message_type"] = "feedback"

        # 反馈消息不参与常规的代码生成上下文
        self.conversation_manager.add_message("user", feedback, metadata)

    def get_usage_stats(self):
        """获取使用统计"""
        return self.usage_stats.copy()

    def reset_conversation(self):
        """重置对话历史"""
        self.conversation_manager = ConversationManager()

    def get_conversation_summary(self) -> Dict[str, Any]:
        """获取对话摘要"""
        return {
            "message_count": len(self.conversation_manager.conversation_history),
            "error_patterns": list(set(self.conversation_manager.error_patterns)),
            "recent_messages": self.conversation_manager.conversation_history[-3:],
        }


class AIForgeOllamaClient(AIForgeLLMClient):
    """Ollama客户端实现"""

    def __init__(
        self,
        name: str,
        base_url: str,
        model: str,
        timeout: int = 30,
        max_tokens: int = 8192,
        components: Dict[str, Any] = None,
    ):
        super().__init__(name, "", base_url, model, timeout, max_tokens, components=components)

    def is_usable(self) -> bool:
        """Ollama不需要API key"""
        return bool(self.model and self.base_url)

    def generate_code(
        self,
        instruction: str,
        system_prompt: str | None = None,
        use_history: bool = True,
        max_retries: int = 2,
    ) -> str | None:
        """Ollama特定的实现"""
        for attempt in range(max_retries):
            try:
                messages = []

                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})

                if use_history:
                    context_messages = self.conversation_manager.get_context_messages()
                    messages.extend(context_messages)

                messages.append({"role": "user", "content": instruction})

                payload = {"model": self.model, "messages": messages, "stream": False}

                response = requests.post(
                    f"{self.base_url}/api/chat", json=payload, timeout=self.timeout
                )

                if response.status_code == 200:
                    result = response.json()
                    assistant_response = result["message"]["content"]

                    if use_history:
                        self.conversation_manager.add_message("user", instruction)
                        self.conversation_manager.add_message("assistant", assistant_response)

                    return assistant_response
                else:
                    if response.status_code >= 500:
                        wait_time = (2**attempt) * 1
                        error_message = self._i18n_manager.t(
                            "llm_client.server_error_retry",
                            name=self.name,
                            status_code=response.status_code,
                            attempt=attempt + 1,
                            wait_time=wait_time,
                        )

                        self.console.print(f"[yellow]{error_message}[/yellow]")
                        time.sleep(wait_time)
                        continue
                    else:
                        error_message = self._i18n_manager.t(
                            "llm_client.client_error",
                            name=self.name,
                            status_code=response.status_code,
                        )

                        self.console.print(f"[red]{error_message}[/red]")
                        return None

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                error_message = self._i18n_manager.t(
                    "llm_client.network_error_retry",
                    name=self.name,
                    error=str(e),
                    attempt=attempt + 1,
                )

                self.console.print(f"[yellow]{error_message}[/yellow]")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    return None
            except Exception as e:
                error_message = self._i18n_manager.t(
                    "llm_client.request_failed", name=self.name, error=str(e)
                )

                self.console.print(f"[red]{error_message}[/red]")
                return None
        return None
