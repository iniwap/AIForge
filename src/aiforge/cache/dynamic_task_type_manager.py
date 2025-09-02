from typing import Dict, Any, Set
import json
import time
from ..core.path_manager import AIForgePathManager


class DynamicTaskTypeManager:
    """动态任务类型管理器"""

    def __init__(self):
        self.cache_dir = AIForgePathManager.get_cache_dir()
        self.task_types_db = self.cache_dir / "task_types.json"
        self.builtin_types = {
            "data_fetch",
            "data_process",
            "file_operation",
            "automation",
            "content_generation",
            "general",
        }
        self.dynamic_types = self._load_dynamic_types()
        self.type_priorities = {}
        self.dynamic_actions = {}
        self._load_dynamic_data()

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
            with open(self.task_types_db, "w", encoding="utf-8") as f:
                json.dump(self.dynamic_types, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def register_dynamic_action(self, action: str, task_type: str, analysis_result: Dict[str, Any]):
        """注册动态生成的动作"""
        if not hasattr(self, "dynamic_actions"):
            self.dynamic_actions = {}

        self.dynamic_actions[action] = {
            "task_type": task_type,
            "parameters": analysis_result.get("required_parameters", {}),
            "created_at": time.time(),
            "usage_count": 0,
            "source": "ai_analysis",
        }

        # 保存到文件
        self._save_dynamic_data()

    def get_dynamic_action_info(self, action: str) -> Dict[str, Any]:
        """获取动态动作信息"""
        return self.dynamic_actions.get(action, {})

    def increment_action_usage(self, action: str):
        """增加动作使用计数"""
        if action in self.dynamic_actions:
            self.dynamic_actions[action]["usage_count"] += 1
            self._save_dynamic_data()

    def _save_dynamic_data(self):
        """保存动态数据到文件"""
        dynamic_data = {
            "dynamic_types": self.dynamic_types,
            "type_priorities": self.type_priorities,
            "dynamic_actions": getattr(self, "dynamic_actions", {}),
        }

        dynamic_file = self.cache_dir / "dynamic_data.json"
        try:
            with open(dynamic_file, "w", encoding="utf-8") as f:
                json.dump(dynamic_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_dynamic_data(self):
        """从文件加载动态数据"""
        dynamic_file = self.cache_dir / "dynamic_data.json"
        if dynamic_file.exists():
            try:
                with open(dynamic_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.dynamic_types = data.get("dynamic_types", {})
                    self.type_priorities = data.get("type_priorities", {})
                    self.dynamic_actions = data.get("dynamic_actions", {})
            except Exception:
                self.dynamic_actions = {}
