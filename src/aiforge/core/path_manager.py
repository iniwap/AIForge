import os
import sys
import platform
from pathlib import Path


class AIForgePathManager:
    """AIForge跨平台路径管理器，确保所有写入操作使用正确的可写目录"""

    @staticmethod
    def is_development_environment() -> bool:
        """检测是否在开发环境"""
        # 首先检查是否为打包版本
        if getattr(sys, "frozen", None):
            return False

        # 然后检查文件系统结构
        current_dir = Path.cwd()
        return (
            (current_dir / "src" / "aiforge").exists()
            and (current_dir / "pyproject.toml").exists()
            and (current_dir / ".git").exists()
        )

    @staticmethod
    def is_docker_environment() -> bool:
        """检测是否在Docker环境中运行"""
        return os.path.exists("/.dockerenv") or os.environ.get("AIFORGE_DOCKER_MODE") == "true"

    @staticmethod
    def get_app_data_dir() -> Path:
        """获取应用数据目录"""
        # 开发模式：使用项目根目录
        if AIForgePathManager.is_development_environment():
            return Path.cwd()

        # Docker环境：使用容器内路径
        if AIForgePathManager.is_docker_environment():
            return Path("/app")

        # 发布模式：使用系统标准目录
        system = platform.system()
        if system == "Darwin":  # macOS
            return Path.home() / "Library" / "Application Support" / "AIForge"
        elif system == "Windows":
            appdata = os.environ.get("APPDATA")
            if appdata:
                return Path(appdata) / "AIForge"
            return Path.home() / "AppData" / "Roaming" / "AIForge"
        else:  # Linux/Unix
            xdg_data = os.environ.get("XDG_DATA_HOME")
            if xdg_data:
                return Path(xdg_data) / "aiforge"
            return Path.home() / ".local" / "share" / "aiforge"

    @staticmethod
    def get_config_dir() -> Path:
        """获取配置文件目录"""
        if AIForgePathManager.is_development_environment():
            return Path.cwd() / "config"

        if AIForgePathManager.is_docker_environment():
            return Path(os.environ.get("AIFORGE_CONFIG_DIR", "/app/config"))

        # 发布模式：使用系统标准配置目录
        system = platform.system()
        if system == "Darwin":  # macOS
            config_dir = Path.home() / "Library" / "Preferences" / "AIForge"
        elif system == "Windows":
            appdata = os.environ.get("APPDATA")
            if appdata:
                config_dir = Path(appdata) / "AIForge"
            else:
                config_dir = Path.home() / "AppData" / "Roaming" / "AIForge"
        else:  # Linux
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config:
                config_dir = Path(xdg_config) / "aiforge"
            else:
                config_dir = Path.home() / ".config" / "aiforge"

        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    @staticmethod
    def get_cache_dir() -> Path:
        """获取缓存目录"""
        if AIForgePathManager.is_development_environment():
            cache_dir = Path.cwd() / "cache"
        elif AIForgePathManager.is_docker_environment():
            cache_dir = Path("/app/cache")
        else:
            # 发布模式：使用系统标准缓存目录
            system = platform.system()
            if system == "Darwin":  # macOS
                cache_dir = Path.home() / "Library" / "Caches" / "AIForge"
            elif system == "Windows":
                localappdata = os.environ.get("LOCALAPPDATA")
                if localappdata:
                    cache_dir = Path(localappdata) / "AIForge" / "Cache"
                else:
                    cache_dir = Path.home() / "AppData" / "Local" / "AIForge" / "Cache"
            else:  # Linux
                xdg_cache = os.environ.get("XDG_CACHE_HOME")
                if xdg_cache:
                    cache_dir = Path(xdg_cache) / "aiforge"
                else:
                    cache_dir = Path.home() / ".cache" / "aiforge"

        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @staticmethod
    def get_safe_workdir(workdir_name: str = "aiforge_work") -> Path:
        """获取安全的工作目录"""
        base_dir = AIForgePathManager.get_app_data_dir()
        workdir = base_dir / workdir_name

        try:
            workdir.mkdir(parents=True, exist_ok=True)
            # 测试写入权限
            test_file = workdir / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            return workdir
        except (PermissionError, OSError):
            # 使用临时目录作为最后备选
            import tempfile

            temp_dir = Path(tempfile.gettempdir()) / "aiforge_work"
            temp_dir.mkdir(parents=True, exist_ok=True)
            return temp_dir

    @staticmethod
    def get_temp_dir() -> Path:
        """获取临时文件目录"""
        workdir = AIForgePathManager.get_safe_workdir()
        temp_dir = workdir / "tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    @staticmethod
    def get_backup_dir() -> Path:
        """获取备份目录"""
        base_dir = AIForgePathManager.get_app_data_dir()
        backup_dir = base_dir / "backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    @staticmethod
    def get_log_dir() -> Path:
        """获取日志目录"""
        base_dir = AIForgePathManager.get_app_data_dir()
        log_dir = base_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    @staticmethod
    def safe_write_file(file_path: Path, content: str, fallback_dir: str = "files") -> Path:
        """安全写入文件，失败时使用备选目录"""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return file_path
        except (PermissionError, OSError):
            safe_base = AIForgePathManager.get_app_data_dir()
            safe_dir = safe_base / fallback_dir
            safe_dir.mkdir(parents=True, exist_ok=True)
            safe_file = safe_dir / file_path.name
            safe_file.write_text(content, encoding="utf-8")
            return safe_file

    @staticmethod
    def is_writable(path: Path) -> bool:
        """检查路径是否可写"""
        try:
            test_file = path / ".write_test"
            test_file.touch()
            test_file.unlink()
            return True
        except (OSError, PermissionError):
            return False

    @staticmethod
    def ensure_directory_exists(path: Path) -> Path:
        """确保目录存在，如果不存在则创建"""
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except (PermissionError, OSError):
            # 权限不足时使用安全目录
            safe_base = AIForgePathManager.get_app_data_dir()
            fallback_path = safe_base / path.name
            fallback_path.mkdir(parents=True, exist_ok=True)
            return fallback_path
