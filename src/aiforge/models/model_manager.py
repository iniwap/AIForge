import shutil
import threading
from pathlib import Path
from typing import Optional


class ModelManager:
    """模型管理器，根据配置自动选择轻量级或标准模式"""

    _instance = None
    _loaded_models = {}
    _lightweight_models = {}
    _lock = threading.RLock()
    _config = None

    def __init__(self):
        self.builtin_models = {
            "paraphrase-MiniLM-L6-v2": "sentence_transformers/paraphrase-MiniLM-L6-v2"
        }

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def set_config(self, config):
        """设置配置对象"""
        self._config = config

    def get_semantic_model(self, model_name: str = "paraphrase-MiniLM-L6-v2"):
        """获取语义模型，自动根据配置选择轻量级或标准模式"""
        # 自动从配置中判断是否使用轻量级模式
        use_lightweight = self._should_use_lightweight()

        if use_lightweight:
            return self._get_lightweight_model(model_name)
        else:
            return self._get_standard_model(model_name)

    def _should_use_lightweight(self) -> bool:
        """根据配置判断是否使用轻量级模式"""
        if self._config is None:
            return True  # 默认使用轻量级

        # 从配置中读取轻量级设置
        return self._config.get("cache", {}).get("use_lightweight_semantic", True)

    def _get_standard_model(self, model_name: str):
        """获取标准语义模型"""
        if model_name not in self._loaded_models:
            with self._lock:
                if model_name not in self._loaded_models:
                    model_path = self.get_model_path(model_name)
                    from sentence_transformers import SentenceTransformer

                    self._loaded_models[model_name] = SentenceTransformer(
                        model_path, tokenizer_kwargs={"clean_up_tokenization_spaces": True}
                    )
        return self._loaded_models[model_name]

    def _get_lightweight_model(self, model_name: str):
        """获取轻量级语义模型"""
        if model_name not in self._lightweight_models:
            with self._lock:
                if model_name not in self._lightweight_models:
                    lightweight_model = {"tfidf": None, "fitted": False, "type": "lightweight"}
                    self._lightweight_models[model_name] = lightweight_model
        return self._lightweight_models[model_name]

    def get_tfidf_vectorizer(self, model_name: str = "paraphrase-MiniLM-L6-v2"):
        """获取TF-IDF向量化器（仅轻量级模式可用）"""
        if not self._should_use_lightweight():
            return None

        lightweight_model = self._get_lightweight_model(model_name)
        if lightweight_model["tfidf"] is None:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer

                lightweight_model["tfidf"] = TfidfVectorizer(
                    max_features=1000, stop_words="english", ngram_range=(1, 2)
                )
            except ImportError:
                return None
        return lightweight_model["tfidf"]

    def is_tfidf_fitted(self, model_name: str = "paraphrase-MiniLM-L6-v2") -> bool:
        """检查TF-IDF是否已训练"""
        if not self._should_use_lightweight():
            return False
        if model_name in self._lightweight_models:
            return self._lightweight_models[model_name]["fitted"]
        return False

    def set_tfidf_fitted(self, model_name: str = "paraphrase-MiniLM-L6-v2", fitted: bool = True):
        """设置TF-IDF训练状态"""
        if self._should_use_lightweight() and model_name in self._lightweight_models:
            self._lightweight_models[model_name]["fitted"] = fitted

    def get_model_path(self, model_name: str) -> Optional[str]:
        """获取模型路径，优先使用内置模型"""
        if model_name in self.builtin_models:
            try:
                builtin_path = self._get_builtin_model_path(model_name)
                if builtin_path and self._validate_model_files(builtin_path):
                    return str(builtin_path)
            except Exception:
                pass
        return model_name

    def _get_builtin_model_path(self, model_name: str) -> Optional[Path]:
        """获取内置模型路径"""
        try:
            import aiforge.models

            model_subpath = self.builtin_models[model_name]
            import tempfile

            temp_dir = Path(tempfile.mkdtemp(prefix=f"aiforge_model_{model_name}_"))
            from importlib.resources import files

            models_root = files(aiforge.models)
            model_path = models_root / model_subpath.split("/")[0] / model_subpath.split("/")[-1]
            if model_path.is_dir():
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
