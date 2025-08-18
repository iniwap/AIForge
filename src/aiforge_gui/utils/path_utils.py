# 路径工具
from pathlib import Path
from typing import Union


class PathUtils:
    """路径工具类"""

    @staticmethod
    def get_project_root() -> Path:
        """获取项目根目录"""
        return Path(__file__).parent.parent

    @staticmethod
    def get_web_dir() -> Path:
        """获取 Web 资源目录"""
        return PathUtils.get_project_root() / "web"

    @staticmethod
    def get_resources_dir() -> Path:
        """获取资源模板目录"""
        return PathUtils.get_project_root() / "resources"

    @staticmethod
    def get_config_dir() -> Path:
        """获取用户配置目录"""
        return Path.home() / ".aiforge" / "gui"

    @staticmethod
    def ensure_dir(path: Union[str, Path]) -> Path:
        """确保目录存在"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def resolve_resource_path(resource_path: str) -> Path:
        """解析资源文件路径"""
        resources_dir = PathUtils.get_resources_dir()
        return resources_dir / resource_path

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """验证 URL 格式"""
        return url.startswith(("http://", "https://"))
