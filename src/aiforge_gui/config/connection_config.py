# 连接配置
import json
from pathlib import Path
from typing import Dict, Any
from aiforge import AIForgePathManager


class ConnectionConfig:
    """连接配置管理器"""

    def __init__(self):
        # 使用标准的配置目录
        self.config_dir = AIForgePathManager.get_config_dir() / "gui"
        self.connection_file = self.config_dir / "connections.json"

        # 确保目录存在
        AIForgePathManager.ensure_directory_exists(self.config_dir)

        # 默认连接配置文件 - 需要处理打包应用的资源访问
        if AIForgePathManager.is_development_environment():
            self.default_connections_file = (
                Path(__file__).parent.parent / "resources" / "config" / "default_connections.json"
            )
        else:
            # 打包应用中的资源文件处理
            # 可能需要从用户配置目录复制默认配置
            self.default_connections_file = self.config_dir / "default_connections.json"

    def load_connections(self) -> Dict[str, Any]:
        """加载连接配置"""
        if self.connection_file.exists():
            try:
                with open(self.connection_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载连接配置失败: {e}")

        # 回退到默认连接配置
        if self.default_connections_file.exists():
            try:
                with open(self.default_connections_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载默认连接配置失败: {e}")

        raise FileNotFoundError("无法找到连接配置文件")

    def save_connections(self, connections: Dict[str, Any]):
        """保存连接配置"""
        with open(self.connection_file, "w", encoding="utf-8") as f:
            json.dump(connections, f, indent=2, ensure_ascii=False)
