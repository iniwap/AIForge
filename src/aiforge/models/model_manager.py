import shutil
from pathlib import Path
from typing import Optional


class ModelManager:
    """模型管理器，处理内置模型和在线下载"""

    def __init__(self):
        self.builtin_models = {
            "paraphrase-MiniLM-L6-v2": "sentence_transformers/paraphrase-MiniLM-L6-v2"
        }

    def get_model_path(self, model_name: str) -> Optional[str]:
        """获取模型路径，优先使用内置模型"""
        if model_name in self.builtin_models:
            try:
                # 尝试使用内置模型
                builtin_path = self._get_builtin_model_path(model_name)
                if builtin_path and self._validate_model_files(builtin_path):
                    return str(builtin_path)
            except Exception:
                pass

        # 回退到在线下载（使用默认缓存目录）
        return model_name  # 返回模型名称，让 SentenceTransformer 自行处理

    def _get_builtin_model_path(self, model_name: str) -> Optional[Path]:
        """获取内置模型路径"""
        try:
            import aiforge.models

            model_subpath = self.builtin_models[model_name]

            # 创建临时目录来提取模型文件
            import tempfile

            temp_dir = Path(tempfile.mkdtemp(prefix=f"aiforge_model_{model_name}_"))

            from importlib.resources import files

            models_root = files(aiforge.models)
            model_path = models_root / model_subpath.split("/")[0] / model_subpath.split("/")[-1]

            if model_path.is_dir():
                # 复制整个模型目录
                shutil.copytree(model_path, temp_dir / model_name, dirs_exist_ok=True)
                return temp_dir / model_name

            return None
        except Exception:
            return None

    def _validate_model_files(self, model_path: Path) -> bool:
        """验证模型文件完整性"""
        required_files = [
            "config.json",
            "model.safetensors",
            "tokenizer.json",
            "tokenizer_config.json",
        ]

        return all((model_path / file).exists() for file in required_files)
