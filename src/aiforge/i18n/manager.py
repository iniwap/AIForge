import importlib.resources
import threading
from typing import Dict, Any, Optional, Union
from rich.console import Console
from .formatters.message_formatter import ICUMessageFormatter
from .detector import LocaleDetector
from ..config.config import AIForgeConfig


class GlobalI18nManager:
    """全局国际化管理器，用于部署和系统级功能"""

    _instance = None
    _lock = threading.RLock()
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: AIForgeConfig = None):
        if self._initialized:
            return

        with self._lock:
            if not self._initialized:
                self._manager = AIForgeI18nManager(config, scope="global")
                GlobalI18nManager._initialized = True

    @classmethod
    def get_instance(cls, config: AIForgeConfig = None):
        """获取全局单例实例"""
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    def t(self, key: str, default=None, **params):
        """代理到内部管理器"""
        return self._manager.t(key, default, **params)

    @property
    def locale(self):
        return self._manager.locale

    @property
    def config(self):
        return self._manager.config


class AIForgeI18nManager:
    """国际化管理器"""

    def __init__(self, config: AIForgeConfig = None, scope: str = "session"):
        """
        初始化国际化管理器实例

        Args:
            config: 配置对象
            scope: 作用域，"global" 或 "session"
        """
        self._config = config
        self.scope = scope
        self.console = Console()
        self.locale, self.fallback_locale = self._detect_locale_from_config()
        self.messages: Dict[str, Dict[str, Any]] = {}
        self.formatter = ICUMessageFormatter()
        self._load_all_messages()

    def _update_language(self, language: str):
        """更新语言设置"""
        self.locale = language
        self.fallback_locale = "en"
        self._load_all_messages()

    def _update_config(self, config: AIForgeConfig):
        """更新配置"""
        self._config = config
        self.locale, self.fallback_locale = self._detect_locale_from_config()
        self._load_all_messages()

    def _detect_locale_from_config(self) -> tuple[str, str]:
        # 如果配置中明确指定了locale，直接使用
        if self._config:
            config_locale = self._config.get("locale")
            if config_locale:
                return config_locale, "en"

        # 否则进行自动检测
        env_locale = LocaleDetector.detect_from_env()
        system_locale = LocaleDetector.detect_system_locale()

        detected_locale = env_locale or system_locale or "en"
        return detected_locale, "en"

    @property
    def config(self) -> Optional[AIForgeConfig]:
        """获取配置"""
        return self._config

    @config.setter
    def config(self, value: AIForgeConfig):
        """设置配置"""
        if not isinstance(value, AIForgeConfig):
            raise TypeError("config must be an instance of AIForgeConfig")
        self._update_config(value)

    def t(self, key: str, default=None, **params) -> Union[str, list, dict, int, float, bool]:
        """翻译函数，智能处理不同数据类型"""
        message = self._get_message(key)

        if message is None:
            if default is not None:
                return default
            # 只在翻译失败时输出错误日志
            print(f"[ERROR] Translation failed for key: {key}")
            return key

        # 对于非字符串类型，直接返回原始类型
        if isinstance(message, (list, dict, int, float, bool)):
            return message

        # 只有字符串类型才进行格式化
        if isinstance(message, str):
            return self.formatter.format(message, **params)

        return message

    def _get_message(self, key: str) -> Optional[Union[str, list, dict, int, float, bool]]:
        """获取消息，支持嵌套键和回退，保持原始数据类型"""
        keys = key.split(".")

        # 尝试当前语言
        current = self.messages.get(self.locale, {})
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                break
        else:
            # 直接返回原始类型，不进行转换
            if isinstance(current, (str, list, dict, int, float, bool)):
                return current

        # 回退到默认语言
        current = self.messages.get(self.fallback_locale, {})
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None

        # 直接返回原始类型，不进行转换
        if isinstance(current, (str, list, dict, int, float, bool)):
            return current

        return None

    def _load_all_messages(self):
        """加载所有语言的消息文件"""
        try:
            # 获取 i18n 资源目录
            i18n_package = importlib.resources.files("aiforge.i18n")
            locales_dir = i18n_package / "locales"

            # 加载当前语言的消息
            self._load_locale_messages(locales_dir, self.locale)

            # 如果当前语言不是回退语言，也加载回退语言的消息
            if self.locale != self.fallback_locale:
                self._load_locale_messages(locales_dir, self.fallback_locale)

        except Exception as e:
            # 只在加载失败时输出错误日志
            print(f"[ERROR] Failed to load i18n messages: {str(e)}")
            self._load_default_messages()

    def _load_locale_messages(self, locales_dir, locale: str):
        """加载指定语言的消息文件"""
        import json

        locale_dir = locales_dir / locale
        if not locale_dir.is_dir():
            return

        # 初始化语言消息字典
        if locale not in self.messages:
            self.messages[locale] = {}

        # 加载所有 JSON 文件
        json_files = [
            "common.json",
            "prompts.json",
            "errors.json",
            "ui.json",
            "data.json",
            "keywords.json",
            "deploy.json",
        ]

        for json_file in json_files:
            file_path = locale_dir / json_file
            if file_path.exists():
                try:
                    with file_path.open("r", encoding="utf-8") as f:
                        file_messages = json.load(f)
                        # 使用深度合并而不是简单的update
                        self._deep_merge(self.messages[locale], file_messages)
                except Exception as e:
                    # 只在文件加载失败时输出错误日志
                    print(f"[ERROR] Failed to load {json_file} for locale {locale}: {str(e)}")

    def _deep_merge(self, target: dict, source: dict):
        """深度合并字典，避免覆盖嵌套结构"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                # 递归合并嵌套字典
                self._deep_merge(target[key], value)
            else:
                # 直接赋值
                target[key] = value

    def _load_default_messages(self):
        """加载默认消息（硬编码回退）"""
        self.messages = {
            "zh": {
                "system": {
                    "initializing": "正在初始化...",
                    "ready": "系统就绪",
                    "error": "系统错误",
                },
                "prompts": {
                    "base_role": "你是 AIForge 智能任务分析器",
                    "execution_guidance": "执行代码，并将执行结果赋值给 __result__",
                },
            },
            "en": {
                "system": {
                    "initializing": "Initializing...",
                    "ready": "System ready",
                    "error": "System error",
                },
                "prompts": {
                    "base_role": "You are AIForge intelligent task analyzer",
                    "execution_guidance": "Execute code and assign result to __result__",
                },
            },
        }
