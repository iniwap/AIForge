import tomlkit
from pathlib import Path
from rich.console import Console
from typing import Dict, Any
import importlib.resources
from ..core.path_manager import AIForgePathManager


class AIForgeConfig:
    """AIForge配置管理器"""

    def __init__(self, config_file: str | None = None, components: Dict[str, Any] = None):
        self.console = Console()

        if config_file:
            self.config_file = Path(config_file)
            self.config = self._load_from_file()
        else:
            self.config_file = None
            self.config = {}

    @classmethod
    def from_dict(cls, config_dict: Dict) -> "AIForgeConfig":
        """从字典创建配置实例"""
        instance = cls()
        instance.config = config_dict
        return instance

    @classmethod
    def from_api_key(cls, api_key: str, provider: str = "openrouter", **kwargs) -> "AIForgeConfig":
        """从API key快速创建配置"""
        default_config = cls.get_builtin_default_config()

        # 设置API key
        if provider in default_config.get("llm", {}):
            default_config["llm"][provider]["api_key"] = api_key
            default_config["default_llm_provider"] = provider

        # 应用所有核心参数
        core_params = ["max_rounds", "max_tokens", "max_optimization_attempts", "locale"]

        for key, value in kwargs.items():
            if key in core_params:
                default_config[key] = value
            elif key.startswith("cache_"):
                # 处理缓存相关参数
                cache_key = key.replace("cache_", "")
                if "cache" not in default_config:
                    default_config["cache"] = {}
                if "code" not in default_config["cache"]:
                    default_config["cache"]["code"] = {}
                default_config["cache"]["code"][cache_key] = value
            elif key.startswith("security_"):
                # 处理安全相关参数
                security_key = key.replace("security_", "")
                if "security" not in default_config:
                    default_config["security"] = {}
                default_config["security"][security_key] = value
            elif key.startswith("optimization_"):
                # 处理优化相关参数
                opt_key = key.replace("optimization_", "")
                if "optimization" not in default_config:
                    default_config["optimization"] = {}
                default_config["optimization"][opt_key] = value

        return cls.from_dict(default_config)

    def _load_from_file(self) -> Dict:
        """从文件加载配置"""
        # 总是从默认配置开始
        config = self.get_builtin_default_config()

        if not self.config_file.exists():
            self.console.print(
                f"[yellow]Configuration file not found: {self.config_file}, using defaults[/yellow]"
            )
            return config

        try:
            with open(self.config_file, "rb") as f:
                file_config = tomlkit.load(f)
            # 深度合并配置
            self._deep_merge_dict(config, file_config)
            return config
        except Exception as e:
            self.console.print(f"[red]Failed to load configuration: {str(e)}[/red]")
            return config

    def _deep_merge_dict(self, base_dict: dict, update_dict: dict):
        """深度合并字典"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_merge_dict(base_dict[key], value)
            else:
                base_dict[key] = value

    @staticmethod
    def get_builtin_default_config() -> Dict:
        """获取内置默认配置"""
        if not hasattr(AIForgeConfig, "_cached_default_config"):
            try:
                with (
                    importlib.resources.files("aiforge.config")
                    .joinpath("default.toml")
                    .open(mode="r", encoding="utf-8") as f
                ):
                    AIForgeConfig._cached_default_config = tomlkit.load(f)
            except Exception:
                AIForgeConfig._cached_default_config = {
                    "max_tokens": 4096,
                    "max_rounds": 5,
                    "default_llm_provider": "openrouter",
                    "llm": {
                        "openrouter": {
                            "type": "openai",
                            "model": "deepseek/deepseek-chat-v3-0324:free",
                            "api_key": "",
                            "base_url": "https://openrouter.ai/api/v1",
                            "timeout": 30,
                            "max_tokens": 8192,
                        },
                        "deepseek": {
                            "type": "deepseek",
                            "model": "deepseek-chat",
                            "api_key": "",
                            "base_url": "https://api.deepseek.com",
                            "timeout": 30,
                            "max_tokens": 8192,
                        },
                        "ollama": {
                            "type": "ollama",
                            "model": "llama3",
                            "api_key": "",
                            "base_url": "http://localhost:11434",
                            "timeout": 30,
                            "max_tokens": 8192,
                        },
                    },
                    "cache": {
                        "code": {
                            "enabled": True,
                            "max_modules": 20,
                            "failure_threshold": 0.8,
                            "max_age_days": 30,
                            "cleanup_interval": 10,
                            "semantic_threshold": 0.6,
                            "enable_semantic_matching": True,
                        }
                    },
                    "optimization": {
                        "enabled": False,
                        "aggressive_minify": False,
                        "max_feedback_length": 200,
                        "obfuscate_variables": True,
                    },
                    "security": {
                        "execution_timeout": 30,
                        "memory_limit_mb": 512,
                        "cpu_time_limit": 30,
                        "file_descriptor_limit": 64,
                        "max_file_size_mb": 10,
                        "max_processes": 10,
                        "file_access": {
                            "user_specified_paths": True,
                            "default_allowed_paths": ["./data", "./output"],
                            "require_explicit_permission": True,
                            "max_allowed_paths": 10,
                        },
                        "network": {
                            "policy": "filtered",
                            "max_requests_per_minute": 60,
                            "max_concurrent_connections": 10,
                            "request_timeout": 30,
                            "allowed_protocols": ["http", "https"],
                            "allowed_ports": [80, 443, 8080, 8443],
                            "blocked_ports": [22, 23, 3389, 5432, 3306],
                            "generated_code": {
                                "force_block_modules": False,
                                "force_block_access": False,
                            },
                            "domain_filtering": {
                                "enabled": True,
                                "whitelist": [
                                    "api.openai.com",
                                    "api.deepseek.com",
                                    "openrouter.ai",
                                    "baidu.com",
                                    "bing.com",
                                    "so.com",
                                    "sogou.com",
                                    "api.x.ai",
                                    "dashscope.aliyuncs.com",
                                    "generativelanguage.googleapis.com",
                                ],
                                "blacklist": ["malicious-site.com"],
                                "task_overrides": {
                                    "data_fetch": {
                                        "mode": "extended",
                                        "additional_domains": [
                                            "sina.com.cn",
                                            "163.com",
                                            "qq.com",
                                            "sohu.com",
                                            "xinhuanet.com",
                                            "people.com.cn",
                                            "chinanews.com",
                                            "thepaper.cn",
                                            "36kr.com",
                                            "ifeng.com",
                                            "cnbeta.com",
                                            "zol.com.cn",
                                            "csdn.net",
                                            "jianshu.com",
                                            "zhihu.com",
                                            "weibo.com",
                                            "douban.com",
                                            "bilibili.com",
                                            "youku.com",
                                            "iqiyi.com",
                                            "tencent.com",
                                            "alibaba.com",
                                            "jd.com",
                                            "tmall.com",
                                            "taobao.com",
                                        ],
                                    }
                                },
                            },
                        },
                    },
                }

        return AIForgeConfig._cached_default_config.copy()  # 返回副本避免修改

    def get_max_tokens(self):
        """获取最大token数"""
        return self.config.get("max_tokens", 4096)

    def get_max_rounds(self):
        """获取最大尝试次数"""
        return self.config.get("max_rounds", 5)

    def get_cache_config(self, cache_type):
        """获取缓存配置"""
        return self.config.get("cache", {}).get(cache_type, {})

    def get_default_llm_provider(self) -> str:
        """获取默认LLM提供商"""
        return self.config.get("default_llm_provider", "")

    def get_optimization_config(self) -> Dict:
        """获取优化配置"""
        return self.config.get("optimization", {})

    def get_max_optimization_attempts(self):
        """获取单轮最大优化次数"""
        return self.config.get("max_optimization_attempts", 3)

    def get(self, key: str, default=None):
        """获取配置值"""
        return self.config.get(key, default)

    def update(self, new_config: Dict):
        """更新配置"""
        self.config.update(new_config)

    def save_to_file(self, file_path: str):
        """保存配置到文件"""
        # 将配置转换为TOML字符串
        toml_content = tomlkit.dumps(self.config)

        # 使用安全的文件写入方法
        AIForgePathManager.safe_write_file(Path(file_path), toml_content, fallback_dir="config")

    def get_security_config(self):
        return self.config.get("security", {})

    def get_security_file_access_config(self):
        sc = self.get_security_config()
        if sc:
            return sc.get("file_access", {})
        else:
            return {}

    def get_security_network_config(self):
        """获取统一的网络安全配置"""
        sc = self.get_security_config()
        if sc:
            return sc.get("network", {})
        return {}

    def get_domain_filtering_config(self):
        """获取域名过滤配置"""
        network_config = self.get_security_network_config()
        return network_config.get("domain_filtering", {})

    def get_generated_code_network_config(self):
        """获取生成代码网络配置"""
        network_config = self.get_security_network_config()
        return network_config.get("generated_code", {})

    def get_network_policy_config(
        self, context: str = "execution", task_type: str = None
    ) -> Dict[str, Any]:
        base_config = self.get_security_network_config()
        policy_level = base_config.get("policy", "filtered")

        # 构建策略配置
        policy_config = {
            "policy_level": policy_level,
            "max_requests_per_minute": base_config.get("max_requests_per_minute", 60),
            "max_concurrent_connections": base_config.get("max_concurrent_connections", 10),
            "request_timeout": base_config.get("request_timeout", 30),
            "allowed_protocols": base_config.get("allowed_protocols", ["http", "https"]),
            "allowed_ports": base_config.get("allowed_ports", [80, 443, 8080, 8443]),
            "blocked_ports": base_config.get("blocked_ports", [22, 23, 3389, 5432, 3306]),
        }

        # 生成代码专用控制
        if context == "execution":
            generated_code_config = base_config.get("generated_code", {})
            policy_config.update(
                {
                    "force_block_modules": generated_code_config.get("force_block_modules", False),
                    "force_block_access": generated_code_config.get("force_block_access", False),
                }
            )

        # 域名过滤配置
        domain_filtering = base_config.get("domain_filtering", {})
        if domain_filtering.get("enabled", True):
            whitelist = domain_filtering.get("whitelist", [])

            # 任务特定域名扩展
            if task_type:
                task_overrides = domain_filtering.get("task_overrides", {}).get(task_type, {})
                if task_overrides.get("mode") == "extended":
                    whitelist = whitelist + task_overrides.get("additional_domains", [])

            policy_config.update(
                {
                    "domain_filtering_enabled": True,
                    "domain_whitelist": whitelist,
                    "domain_blacklist": domain_filtering.get("blacklist", []),
                }
            )
        else:
            policy_config["domain_filtering_enabled"] = False

        return policy_config
