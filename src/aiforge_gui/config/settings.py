# 设置管理
import json
from pathlib import Path
from typing import Dict, Any
from aiforge import AIForgePathManager


class GUISettings:
    """GUI 设置管理器"""

    def __init__(self):

        # 使用标准的配置目录
        self.config_dir = AIForgePathManager.get_config_dir() / "gui"
        self.config_file = self.config_dir / "settings.json"

        # 确保目录存在
        AIForgePathManager.ensure_directory_exists(self.config_dir)

        # 默认设置文件 - 需要处理打包应用的资源访问
        if AIForgePathManager.is_development_environment():
            self.default_settings_file = (
                Path(__file__).parent.parent / "resources" / "config" / "default_settings.json"
            )
        else:
            # 打包应用中的资源文件处理
            # 可能需要从用户配置目录复制默认设置
            self.default_settings_file = self.config_dir / "default_settings.json"

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
