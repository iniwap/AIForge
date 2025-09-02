import hashlib
import json
import os
import pickle
import time
from typing import Dict, List, Any
from collections import defaultdict
from pathlib import Path

from ..extensions.extension_manager import ExtensionManager
from .code_cache import AiForgeCodeCache
from .action_matcher import SemanticActionMatcher
from ..core.path_manager import AIForgePathManager


class EnhancedStandardizedCache(AiForgeCodeCache):
    """增强的标准化缓存"""

    def __init__(self, config: dict | None = None):
        # 扩展配置以支持语义匹配功能
        enhanced_config = config or {}
        enhanced_config.update(
            {
                "semantic_threshold": enhanced_config.get("semantic_threshold", 0.4),
                "enable_semantic_matching": enhanced_config.get("enable_semantic_matching", True),
                "use_lightweight_semantic": enhanced_config.get("use_lightweight_semantic", True),
                "enable_action_clustering": enhanced_config.get("enable_action_clustering", True),
                "action_cluster_threshold": enhanced_config.get("action_cluster_threshold", 0.75),
            }
        )

        # 调用父类初始化，复用基础缓存功能
        super().__init__(enhanced_config)

        # 向量存储路径（增强功能特有）
        self.vector_store_path = self.cache_dir / "vector_store.pkl"
        self.action_clusters_path = self.cache_dir / "action_clusters.pkl"

        # 初始化扩展管理器
        self.extension_manager = ExtensionManager()
        self._load_builtin_extensions()

        # 初始化语义分析组件（延迟加载）
        self._init_semantic_components()

        # 初始化语义动作匹配器
        self._init_semantic_action_matcher()

        # 加载向量存储
        self._load_vector_storage()

        # 初始化模块索引
        if not hasattr(self, "_module_indexes"):
            self._module_indexes = defaultdict(list)

    def _init_semantic_action_matcher(self):
        """初始化语义动作匹配器"""
        if self.config.get("enable_action_clustering", True):
            self.semantic_action_matcher = SemanticActionMatcher(self)
            self._load_action_clusters()
        else:
            self.semantic_action_matcher = None

    def _load_action_clusters(self):
        """加载动作聚类数据"""
        if os.path.exists(self.action_clusters_path):
            try:
                with open(self.action_clusters_path, "rb") as f:
                    cluster_data = pickle.load(f)
                    self.semantic_action_matcher.action_clusters = cluster_data.get(
                        "action_clusters", {}
                    )
                    self.semantic_action_matcher.action_vectors = cluster_data.get(
                        "action_vectors", {}
                    )
            except Exception:
                pass

    def _save_action_clusters(self):
        """保存动作聚类数据"""
        if self.semantic_action_matcher:
            try:
                cluster_data = {
                    "action_clusters": self.semantic_action_matcher.action_clusters,
                    "action_vectors": self.semantic_action_matcher.action_vectors,
                }
                with open(self.action_clusters_path, "wb") as f:
                    pickle.dump(cluster_data, f)
            except Exception:
                pass

    def _load_builtin_extensions(self):
        """加载内置扩展"""
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

    def _init_semantic_components(self):
        """初始化语义分析组件"""
        if not self.config.get("enable_semantic_matching", True):
            self.semantic_enabled = False
            return

        self.semantic_enabled = True
        self._semantic_model = None

    @property
    def semantic_model(self):
        """延迟加载语义模型"""
        if self._semantic_model is None:
            try:
                from ..models.model_manager import ModelManager

                self._semantic_model = ModelManager().get_semantic_model()
            except Exception:
                self.semantic_enabled = False
                return None
        return self._semantic_model

    @property
    def tfidf_vectorizer(self):
        """获取TF-IDF向量化器"""
        from ..models.model_manager import ModelManager

        return ModelManager().get_tfidf_vectorizer()

    @property
    def fitted_tfidf(self):
        """检查TF-IDF是否已训练"""
        from ..models.model_manager import ModelManager

        return ModelManager().is_tfidf_fitted()

    def set_tfidf_fitted(self, fitted: bool = True):
        """设置TF-IDF训练状态"""
        from ..models.model_manager import ModelManager

        ModelManager().set_tfidf_fitted(fitted=fitted)

    def _load_vector_storage(self):
        """加载向量存储"""
        if os.path.exists(self.vector_store_path):
            try:
                with open(self.vector_store_path, "rb") as f:
                    vector_data = pickle.load(f)
                    self.command_vectors = vector_data.get("command_vectors", {})
                    self.intent_clusters = vector_data.get("intent_clusters", defaultdict(list))
                    self.param_templates = vector_data.get("param_templates", defaultdict(list))
                    self.usage_stats = vector_data.get("usage_stats", {})
            except Exception:
                self._init_empty_vectors()
        else:
            self._init_empty_vectors()

    def _init_empty_vectors(self):
        """初始化空向量存储"""
        self.command_vectors = {}
        self.intent_clusters = defaultdict(list)
        self.param_templates = defaultdict(list)
        self.usage_stats = {}

    def get_cached_modules_by_standardized_instruction(
        self, standardized_instruction: Dict[str, Any]
    ) -> List[Any]:
        """通用缓存模块查找"""

        if self.should_cleanup():
            self.cleanup()

        task_type = standardized_instruction.get("task_type", "general")
        action = standardized_instruction.get("action", "process")
        source = standardized_instruction.get("source", "unknown")  # 获取来源信息

        results = []

        # 策略1: 精确匹配（最高优先级）
        exact_matches = self._get_exact_matches(task_type, action)
        results.extend([(m, "exact", 1.0) for m in exact_matches])

        # 策略2: 动作聚类匹配（高优先级）
        if self.semantic_action_matcher and not results:
            cluster_matches = self._get_action_cluster_matches(action, source)
            results.extend([(m, "action_cluster", 0.9) for m in cluster_matches])

        # 策略3: 任务类型匹配
        if not results:
            type_matches = self._get_task_type_matches(task_type)
            results.extend([(m, "task_type", 0.8) for m in type_matches])

        # 策略4: 语义相似度匹配
        if self.semantic_enabled:
            semantic_matches = self._get_semantic_matches(standardized_instruction)
            results.extend([(m, "semantic", score) for m, score in semantic_matches])

        # 策略5: 动作相似度匹配（兜底）
        if not results:
            action_matches = self._get_action_similarity_matches(action)
            results.extend([(m, "action_similarity", 0.6) for m in action_matches])

        return self._rank_and_deduplicate_results(results)

    def _get_action_cluster_matches(self, action: str, source: str = "unknown") -> List[Any]:
        """基于动作聚类的匹配，确保使用标准化"""
        if not self.semantic_action_matcher:
            return []

        matches = []

        try:
            # 获取标准化后的动作聚类，传递来源信息
            cluster_id = self.semantic_action_matcher.get_action_cluster(action, source)

            # 查找同一聚类中的其他动作对应的模块
            if cluster_id in self.semantic_action_matcher.action_clusters:
                cluster_actions = self.semantic_action_matcher.action_clusters[cluster_id]

                with self._lock:
                    for cluster_action in cluster_actions:
                        if cluster_action != action:  # 排除自身
                            # 查找使用该动作的模块
                            modules = self._find_modules_by_action(cluster_action)
                            matches.extend(modules)

        except Exception:
            pass

        return matches

    def _find_modules_by_action(self, action: str) -> List[Any]:
        """根据动作查找模块"""
        matches = []

        with self._lock:
            try:
                all_modules = self.CodeModule.select()

                for module in all_modules:
                    try:
                        metadata = json.loads(module.metadata)
                        cached_action = metadata.get("standardized_instruction", {}).get(
                            "action", ""
                        )

                        if cached_action == action:
                            matches.append(
                                (
                                    module.module_id,
                                    module.file_path,
                                    module.success_count,
                                    module.failure_count,
                                )
                            )
                    except Exception:
                        continue

            except Exception:
                pass

        return matches

    def _get_exact_matches(self, task_type: str, action: str) -> List[Any]:
        """精确匹配"""
        exact_key = hashlib.md5(f"{task_type}_{action}".encode()).hexdigest()
        return self._get_modules_by_key(exact_key)

    def _get_modules_by_key(self, cache_key: str) -> List[Any]:
        """根据缓存键获取模块，按成功率排序"""
        if not cache_key:
            return []

        with self._lock:
            try:
                # 简化的查询，不使用复杂的Case逻辑
                modules = (
                    self.CodeModule.select()
                    .where(self.CodeModule.instruction_hash == cache_key)
                    .order_by(self.CodeModule.last_used.desc())
                )

                result = [
                    (m.module_id, m.file_path, m.success_count, m.failure_count) for m in modules
                ]

                return result
            except Exception:
                return []

    def _get_task_type_matches(self, task_type: str) -> List[Any]:
        """任务类型匹配"""
        matches = []

        with self._lock:
            try:
                # 直接查询数据库中相同task_type的模块
                modules = (
                    self.CodeModule.select()
                    .where(self.CodeModule.task_type == task_type)
                    .order_by(self.CodeModule.last_used.desc())
                    .limit(10)
                )

                matches = [
                    (m.module_id, m.file_path, m.success_count, m.failure_count) for m in modules
                ]

            except Exception:
                pass

        return matches

    def _get_action_similarity_matches(self, action: str) -> List[Any]:
        """动作相似度匹配"""
        matches = []

        with self._lock:
            try:
                all_modules = self.CodeModule.select()

                for module in all_modules:
                    try:
                        metadata = json.loads(module.metadata)
                        cached_action = metadata.get("standardized_instruction", {}).get(
                            "action", ""
                        )

                        if cached_action:
                            # 使用通用的文本相似度计算
                            similarity = self._compute_text_similarity(action, cached_action)

                            # 设置较低的阈值以增加匹配机会
                            if similarity > 0.5:
                                matches.append(
                                    (
                                        module.module_id,
                                        module.file_path,
                                        module.success_count,
                                        module.failure_count,
                                    )
                                )

                    except Exception:
                        continue

            except Exception:
                pass

        return matches

    def _get_semantic_matches(self, standardized_instruction: Dict[str, Any]) -> List[tuple]:
        """通用语义匹配"""
        if not self.semantic_enabled:
            return []

        target = standardized_instruction.get("target", "")
        action = standardized_instruction.get("action", "")
        task_type = standardized_instruction.get("task_type", "")

        semantic_matches = []

        with self._lock:
            try:
                all_modules = self.CodeModule.select()

                for module in all_modules:
                    try:
                        metadata = json.loads(module.metadata)
                        cached_instruction = metadata.get("standardized_instruction", {})
                        cached_target = cached_instruction.get("target", "")
                        cached_action = cached_instruction.get("action", "")
                        cached_task_type = cached_instruction.get("task_type", "")

                        if not cached_target and not cached_action:
                            continue

                        # 计算多维度相似度
                        similarity = self._compute_multi_dimensional_similarity(
                            target,
                            action,
                            task_type,
                            cached_target,
                            cached_action,
                            cached_task_type,
                        )

                        # 动态阈值：根据匹配维度调整
                        threshold = self._calculate_dynamic_threshold(
                            target,
                            action,
                            task_type,
                            cached_target,
                            cached_action,
                            cached_task_type,
                        )

                        if similarity > threshold:
                            semantic_matches.append(
                                (
                                    (
                                        module.module_id,
                                        module.file_path,
                                        module.success_count,
                                        module.failure_count,
                                    ),
                                    similarity,
                                )
                            )

                    except Exception:
                        continue

            except Exception:
                pass

        semantic_matches.sort(key=lambda x: x[1], reverse=True)
        return semantic_matches[:10]

    def _compute_multi_dimensional_similarity(
        self, target1: str, action1: str, type1: str, target2: str, action2: str, type2: str
    ) -> float:
        """多维度相似度计算"""

        # 任务类型完全匹配得分最高
        type_similarity = 1.0 if type1 == type2 else 0.0

        # 动作文本相似度
        action_similarity = self._compute_text_similarity(action1, action2)

        # 目标文本相似度
        target_similarity = self._compute_text_similarity(target1, target2)

        # 语义特征相似度
        semantic_similarity = 0.0
        if self.semantic_enabled:
            features1 = set(self._extract_semantic_features(f"{target1} {action1}"))
            features2 = set(self._extract_semantic_features(f"{target2} {action2}"))

            if features1 and features2:
                intersection = len(features1 & features2)
                union = len(features1 | features2)
                semantic_similarity = intersection / union if union > 0 else 0.0

        # 加权计算最终相似度
        weights = {"type": 0.3, "action": 0.3, "target": 0.2, "semantic": 0.2}

        final_similarity = (
            weights["type"] * type_similarity
            + weights["action"] * action_similarity
            + weights["target"] * target_similarity
            + weights["semantic"] * semantic_similarity
        )

        return final_similarity

    def _compute_text_similarity(self, text1: str, text2: str) -> float:
        """通用文本相似度计算"""
        if not text1 or not text2:
            return 0.0

        if text1 == text2:
            return 1.0

        # 标准化文本
        words1 = set(self._normalize_text(text1).split())
        words2 = set(self._normalize_text(text2).split())

        if not words1 or not words2:
            return 0.0

        # Jaccard相似度
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _normalize_text(self, text: str) -> str:
        """文本标准化处理"""
        import re

        # 转换为小写
        text = text.lower()

        # 移除标点符号，保留中英文字符和数字
        text = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", text)

        # 移除多余空格
        text = " ".join(text.split())

        return text

    def _calculate_dynamic_threshold(
        self, target1: str, action1: str, type1: str, target2: str, action2: str, type2: str
    ) -> float:
        """动态阈值计算"""

        # 基础阈值
        base_threshold = 0.4

        # 如果任务类型相同，降低阈值
        if type1 == type2:
            base_threshold -= 0.1

        # 如果动作完全相同，大幅降低阈值
        if action1 == action2:
            base_threshold -= 0.2

        # 确保阈值在合理范围内
        return max(0.2, min(0.6, base_threshold))

    def _extract_semantic_features(self, text: str) -> List[str]:
        """提取语义特征"""
        if not text:
            return []

        features = []

        # 提取关键词
        words = self._normalize_text(text).split()
        features.extend(words[:5])  # 取前5个词作为特征

        # 提取长度特征
        if len(text) > 50:
            features.append("long_text")
        elif len(text) < 10:
            features.append("short_text")

        return features

    def _generate_semantic_hash(self, text: str) -> str:
        """生成语义哈希"""
        if not text:
            return ""

        normalized = self._normalize_text(text)
        return hashlib.md5(normalized.encode()).hexdigest()[:8]

    def _extract_intent_category(self, text: str) -> str:
        """提取意图分类"""
        if not text:
            return "general"

        # 简单的意图分类
        text_lower = text.lower()

        if any(word in text_lower for word in ["获取", "查询", "搜索", "get", "fetch", "search"]):
            return "data_fetch"
        elif any(word in text_lower for word in ["分析", "计算", "处理", "analyze", "process"]):
            return "data_analysis"
        elif any(word in text_lower for word in ["生成", "创建", "制作", "generate", "create"]):
            return "content_generation"
        else:
            return "general"

    def _generate_param_signature(self, params: Dict) -> str:
        """生成参数签名"""
        if not params:
            return "no_params"

        # 提取参数名并排序
        param_names = sorted(params.keys())
        return "_".join(param_names)

    def save_standardized_module(
        self, standardized_instruction: Dict[str, Any], code: str, metadata: dict | None = None
    ) -> str | None:
        task_type = standardized_instruction.get("task_type", "general")
        action = standardized_instruction.get("action", "process")
        target = standardized_instruction.get("target", "")

        # 生成语义哈希用于区分
        semantic_hash = self._generate_semantic_hash(target)[:6]
        param_signature = self._generate_param_signature(
            standardized_instruction.get("required_parameters", {})
        )

        # 更具区分性的文件名
        module_id = (
            f"enhanced_{task_type}_{action}_{semantic_hash}_{param_signature}_{int(time.time())}"
        )

        # 保存主记录
        result = self._save_module_record(module_id, standardized_instruction, code, metadata)

        if result:
            # 建立多个索引以提高命中率
            self._create_multiple_indexes(module_id, task_type, action, standardized_instruction)

            # 更新动作聚类（确保调用标准化）
            self._update_action_clustering(action)

        return result

    def _update_action_clustering(self, action: str):
        """更新动作聚类"""
        if self.semantic_action_matcher:
            try:
                # 获取或创建动作聚类

                # 保存聚类数据
                self._save_action_clusters()

            except Exception:
                pass

    def _save_module_record(
        self,
        module_id: str,
        standardized_instruction: Dict[str, Any],
        code: str,
        metadata: dict | None = None,
    ) -> str | None:
        """完整的模块记录保存实现"""

        task_type = standardized_instruction.get("task_type", "general")
        action = standardized_instruction.get("action", "process")
        target = standardized_instruction.get("target", "")

        # 生成主缓存键
        primary_key = hashlib.md5(f"{task_type}_{action}".encode()).hexdigest()
        file_path = self.modules_dir / f"{module_id}.py"

        try:
            # 保存代码文件
            AIForgePathManager.safe_write_file(
                Path(file_path), code, fallback_dir="appropriate_dir"
            )

            # 生成语义特征
            semantic_hash = None
            intent_category = None
            param_signature = None

            if self.semantic_enabled:
                semantic_hash = self._generate_semantic_hash(target)
                intent_category = self._extract_intent_category(target)
                params = standardized_instruction.get("required_parameters", {})
                param_signature = self._generate_param_signature(params)

            # 构建完整元数据
            extended_metadata = {
                "standardized_instruction": standardized_instruction,
                "task_type": task_type,
                "action": action,
                "target": target,
                "cache_key": primary_key,
                "is_standardized": True,
                "created_at": time.time(),
                "semantic_features": (
                    self._extract_semantic_features(target) if self.semantic_enabled else []
                ),
                **(metadata or {}),
            }

            # 保存到数据库
            current_time = time.time()
            with self._lock:
                self.CodeModule.create(
                    module_id=module_id,
                    instruction_hash=primary_key,
                    file_path=str(file_path),
                    created_at=current_time,
                    last_used=current_time,
                    metadata=json.dumps(extended_metadata),
                    semantic_hash=semantic_hash,
                    intent_category=intent_category,
                    param_signature=param_signature,
                    task_type=task_type,
                    is_parameterized=bool(standardized_instruction.get("required_parameters")),
                    parameter_count=len(standardized_instruction.get("required_parameters", {})),
                )

            # 更新向量存储
            if self.semantic_enabled:
                self._update_vector_storage(
                    module_id,
                    target,
                    intent_category,
                    standardized_instruction.get("required_parameters", {}),
                )

            return module_id

        except Exception:
            if file_path.exists():
                file_path.unlink()
            return None

    def _create_multiple_indexes(
        self, module_id: str, task_type: str, action: str, standardized_instruction: Dict[str, Any]
    ):
        """创建多个索引以提高匹配率"""
        try:
            with self._lock:
                # 创建任务类型索引
                type_key = hashlib.md5(task_type.encode()).hexdigest()
                self._create_index_record(module_id, type_key, "task_type")

                # 创建动作索引
                action_key = hashlib.md5(action.encode()).hexdigest()
                self._create_index_record(module_id, action_key, "action")

                # 创建语义特征索引
                target = standardized_instruction.get("target", "")
                if target and self.semantic_enabled:
                    semantic_features = self._extract_semantic_features(target)
                    for feature in semantic_features[:3]:  # 取前3个特征
                        feature_key = hashlib.md5(feature.encode()).hexdigest()
                        self._create_index_record(module_id, feature_key, "semantic_feature")

        except Exception:
            pass

    def _create_index_record(self, module_id: str, index_key: str, index_type: str):
        """创建索引记录的辅助方法"""
        try:
            if not hasattr(self, "_module_indexes"):
                self._module_indexes = defaultdict(list)

            self._module_indexes[index_key].append(
                {"module_id": module_id, "index_type": index_type, "created_at": time.time()}
            )

        except Exception:
            pass

    def _rank_and_deduplicate_results(self, results: List[tuple]) -> List[Any]:
        """对结果进行排序和去重"""
        strategy_priority = {
            "exact": 10,  # 精确匹配最高优先级
            "action_cluster": 9,  # 动作聚类匹配（新增）
            "task_type": 8,  # 任务类型匹配
            "semantic": 6,  # 语义匹配
            "action_similarity": 4,  # 动作相似度匹配
        }

        # 去重（基于module_id）
        seen_modules = set()
        ranked_results = []

        for result_tuple in results:
            if len(result_tuple) >= 2:
                module_data = result_tuple[0]
                strategy = result_tuple[1]
                score = result_tuple[2] if len(result_tuple) > 2 else 1.0

                if len(module_data) >= 4:
                    module_id, file_path, success_count, failure_count = module_data[:4]
                else:
                    continue
            else:
                continue

            if module_id not in seen_modules:
                seen_modules.add(module_id)
                # 计算综合分数：策略优先级 + 成功率 + 相似度分数
                total_attempts = success_count + failure_count
                success_rate = success_count / total_attempts if total_attempts > 0 else 0.5

                # 为聚类匹配增加额外加分
                cluster_bonus = 0.2 if strategy == "action_cluster" else 0.0

                final_score = (
                    strategy_priority.get(strategy, 1)
                    + success_rate
                    + (score - 1.0) * 0.5
                    + cluster_bonus
                )

                ranked_results.append(
                    (module_id, file_path, success_count, failure_count, final_score)
                )

        # 按综合分数排序
        ranked_results.sort(key=lambda x: x[4], reverse=True)

        # 返回原格式
        return [(m[0], m[1], m[2], m[3]) for m in ranked_results]

    def _update_vector_storage(
        self, module_id: str, target: str, intent_category: str, params: Dict
    ):
        """更新向量存储"""
        if not self.semantic_enabled:
            return

        try:

            if not self.use_lightweight_mode:
                # 标准模式：生成并存储向量
                vector = self.semantic_model.encode(target)
                self.command_vectors[module_id] = vector
            else:
                # 轻量级模式：只存储文本特征
                features = self._extract_semantic_features(target)
                self.command_vectors[module_id] = {"text": target, "features": features}

            # 更新意图聚类
            if intent_category:
                if intent_category not in self.intent_clusters:
                    self.intent_clusters[intent_category] = []
                self.intent_clusters[intent_category].append(module_id)

            # 更新参数模板
            param_signature = self._generate_param_signature(params)
            if param_signature not in self.param_templates:
                self.param_templates[param_signature] = []
            self.param_templates[param_signature].append(module_id)

            # 初始化使用统计
            self.usage_stats[module_id] = {"hits": 0, "misses": 0, "last_used": time.time()}

            # 保存向量存储
            self._save_vector_storage()

        except Exception:
            pass

    def _save_vector_storage(self):
        """保存向量存储到文件"""
        try:
            vector_data = {
                "command_vectors": self.command_vectors,
                "intent_clusters": dict(self.intent_clusters),
                "param_templates": dict(self.param_templates),
                "usage_stats": self.usage_stats,
            }

            with open(self.vector_store_path, "wb") as f:
                pickle.dump(vector_data, f)

        except Exception:
            pass
