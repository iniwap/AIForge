import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from aiforge import AIForgePathManager


class WebViewBridge:
    def __init__(self, engine_manager):
        self.execution_lock = threading.Lock()
        self.current_execution = None
        self.engine_manager = engine_manager
        self.settings_file = str(AIForgePathManager.get_config_dir() / "gui" / "settings.json")
        AIForgePathManager.ensure_directory_exists(Path(self.settings_file).parent)

    def execute_instruction(self, instruction: str, options: str = "{}", *args, **kwargs) -> str:
        """执行指令，支持延迟初始化和API密钥检查"""
        if not self.engine_manager.is_local_mode():
            return json.dumps({"error": "远程模式请使用 Web API"})

        with self.execution_lock:
            try:
                print(f"🎯 开始执行指令: {instruction}")

                # 检查API密钥
                if not self.engine_manager.has_valid_api_key():
                    return json.dumps(
                        {
                            "success": False,
                            "error": "未配置API密钥，请先在配置中设置",
                            "data": None,
                            "requires_config": True,
                        }
                    )

                # 获取引擎实例（延迟初始化）
                try:
                    engine = self.engine_manager.get_engine()
                    if not engine:
                        return json.dumps(
                            {"success": False, "error": "引擎初始化失败", "data": None}
                        )
                except RuntimeError as e:
                    return json.dumps(
                        {"success": False, "error": str(e), "data": None, "requires_config": True}
                    )

                # 设置执行状态
                self.current_execution = {
                    "instruction": instruction,
                    "start_time": time.time(),
                    "status": "running",
                }

                # 使用引擎的run方法执行指令
                result = engine.run(instruction)

                # 更新执行状态
                self.current_execution["status"] = "completed"
                self.current_execution["end_time"] = time.time()

                print("✅ 指令执行完成")
                adapted_result = engine.adapt_result_for_ui(
                    result, "editor" if result.task_type == "content_generation" else None, "gui"
                )
                return json.dumps(
                    {
                        "success": True,
                        "data": adapted_result,
                        "execution_time": self.current_execution["end_time"]
                        - self.current_execution["start_time"],
                    }
                )

            except Exception as e:
                print(f"❌ 指令执行失败: {e}")
                import traceback

                traceback.print_exc()

                if self.current_execution:
                    self.current_execution["status"] = "failed"
                    self.current_execution["error"] = str(e)

                return json.dumps({"success": False, "error": str(e), "data": None})
            finally:
                # 清理执行状态
                if self.current_execution and self.current_execution.get("status") != "running":
                    self.current_execution = None

    def get_connection_info(self) -> str:
        """获取连接信息"""
        try:
            info = self.engine_manager.get_connection_info()
            return json.dumps(info)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def get_config_info(self) -> str:
        """获取当前配置信息"""
        try:
            config_info = {
                "mode": self.engine_manager.mode.value,
                "has_local_engine": self.engine_manager.mode.value == "local",
                "has_remote_url": bool(self.engine_manager.config.get("remote_url")),
                "current_config": {
                    "provider": self.engine_manager.config.get("provider", "openrouter"),
                    "locale": self.engine_manager.config.get("locale", "zh"),
                    "has_api_key": self.engine_manager.has_valid_api_key(),
                    "max_rounds": self.engine_manager.config.get("max_rounds", 2),
                    "max_tokens": self.engine_manager.config.get("max_tokens", 4096),
                },
                "api_server_url": self._get_api_server_url(),
            }
            return json.dumps(config_info)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _get_current_api_key(self) -> Optional[str]:
        """获取当前API密钥（优先级：配置 > 环境变量）"""
        return self.engine_manager._get_current_api_key()

    def _get_api_server_url(self) -> Optional[str]:
        """获取本地API服务器URL"""
        if hasattr(self.engine_manager, "_api_server") and self.engine_manager._api_server:
            api_server = self.engine_manager._api_server
            if hasattr(api_server, "port") and api_server.port:
                return f"http://127.0.0.1:{api_server.port}"
        return None

    def update_config(self, config_json: str) -> str:
        """更新配置"""
        try:
            config_data = json.loads(config_json)

            # 验证配置数据
            valid_providers = [
                "openrouter",
                "deepseek",
                "ollama",
                "grok",
                "qwen",
                "gemini",
                "claude",
                "cohere",
                "mistral",
            ]
            valid_locales = ["zh", "en", "ja", "ko", "fr", "de", "es", "pt", "ru", "ar", "hi", "vi"]

            if config_data.get("provider") and config_data["provider"] not in valid_providers:
                return json.dumps(
                    {"success": False, "error": f"Invalid provider: {config_data['provider']}"}
                )

            if config_data.get("locale") and config_data["locale"] not in valid_locales:
                return json.dumps(
                    {"success": False, "error": f"Invalid locale: {config_data['locale']}"}
                )

            # 更新引擎管理器配置
            old_config = self.engine_manager.config.copy()

            # 更新基础配置
            if "provider" in config_data:
                self.engine_manager.config["provider"] = config_data["provider"]
            if "locale" in config_data:
                self.engine_manager.config["locale"] = config_data["locale"]
            if "api_key" in config_data and config_data["api_key"]:
                self.engine_manager.config["api_key"] = config_data["api_key"]
            if "max_rounds" in config_data:
                self.engine_manager.config["max_rounds"] = int(config_data["max_rounds"])
            if "max_tokens" in config_data:
                self.engine_manager.config["max_tokens"] = int(config_data["max_tokens"])

            # 如果是本地模式且关键配置发生变化，重新初始化引擎
            if self.engine_manager.is_local_mode() and self._config_requires_engine_restart(
                old_config, self.engine_manager.config
            ):
                self.engine_manager._initialize_local_engine()

            # 保存配置到文件（不包含API密钥）
            self._save_persistent_config()

            return json.dumps(
                {
                    "success": True,
                    "message": "配置已更新",
                    "mode": self.engine_manager.mode.value,
                    "requires_restart": self._config_requires_engine_restart(
                        old_config, self.engine_manager.config
                    ),
                }
            )

        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def _config_requires_engine_restart(self, old_config: Dict, new_config: Dict) -> bool:
        """检查配置变化是否需要重启引擎"""
        restart_keys = ["api_key", "provider", "max_rounds", "max_tokens"]
        for key in restart_keys:
            if old_config.get(key) != new_config.get(key):
                return True
        return False

    def _save_persistent_config(self):
        """保存持久化配置（不包含敏感信息）"""
        try:
            persistent_config = {
                "provider": self.engine_manager.config.get("provider", "openrouter"),
                "locale": self.engine_manager.config.get("locale", "zh"),
                "max_rounds": self.engine_manager.config.get("max_rounds", 2),
                "max_tokens": self.engine_manager.config.get("max_tokens", 4096),
                "last_updated": time.time(),
            }

            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(persistent_config, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"Failed to save persistent config: {e}")

    def load_persistent_config(self) -> Dict[str, Any]:
        """加载持久化配置"""
        try:
            if Path(self.settings_file).exists():
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Failed to load persistent config: {e}")

        return {"provider": "openrouter", "locale": "zh", "max_rounds": 2, "max_tokens": 4096}

    def check_api_key_status(self) -> str:
        """检查API密钥状态"""
        try:
            has_api_key = self.engine_manager.has_valid_api_key()
            return json.dumps(
                {
                    "has_api_key": has_api_key,
                    "provider": self.engine_manager.config.get("provider", "openrouter"),
                    "mode": self.engine_manager.mode.value,
                }
            )
        except Exception as e:
            return json.dumps({"error": str(e)})

    def get_system_info(self) -> str:
        """获取系统信息"""
        try:
            if self.engine_manager.is_local_mode():
                try:
                    engine = self.engine_manager.get_engine()
                    if engine and hasattr(engine, "get_system_info"):
                        info = engine.get_system_info()
                        return json.dumps(info)
                except RuntimeError:
                    # 引擎未初始化（可能缺少API密钥），继续返回基本信息
                    pass

            return json.dumps(
                {
                    "mode": self.engine_manager.mode.value,
                    "platform": "webview",
                    "features": self.engine_manager._get_supported_features(),
                }
            )

        except Exception as e:
            return json.dumps({"error": str(e)})

    # 保留原有的设置管理方法
    def save_settings(self, settings: str) -> str:
        """保存设置"""
        try:
            settings_dict = json.loads(settings)
            valid_settings = self._validate_settings(settings_dict)
            current_settings = self._load_settings_from_file()
            current_settings.update(valid_settings)

            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(current_settings, f, indent=2, ensure_ascii=False)

            self._apply_settings_to_engine(current_settings)

            return json.dumps(
                {"success": True, "message": "设置已保存", "settings": current_settings}
            )

        except Exception as e:
            return json.dumps({"error": f"保存设置失败: {str(e)}"})

    def load_settings(self) -> str:
        """加载设置"""
        try:
            settings = self._load_settings_from_file()
            return json.dumps(settings)
        except Exception as e:
            return json.dumps({"error": f"加载设置失败: {str(e)}"})

    def _validate_settings(self, settings_dict: Dict[str, Any]) -> Dict[str, Any]:
        """验证设置格式"""
        valid_settings = {}

        # 主题设置
        if "theme" in settings_dict and settings_dict["theme"] in ["dark", "light"]:
            valid_settings["theme"] = settings_dict["theme"]

        # 语言设置
        if "language" in settings_dict and settings_dict["language"] in ["zh", "en"]:
            valid_settings["language"] = settings_dict["language"]

        # 进度显示级别
        if "progressLevel" in settings_dict and settings_dict["progressLevel"] in [
            "detailed",
            "minimal",
            "none",
        ]:
            valid_settings["progressLevel"] = settings_dict["progressLevel"]

        # 最大执行轮数
        if "maxRounds" in settings_dict:
            try:
                max_rounds = int(settings_dict["maxRounds"])
                if 1 <= max_rounds <= 20:
                    valid_settings["maxRounds"] = max_rounds
            except (ValueError, TypeError):
                pass

        # 远程服务器地址
        if "remoteUrl" in settings_dict:
            remote_url = str(settings_dict["remoteUrl"]).strip()
            if remote_url:
                valid_settings["remoteUrl"] = remote_url

        # 窗口设置
        if "windowWidth" in settings_dict:
            try:
                width = int(settings_dict["windowWidth"])
                if 800 <= width <= 3840:
                    valid_settings["windowWidth"] = width
            except (ValueError, TypeError):
                pass

        if "windowHeight" in settings_dict:
            try:
                height = int(settings_dict["windowHeight"])
                if 600 <= height <= 2160:
                    valid_settings["windowHeight"] = height
            except (ValueError, TypeError):
                pass

        return valid_settings

    def _load_settings_from_file(self) -> Dict[str, Any]:
        """从文件加载设置"""
        default_settings = {
            "theme": "dark",
            "language": "zh",
            "progressLevel": "detailed",
            "maxRounds": 5,
            "remoteUrl": "",
            "windowWidth": 1200,
            "windowHeight": 800,
        }

        if Path(self.settings_file).exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    saved_settings = json.load(f)
                    # 合并默认设置和保存的设置
                    default_settings.update(saved_settings)
            except Exception as e:
                print(f"加载设置文件失败: {e}")

        return default_settings

    def _apply_settings_to_engine(self, settings: Dict[str, Any]):
        """将设置应用到引擎管理器"""
        try:
            if self.engine_manager.is_local_mode():
                engine = self.engine_manager.get_engine()
                if engine and hasattr(engine, "update_settings"):
                    # 提取引擎相关设置
                    engine_settings = {
                        "language": settings.get("language", "zh"),
                        "max_rounds": settings.get("maxRounds", 5),
                        "progress_level": settings.get("progressLevel", "detailed"),
                    }
                    engine.update_settings(engine_settings)
        except Exception as e:
            print(f"应用设置到引擎失败: {e}")

    def reset_settings(self) -> str:
        """重置设置为默认值"""
        try:
            if Path(self.settings_file).exists():
                Path(self.settings_file).unlink()

            default_settings = self._load_settings_from_file()
            return json.dumps(
                {"success": True, "message": "设置已重置为默认值", "settings": default_settings}
            )
        except Exception as e:
            return json.dumps({"error": f"重置设置失败: {str(e)}"})

    def export_settings(self) -> str:
        """导出设置"""
        try:
            settings = self._load_settings_from_file()
            return json.dumps(
                {
                    "success": True,
                    "settings": settings,
                    "timestamp": time.time(),
                }
            )
        except Exception as e:
            return json.dumps({"error": f"导出设置失败: {str(e)}"})

    def import_settings(self, settings_data: str) -> str:
        """导入设置"""
        try:
            import_data = json.loads(settings_data)

            if "settings" in import_data:
                settings_dict = import_data["settings"]
                valid_settings = self._validate_settings(settings_dict)

                # 保存导入的设置
                with open(self.settings_file, "w", encoding="utf-8") as f:
                    json.dump(valid_settings, f, indent=2, ensure_ascii=False)

                # 应用设置
                self._apply_settings_to_engine(valid_settings)

                return json.dumps(
                    {"success": True, "message": "设置导入成功", "settings": valid_settings}
                )
            else:
                return json.dumps({"error": "无效的设置数据格式"})

        except Exception as e:
            return json.dumps({"error": f"导入设置失败: {str(e)}"})
