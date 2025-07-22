import hashlib
import time
import json
from pathlib import Path
from typing import Any, List, Dict, Tuple
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
        """基于标准化指令获取缓存模块"""
        task_type = standardized_instruction.get("task_type")
        action = standardized_instruction.get("action", "process")
        cache_key = standardized_instruction.get("cache_key")

        print(f"[DEBUG] 缓存查找: task_type={task_type}, action={action}, cache_key={cache_key}")

        results = []

        # 策略1: 精确匹配
        if cache_key:
            exact_matches = self._get_modules_by_key(cache_key)
            print(f"[DEBUG] 精确匹配结果: {len(exact_matches)} 个模块")
            results.extend([(m, "exact") for m in exact_matches])

        # 策略2: 任务类型匹配
        type_action_key = f"{task_type}_{action}"
        type_action_hash = hashlib.md5(type_action_key.encode()).hexdigest()
        print(f"[DEBUG] 任务类型匹配键: {type_action_key} -> {type_action_hash}")
        type_matches = self._get_modules_by_key(type_action_hash)
        print(f"[DEBUG] 任务类型匹配结果: {len(type_matches)} 个模块")
        results.extend([(m, "type_action") for m in type_matches])

        final_results = self._rank_and_deduplicate_results(results)
        print(f"[DEBUG] 最终缓存查找结果: {len(final_results)} 个模块")

        return final_results

    def _calculate_pattern_similarity(self, patterns1: List[str], patterns2: List[str]) -> float:
        """计算模式相似度"""
        if not patterns1 or not patterns2:
            return 0.0

        # 使用简单的词汇重叠度计算相似度
        set1 = set()
        set2 = set()

        # 将模式分词
        for pattern in patterns1:
            words = pattern.lower().split()
            set1.update(words)

        for pattern in patterns2:
            words = pattern.lower().split()
            set2.update(words)

        if not set1 or not set2:
            return 0.0

        # 计算 Jaccard 相似度
        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def _find_similar_task_types(self, task_type: str) -> List[str]:
        """查找相似的任务类型"""
        similar_types = []

        # 基于模式匹配查找相似类型
        if task_type in self.task_type_manager.dynamic_types:
            current_patterns = self.task_type_manager.dynamic_types[task_type]["patterns"]

            for other_type, info in self.task_type_manager.dynamic_types.items():
                if other_type != task_type:
                    # 计算模式相似度
                    similarity = self._calculate_pattern_similarity(
                        current_patterns, info["patterns"]
                    )
                    if similarity > 0.3:  # 相似度阈值
                        similar_types.append(other_type)

        return similar_types[:3]  # 最多返回3个相似类型

    def _generate_parameter_signature(self, required_params: Dict[str, Any]) -> str:
        """生成参数签名用于缓存匹配"""
        if not required_params:
            return ""

        param_types = []
        for param_name, param_info in sorted(required_params.items()):
            if isinstance(param_info, dict):
                param_type = param_info.get("type", "str")
                required = param_info.get("required", True)
                param_types.append(f"{param_name}:{param_type}{'!' if required else '?'}")
            else:
                param_types.append(f"{param_name}:str!")

        return ",".join(param_types)

    def _find_exact_parameter_matches(
        self, cache_key: str, task_type: str, required_params: Dict[str, Any]
    ) -> List[Tuple[str, str, int, int]]:
        """查找参数完全匹配的模块"""
        param_signature = self._generate_parameter_signature(required_params)

        # 构建查询条件
        conditions = []

        # 如果有缓存键，优先使用缓存键匹配
        if cache_key:
            conditions.append(self.CodeModule.cache_key == cache_key)

        # 如果有参数签名，使用任务类型+参数签名匹配
        if param_signature:
            conditions.append(
                (self.CodeModule.task_type == task_type)
                & (self.CodeModule.parameter_signature == param_signature)
            )
        else:
            # 无参数情况，匹配同类型的非参数化模块
            conditions.append(
                (self.CodeModule.task_type == task_type)
                & (self.CodeModule.is_parameterized is False)
            )

        if not conditions:
            return []

        modules = (
            self.CodeModule.select()
            .where(conditions[0] if len(conditions) == 1 else conditions[0] | conditions[1])
            .order_by(
                (
                    self.CodeModule.success_count
                    / (self.CodeModule.success_count + self.CodeModule.failure_count + 1)
                ).desc(),
                self.CodeModule.last_used.desc(),
            )
        )

        return [(m.module_id, m.file_path, m.success_count, m.failure_count) for m in modules]

    def _find_compatible_parameter_matches(
        self, task_type: str, required_params: Dict[str, Any]
    ) -> List[Tuple[str, str, int, int]]:
        """查找参数兼容的模块"""
        if not required_params:
            return []

        # 查找相同任务类型且参数数量相近的模块
        param_count = len(required_params)

        modules = (
            self.CodeModule.select()
            .where(
                (self.CodeModule.task_type == task_type)
                & (self.CodeModule.parameter_count.between(param_count - 1, param_count + 1))
                & (self.CodeModule.is_parameterized is True)
            )
            .order_by(
                (
                    self.CodeModule.success_count
                    / (self.CodeModule.success_count + self.CodeModule.failure_count + 1)
                ).desc()
            )
            .limit(3)  # 限制兼容匹配数量
        )

        return [(m.module_id, m.file_path, m.success_count, m.failure_count) for m in modules]

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
        """保存基于参数化标准化指令的模块"""
        if not self._validate_code(code):
            return None

        task_type = standardized_instruction.get("task_type", "general")
        action = standardized_instruction.get("action", "process")

        # 生成缓存键
        cache_key = hashlib.md5(f"{task_type}_{action}".encode()).hexdigest()

        print(f"[DEBUG] 保存模块: task_type={task_type}, action={action}")
        print(f"[DEBUG] 保存缓存键: {task_type}_{action} -> {cache_key}")

        module_id = f"std_{task_type}_{action}_{int(time.time())}"
        print(f"[DEBUG] 生成模块ID: {module_id}")

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
                    instruction_hash=cache_key,
                    file_path=str(file_path),
                    created_at=current_time,
                    last_used=current_time,
                    metadata=json.dumps(extended_metadata),
                )

            print(f"[DEBUG] 模块保存成功: {module_id}, 缓存键: {cache_key}")
            return module_id

        except Exception as e:
            print(f"[DEBUG] 模块保存失败: {e}")
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

            except Exception:
                pass

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
