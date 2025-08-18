# webview JavaScript-Python 桥接
import json
import time
import threading
from pathlib import Path
from typing import Dict, Any


class WebViewBridge:
    """webview JavaScript-Python 桥接"""

    def __init__(self, engine_manager):
        self.execution_lock = threading.Lock()
        self.current_execution = None
        self.engine_manager = engine_manager
        self.settings_file = str(Path.home() / ".aiforge" / "gui" / "settings.json")
        Path(self.settings_file).parent.mkdir(parents=True, exist_ok=True)

    def get_connection_info(self) -> str:
        """获取连接信息"""
        try:
            info = self.engine_manager.get_connection_info()
            return json.dumps(info)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def execute_instruction(self, instruction: str, options: str = "{}", *args, **kwargs) -> str:
        """执行指令，增加错误处理和状态管理"""
        if not self.engine_manager.is_local_mode():
            return json.dumps({"error": "远程模式请使用 Web API"})

        with self.execution_lock:
            try:
                print(f"🎯 开始执行指令: {instruction}")

                # 获取引擎实例
                engine = self.engine_manager.get_engine()
                if not engine:
                    return json.dumps({"success": False, "error": "引擎未初始化", "data": None})

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
                return json.dumps(
                    {
                        "success": True,
                        "data": result,
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

    def get_system_info(self) -> str:
        """获取系统信息"""
        try:
            if self.engine_manager.is_local_mode():
                engine = self.engine_manager.get_engine()
                if engine and hasattr(engine, "get_system_info"):
                    info = engine.get_system_info()
                    return json.dumps(info)

            return json.dumps(
                {
                    "mode": self.engine_manager.mode.value,
                    "platform": "webview",
                    "features": self.engine_manager._get_supported_features(),
                }
            )

        except Exception as e:
            return json.dumps({"error": str(e)})

    def save_settings(self, settings: str) -> str:
        """保存设置"""
        try:
            # 解析并使用 settings_dict
            settings_dict = json.loads(settings)

            # 验证设置格式
            valid_settings = self._validate_settings(settings_dict)

            # 加载现有设置
            current_settings = self._load_settings_from_file()

            # 合并设置
            current_settings.update(valid_settings)

            # 保存到文件
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(current_settings, f, indent=2, ensure_ascii=False)

            # 应用设置到引擎管理器
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
                self.settings_file.unlink()

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
                    "timestamp": json.dumps({"timestamp": "now"}),  # 可以用实际时间戳
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
