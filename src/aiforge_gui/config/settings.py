# 设置管理
import json
from pathlib import Path
from typing import Dict, Any


class GUISettings:
    """GUI 设置管理器"""

    def __init__(self):
        self.config_dir = Path.home() / ".aiforge" / "gui"
        self.config_file = self.config_dir / "settings.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 默认设置文件路径
        self.default_settings_file = (
            Path(__file__).parent.parent / "resources" / "config" / "default_settings.json"
        )

    def load_settings(self) -> Dict[str, Any]:
        """加载设置"""
        # 首先尝试加载用户设置
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载用户设置失败: {e}")

        # 回退到默认设置文件
        if self.default_settings_file.exists():
            try:
                with open(self.default_settings_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载默认设置失败: {e}")

        # 如果都失败了，抛出错误
        raise FileNotFoundError("无法找到设置文件")

    def save_settings(self, settings: Dict[str, Any]):
        """保存设置"""
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

    def reset_settings(self):
        """重置为默认设置"""
        if self.config_file.exists():
            self.config_file.unlink()
