from typing import Dict, Any, Set
import json
import time
from pathlib import Path


class DynamicTaskTypeManager:
    """动态任务类型管理器"""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.task_types_db = cache_dir / "task_types.json"
        self.builtin_types = {
            "data_fetch",
            "data_process",
            "file_operation",
            "automation",
            "content_generation",
            "general",
        }
        self.dynamic_types = self._load_dynamic_types()

    def _load_dynamic_types(self) -> Dict[str, Dict]:
        """加载动态任务类型"""
        if self.task_types_db.exists():
            with open(self.task_types_db, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def register_task_type(self, task_type: str, standardized_instruction: Dict[str, Any]):
        """注册新的任务类型"""
        if task_type in self.builtin_types:
            return  # 内置类型不需要注册

        if task_type not in self.dynamic_types:
            self.dynamic_types[task_type] = {
                "count": 0,
                "success_count": 0,
                "patterns": [],
                "created_at": time.time(),
                "last_used": time.time(),
            }

        # 更新统计信息
        self.dynamic_types[task_type]["count"] += 1
        self.dynamic_types[task_type]["last_used"] = time.time()

        # 提取模式
        target = standardized_instruction.get("target", "")
        if target and target not in self.dynamic_types[task_type]["patterns"]:
            self.dynamic_types[task_type]["patterns"].append(target[:50])

        self._save_dynamic_types()

    def update_success_rate(self, task_type: str, success: bool):
        """更新成功率"""
        if task_type in self.dynamic_types:
            if success:
                self.dynamic_types[task_type]["success_count"] += 1
            self._save_dynamic_types()

    def get_all_task_types(self) -> Set[str]:
        """获取所有任务类型（内置+动态）"""
        return self.builtin_types | set(self.dynamic_types.keys())

    def get_task_type_priority(self, task_type: str) -> int:
        """获取任务类型优先级（用于缓存匹配）"""
        if task_type in self.builtin_types:
            return 100  # 内置类型最高优先级
        elif task_type in self.dynamic_types:
            # 基于使用频率和成功率计算优先级
            info = self.dynamic_types[task_type]
            success_rate = info["success_count"] / max(info["count"], 1)
            return int(50 + success_rate * 30 + min(info["count"] / 10, 20))
        return 0

    def _save_dynamic_types(self):
        """保存动态任务类型到文件"""
        try:
            # 确保目录存在
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            with open(self.task_types_db, "w", encoding="utf-8") as f:
                json.dump(self.dynamic_types, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
