# 连接配置
import json
from pathlib import Path
from typing import Dict, Any


class ConnectionConfig:
    """连接配置管理器"""

    def __init__(self):
        self.config_dir = Path.home() / ".aiforge" / "gui"
        self.connection_file = self.config_dir / "connections.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 默认连接配置文件
        self.default_connections_file = (
            Path(__file__).parent.parent / "resources" / "config" / "default_connections.json"
        )

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
