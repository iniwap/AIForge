import os
import platform
from pathlib import Path
from typing import Dict, Any
from PIL import Image, ImageDraw, ImageFont
from aiforge import AIForgePathManager


class ResourceManager:
    """资源管理器 - 直接使用 resources 目录，无需复制"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.resources_dir = self.base_dir / "resources"
        self.static_dir = self.resources_dir / "static"
        self.templates_dir = self.resources_dir / "templates"
        self.icons_dir = self.resources_dir / "icons"

    def setup_resources(self):
        """验证资源文件完整性"""
        self._validate_resources()
        self._setup_icons()  # 新增图标设置

    def _validate_resources(self):
        """验证资源文件完整性"""
        required_files = [
            self.templates_dir / "index.html",
            self.static_dir / "js" / "main.js",
            self.static_dir / "js" / "ui-adapters.js",
            self.static_dir / "js" / "streaming-client.js",
            self.static_dir / "js" / "config-manager.js",
            self.static_dir / "css" / "aiforge.css",
        ]

        missing_files = []
        for file_path in required_files:
            if not file_path.exists():
                missing_files.append(file_path)

        if missing_files:
            raise FileNotFoundError(f"缺少必需的资源文件: {missing_files}")

    def _setup_icons(self):
        """设置图标资源"""

        # 使用安全的目录创建方法
        self.icons_dir = AIForgePathManager.ensure_directory_exists(self.icons_dir)

        # 检查并创建平台特定的图标
        icon_files = {
            "Windows": self.icons_dir / "icon.ico",
            "Darwin": self.icons_dir / "icon.icns",  # macOS
            "Linux": self.icons_dir / "icon.png",
        }

        current_platform = platform.system()
        icon_path = icon_files.get(current_platform, self.icons_dir / "icon.png")

        if not icon_path.exists():
            self._create_default_icon(icon_path)

    def _create_default_icon(self, icon_path: Path):
        """创建默认图标"""
        try:
            # 创建一个带有 AIForge 标识的图标
            size = 256
            image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)

            # 绘制背景圆形
            margin = 20
            draw.ellipse(
                [margin, margin, size - margin, size - margin],
                fill=(0, 100, 200, 255),
                outline=(255, 255, 255, 255),
                width=4,
            )

            # 绘制 "AF" 文字
            try:
                font_size = size // 4
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

            text = "AF"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            x = (size - text_width) // 2
            y = (size - text_height) // 2

            draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

            # 保存图标
            if icon_path.suffix == ".ico":
                # Windows ICO 格式
                image.save(
                    icon_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)]
                )
            else:
                # PNG 格式
                image.save(icon_path, format="PNG")

            print(f"✅ 创建默认图标: {icon_path}")

        except Exception as e:
            print(f"⚠️ 创建默认图标失败: {e}")

    def get_icon_path(self) -> Path:
        """获取当前平台的图标路径"""
        icon_files = {
            "Windows": self.icons_dir / "icon.ico",
            "Darwin": self.icons_dir / "icon.icns",
            "Linux": self.icons_dir / "icon.png",
        }

        current_platform = platform.system()
        return icon_files.get(current_platform, self.icons_dir / "icon.png")

    def get_static_dir(self) -> Path:
        """获取静态文件目录"""
        return self.static_dir

    def get_templates_dir(self) -> Path:
        """获取模板目录"""
        return self.templates_dir

    def get_resource_content(self, resource_path: str) -> str:
        """读取资源文件内容"""
        file_path = self.resources_dir / resource_path
        if not file_path.exists():
            raise FileNotFoundError(f"资源文件不存在: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def list_resources(self) -> Dict[str, Any]:
        """列出所有资源文件"""
        resources = {}

        for root, dirs, files in os.walk(self.resources_dir):
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.resources_dir)
                resources[str(relative_path)] = {
                    "size": file_path.stat().st_size,
                    "modified": file_path.stat().st_mtime,
                }

        return resources
