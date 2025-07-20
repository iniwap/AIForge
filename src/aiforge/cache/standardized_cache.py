import hashlib
import time
import json
from pathlib import Path
from typing import Any, List, Dict
from peewee import Case
from .code_cache import AiForgeCodeCache
from ..extensions.extension_manager import ExtensionManager


class StandardizedCodeCache(AiForgeCodeCache):
    """完全基于标准化指令的增强代码缓存管理器 - 支持模板扩展"""

    def __init__(self, cache_dir: Path, config: dict | None = None):
        super().__init__(cache_dir, config)
        self.extension_manager = ExtensionManager()
        self._load_builtin_extensions()

    def _load_builtin_extensions(self):
        """加载内置扩展"""
        # 这里可以加载预定义的领域扩展
        pass

    def register_template_extension(self, extension_config: Dict[str, Any]) -> bool:
        """注册模板扩展"""
        try:
            domain_name = extension_config.get("domain")
            extension_class = extension_config.get("class")

            # 动态创建扩展实例
            extension = extension_class(domain_name, extension_config)
            return self.extension_manager.register_template_extension(extension)
        except Exception:
            return False

    def get_cached_modules_by_standardized_instruction(
        self, standardized_instruction: Dict[str, Any]
    ) -> List[Any]:
        """基于标准化指令获取缓存模块 - 支持模板扩展优先匹配"""
        # 1. 优先检查模板扩展
        template_match = self.extension_manager.find_template_match(standardized_instruction)
        if template_match:
            template_results = self._get_template_cached_modules(
                template_match, standardized_instruction
            )
            if template_results:
                return template_results

        # 2. 回退到标准化指令匹配
        cache_key = standardized_instruction.get("cache_key")
        task_type = standardized_instruction.get("task_type")
        action = standardized_instruction.get("action", "process")

        results = []

        # 策略1: 精确匹配cache_key (已经是MD5哈希)
        if cache_key:
            exact_matches = self._get_modules_by_key(cache_key)
            results.extend([(m, "exact") for m in exact_matches])

        # 策略1.5: 任务类型+查询动作匹配
        if task_type == "data_fetch" and action == "search":
            query_action_key = f"{task_type}_查询"
            query_action_hash = hashlib.md5(query_action_key.encode()).hexdigest()
            query_matches = self._get_modules_by_key(query_action_hash)
            results.extend([(m, "query_action") for m in query_matches])

        # 策略2: 任务类型+动作匹配
        type_action_key = f"{task_type}_{action}"
        type_action_hash = hashlib.md5(type_action_key.encode()).hexdigest()
        type_matches = self._get_modules_by_key(type_action_hash)
        results.extend([(m, "type_action") for m in type_matches])

        # 策略3: 通用任务类型匹配
        general_key = f"{task_type}_general"
        general_hash = hashlib.md5(general_key.encode()).hexdigest()
        general_matches = self._get_modules_by_key(general_hash)
        results.extend([(m, "general") for m in general_matches])

        return self._rank_and_deduplicate_results(results)

    def _get_template_cached_modules(
        self, template_match: Dict, standardized_instruction: Dict
    ) -> List[Any]:
        """获取模板匹配的缓存模块"""
        template_name = template_match.get("template_name")
        domain = template_match.get("domain")

        # 生成模板特定的缓存键
        template_cache_key = f"template_{domain}_{template_name}"

        with self._lock:
            try:
                modules = (
                    self.CodeModule.select()
                    .where(self.CodeModule.instruction_hash == template_cache_key)
                    .order_by(self.CodeModule.success_count.desc())
                )

                results = []
                for module in modules:
                    metadata = json.loads(module.metadata)
                    if metadata.get("is_template_extension", False):
                        results.append(
                            (
                                module.module_id,
                                module.file_path,
                                module.success_count,
                                module.failure_count,
                                metadata,
                            )
                        )

                return results
            except Exception:
                return []

    def save_template_extension_module(
        self, template_match: Dict, standardized_instruction: Dict, code: str
    ) -> str | None:
        """保存模板扩展生成的模块"""
        if not self._validate_code(code):
            return None

        template_name = template_match.get("template_name")
        domain = template_match.get("domain")
        template_cache_key = f"template_{domain}_{template_name}"

        module_id = f"template_ext_{domain}_{template_name}_{int(time.time())}"
        file_path = self.modules_dir / f"{module_id}.py"

        try:
            # 保存代码文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            # 扩展元数据
            extended_metadata = {
                "standardized_instruction": standardized_instruction,
                "template_match": template_match,
                "domain": domain,
                "template_name": template_name,
                "is_template_extension": True,
                "created_at": time.time(),
            }

            # 保存到数据库
            current_time = time.time()
            with self._lock:
                self.CodeModule.create(
                    module_id=module_id,
                    instruction_hash=template_cache_key,
                    file_path=str(file_path),
                    created_at=current_time,
                    last_used=current_time,
                    metadata=json.dumps(extended_metadata),
                )

            return module_id

        except Exception:
            if file_path.exists():
                file_path.unlink()
            return None

    def _get_modules_by_key(self, cache_key: str) -> List[Any]:
        """根据缓存键获取模块，按成功率排序"""
        if not cache_key:
            return []

        with self._lock:
            try:
                # 执行具体查询
                modules = (
                    self.CodeModule.select()
                    .where(self.CodeModule.instruction_hash == cache_key)
                    .order_by(
                        Case(
                            None,
                            [
                                (
                                    (self.CodeModule.success_count + self.CodeModule.failure_count)
                                    == 0,
                                    0.5,
                                )
                            ],
                            self.CodeModule.success_count
                            / (self.CodeModule.success_count + self.CodeModule.failure_count),
                        ).desc()
                    )
                )

                result = [
                    (m.module_id, m.file_path, m.success_count, m.failure_count) for m in modules
                ]

                return result
            except Exception:
                return []

    def _rank_and_deduplicate_results(self, results: List[tuple]) -> List[Any]:
        """对结果进行排序和去重"""
        # 按策略优先级排序: exact > query_action > type_action > general
        strategy_priority = {"exact": 4, "query_action": 3, "type_action": 2, "general": 1}

        # 去重（基于module_id）
        seen_modules = set()
        ranked_results = []

        for result_tuple in results:
            if len(result_tuple) == 2:
                module_data, strategy = result_tuple
                if len(module_data) == 4:
                    module_id, file_path, success_count, failure_count = module_data
                else:
                    continue
            else:
                continue

            if module_id not in seen_modules:
                seen_modules.add(module_id)
                # 计算综合分数：策略优先级 + 成功率
                total_attempts = success_count + failure_count
                success_rate = success_count / total_attempts if total_attempts > 0 else 0.5
                score = strategy_priority.get(strategy, 1) + success_rate

                ranked_results.append((module_id, file_path, success_count, failure_count, score))

        # 按综合分数排序
        ranked_results.sort(key=lambda x: x[4], reverse=True)

        # 返回原格式
        return [(m[0], m[1], m[2], m[3]) for m in ranked_results]

    def save_standardized_module(
        self,
        standardized_instruction: Dict[str, Any],
        code: str,
        metadata: dict | None = None,
    ) -> str | None:
        """保存基于标准化指令的增强模块"""
        if not self._validate_code(code):
            return None

        task_type = standardized_instruction.get("task_type", "general")
        action = standardized_instruction.get("action", "process")

        # 修改：使用与查询一致的缓存键生成策略
        # 不再使用复杂的 _generate_standardized_cache_key 方法
        # 而是直接使用 task_type_action 格式并进行MD5哈希
        cache_key = hashlib.md5(f"{task_type}_{action}".encode()).hexdigest()

        module_id = f"std_{task_type}_{action}_{int(time.time())}"
        file_path = self.modules_dir / f"{module_id}.py"

        try:
            # 保存代码文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            # 扩展元数据
            extended_metadata = {
                "standardized_instruction": standardized_instruction,
                "task_type": task_type,
                "action": action,
                "cache_key": cache_key,
                "is_standardized": True,
                "created_at": time.time(),
                **(metadata or {}),
            }

            # 保存到数据库
            current_time = time.time()
            with self._lock:
                self.CodeModule.create(
                    module_id=module_id,
                    instruction_hash=cache_key,  # 使用新的简化缓存键
                    file_path=str(file_path),
                    created_at=current_time,
                    last_used=current_time,
                    metadata=json.dumps(extended_metadata),
                )

            return module_id

        except Exception:
            if file_path.exists():
                file_path.unlink()
            return None

    def _generate_standardized_cache_key(self, standardized_instruction: Dict[str, Any]) -> str:
        """基于标准化指令生成缓存键"""
        task_type = standardized_instruction.get("task_type", "general")
        action = standardized_instruction.get("action", "process")
        parameters = standardized_instruction.get("parameters", {})

        # 生成稳定的参数哈希
        params_str = json.dumps(parameters, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]

        # 组合生成缓存键
        key_base = f"{task_type}_{action}_{params_hash}"
        return hashlib.md5(key_base.encode()).hexdigest()

    def get_cache_statistics_by_task_type(self) -> Dict[str, Any]:
        """按任务类型获取缓存统计信息"""
        with self._lock:
            try:
                total_modules = self.CodeModule.select().count()
                standardized_modules = (
                    self.CodeModule.select()
                    .where(self.CodeModule.metadata.contains('"is_standardized": true'))
                    .count()
                )

                # 按任务类型统计
                task_type_stats = {}
                action_stats = {}
                modules = self.CodeModule.select()

                for module in modules:
                    try:
                        metadata = json.loads(module.metadata)
                        if metadata.get("is_standardized"):
                            task_type = metadata.get("task_type", "unknown")
                            action = metadata.get("action", "unknown")

                            task_type_stats[task_type] = task_type_stats.get(task_type, 0) + 1
                            action_key = f"{task_type}_{action}"
                            action_stats[action_key] = action_stats.get(action_key, 0) + 1
                    except Exception:
                        continue

                return {
                    "total_modules": total_modules,
                    "standardized_modules": standardized_modules,
                    "task_type_distribution": task_type_stats,
                    "action_distribution": action_stats,
                    "cache_hit_rate": self._calculate_hit_rate(),
                    "most_used_task_types": sorted(
                        task_type_stats.items(), key=lambda x: x[1], reverse=True
                    )[:5],
                }
            except Exception:
                return {"error": "Failed to get statistics"}

    def _calculate_hit_rate(self) -> float:
        """计算缓存命中率"""
        try:
            modules = self.CodeModule.select()
            total_attempts = 0
            successful_hits = 0

            for module in modules:
                total_attempts += module.success_count + module.failure_count
                successful_hits += module.success_count

            return successful_hits / total_attempts if total_attempts > 0 else 0.0
        except Exception:
            return 0.0

    def cleanup_by_task_type(self, task_type: str, max_modules: int = 5):
        """按任务类型清理模块，保留最成功的几个"""
        with self._lock:
            try:
                # 查找指定任务类型的模块
                modules = (
                    self.CodeModule.select()
                    .where(self.CodeModule.metadata.contains(f'"task_type": "{task_type}"'))
                    .order_by(self.CodeModule.success_count.desc())
                )

                modules_list = list(modules)
                if len(modules_list) > max_modules:
                    # 删除多余的模块
                    modules_to_delete = modules_list[max_modules:]

                    for module in modules_to_delete:
                        # 删除文件
                        file_path = Path(module.file_path)
                        if file_path.exists():
                            file_path.unlink()

                        # 删除数据库记录
                        module.delete_instance()

            except Exception as e:
                print(f"清理任务类型 {task_type} 的模块失败: {e}")

    def find_similar_modules(
        self, standardized_instruction: Dict[str, Any], limit: int = 5
    ) -> List[Dict]:
        """查找相似的模块"""
        task_type = standardized_instruction.get("task_type")
        action = standardized_instruction.get("action")

        with self._lock:
            try:
                # 查找相同任务类型和动作的模块
                similar_modules = []
                modules = (
                    self.CodeModule.select()
                    .where(
                        self.CodeModule.metadata.contains(f'"task_type": "{task_type}"'),
                        self.CodeModule.metadata.contains(f'"action": "{action}"'),
                    )
                    .order_by(self.CodeModule.success_count.desc())
                    .limit(limit)
                )

                for module in modules:
                    try:
                        metadata = json.loads(module.metadata)
                        similar_modules.append(
                            {
                                "module_id": module.module_id,
                                "task_type": metadata.get("task_type"),
                                "action": metadata.get("action"),
                                "success_count": module.success_count,
                                "failure_count": module.failure_count,
                                "success_rate": module.success_rate,
                                "created_at": module.created_at,
                            }
                        )
                    except Exception:
                        continue

                return similar_modules
            except Exception:
                return []
