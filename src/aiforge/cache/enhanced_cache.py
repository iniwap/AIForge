import hashlib
import json
import os
import pickle
import time
from typing import Dict, List, Any
from collections import defaultdict
from pathlib import Path
from peewee import Case

from ..extensions.extension_manager import ExtensionManager
from .code_cache import AiForgeCodeCache
from ..utils.code_validator import CodeValidator
from .semantic_action_matcher import SemanticActionMatcher


class EnhancedStandardizedCache(AiForgeCodeCache):
    """增强的标准化缓存"""

    def __init__(self, cache_dir: Path, config: dict | None = None):
        # 扩展配置以支持语义匹配功能
        enhanced_config = config or {}
        enhanced_config.update(
            {
                "semantic_threshold": enhanced_config.get("semantic_threshold", 0.6),
                "enable_semantic_matching": enhanced_config.get("enable_semantic_matching", True),
                "use_lightweight_semantic": enhanced_config.get("use_lightweight_semantic", False),
            }
        )

        # 调用父类初始化，复用基础缓存功能
        super().__init__(cache_dir, enhanced_config)

        # 向量存储路径（增强功能特有）
        self.vector_store_path = self.cache_dir / "vector_store.pkl"

        # 初始化扩展管理器
        self.extension_manager = ExtensionManager()
        self._load_builtin_extensions()

        # 初始化语义分析组件（延迟加载）
        self._init_semantic_components()

        # 加载向量存储
        self._load_vector_storage()

    def _load_builtin_extensions(self):
        """加载内置扩展"""
        # 保留原有扩展加载逻辑
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
        """初始化语义分析组件 - 支持轻量级模式"""
        if not self.config.get("enable_semantic_matching", True):
            self.semantic_enabled = False
            return

        # 检查是否启用轻量级模式
        self.use_lightweight_mode = self.config.get("use_lightweight_semantic", False)

        if self.use_lightweight_mode:
            # 轻量级模式：不需要外部依赖
            self.semantic_enabled = True
            self._semantic_model = None
            self._tfidf = None
            self.fitted_tfidf = False
            print("[DEBUG] 轻量级语义匹配组件已启用")
        else:
            # 标准模式：延迟加载重型模型
            self.semantic_enabled = True
            self._semantic_model = None
            self._tfidf = None
            self.fitted_tfidf = False
            print("[DEBUG] 语义匹配组件已启用（延迟加载模式）")

    @property
    def semantic_model(self):
        """延迟加载语义模型 - 优先使用内置模型"""
        if self._semantic_model is None:
            try:
                print("[DEBUG] 正在加载语义模型...")
                from sentence_transformers import SentenceTransformer
                from ..models.model_manager import ModelManager

                # 使用模型管理器获取模型路径
                model_manager = ModelManager()
                model_path = model_manager.get_model_path("paraphrase-MiniLM-L6-v2")

                # 加载模型
                self._semantic_model = SentenceTransformer(model_path)
                print("[DEBUG] 语义模型加载完成")

            except ImportError:
                print("[DEBUG] sentence_transformers 未安装，禁用语义匹配")
                self.semantic_enabled = False
                return None
            except Exception as e:
                print(f"[DEBUG] 语义模型加载失败: {e}")
                self.semantic_enabled = False
                return None

        return self._semantic_model

    @property
    def tfidf(self):
        """延迟加载 TF-IDF 向量化器"""
        if self._tfidf is None:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer

                self._tfidf = TfidfVectorizer(max_features=1000, stop_words="english")
            except ImportError:
                return None
        return self._tfidf

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
            except Exception as e:
                print(f"[DEBUG] 加载向量存储失败: {e}")
                self._init_empty_vectors()
        else:
            self._init_empty_vectors()

    def _init_empty_vectors(self):
        """初始化空向量存储"""
        self.command_vectors = {}
        self.intent_clusters = defaultdict(list)
        self.param_templates = defaultdict(list)
        self.usage_stats = {}

    def _load_cache_index(self):
        """加载缓存索引和向量存储"""
        # 向量存储
        if os.path.exists(self.vector_store_path):
            try:
                with open(self.vector_store_path, "rb") as f:
                    vector_data = pickle.load(f)
                    self.command_vectors = vector_data.get("command_vectors", {})
                    self.intent_clusters = vector_data.get("intent_clusters", defaultdict(list))
                    self.param_templates = vector_data.get("param_templates", defaultdict(list))
                    self.usage_stats = vector_data.get("usage_stats", {})
            except Exception as e:
                print(f"[DEBUG] 加载向量存储失败: {e}")
                self._init_empty_vectors()
        else:
            self._init_empty_vectors()

        # 重建TF-IDF模型
        if self.semantic_enabled:
            self._rebuild_tfidf_model()

    def _rebuild_tfidf_model(self):
        """重建TF-IDF模型"""
        try:
            with self._lock:
                all_modules = self.CodeModule.select()
                commands = []
                for module in all_modules:
                    try:
                        metadata = json.loads(module.metadata)
                        original_command = metadata.get("standardized_instruction", {}).get(
                            "target", ""
                        )
                        if original_command:
                            commands.append(original_command)
                    except Exception:
                        continue

                if commands and len(commands) > 1:
                    self.tfidf.fit(commands)
                    self.fitted_tfidf = True
                    print(f"[DEBUG] TF-IDF模型重建完成，训练样本: {len(commands)}")
        except Exception as e:
            print(f"[DEBUG] TF-IDF模型重建失败: {e}")

    def get_cached_modules_by_standardized_instruction(
        self, standardized_instruction: Dict[str, Any]
    ) -> List[Any]:
        """基于语义聚类的缓存模块查找"""

        if self.should_cleanup():
            self.cleanup()

        task_type = standardized_instruction.get("task_type", "general")
        action = standardized_instruction.get("action", "process")

        # 使用语义动作匹配器
        if not hasattr(self, "action_matcher"):
            self.action_matcher = SemanticActionMatcher(self)

        # 获取动作的语义聚类
        action_cluster = self.action_matcher.get_action_cluster(action)

        print(f"[DEBUG] 语义缓存查找: task_type={task_type}, action_cluster={action_cluster}")

        results = []

        # 策略1: 精确任务类型 + 语义聚类匹配
        cluster_key = f"{task_type}_{action_cluster}"
        cluster_hash = hashlib.md5(cluster_key.encode()).hexdigest()
        cluster_matches = self._get_modules_by_key(cluster_hash)

        # 对聚类匹配进行二次验证
        validated_matches = self._validate_cluster_matches(
            cluster_matches, action, standardized_instruction
        )
        results.extend([(m, "semantic_cluster") for m in validated_matches])

        # 策略2: 如果聚类匹配失败，尝试语义相似度匹配
        if not results and self.semantic_enabled:
            semantic_matches = self._get_semantic_matches(standardized_instruction)
            results.extend([(m, "semantic_similarity") for m, score in semantic_matches])

        return self._rank_and_deduplicate_results(results)

    def _validate_cluster_matches(
        self, matches: List[Any], query_action: str, standardized_instruction: Dict[str, Any]
    ) -> List[Any]:
        """验证聚类匹配的准确性"""
        validated = []

        for match in matches:
            module_id, file_path, success_count, failure_count = match

            try:
                # 加载模块元数据
                with self._lock:
                    module_record = self.CodeModule.get(self.CodeModule.module_id == module_id)
                    metadata = json.loads(module_record.metadata)

                cached_instruction = metadata.get("standardized_instruction", {})
                cached_action = cached_instruction.get("action", "")

                # 计算动作相似度
                action_similarity = self._compute_action_similarity(query_action, cached_action)

                # 只有相似度足够高才认为匹配
                if action_similarity > 0.7:  # 可调节阈值
                    validated.append(match)
                    print(
                        f"[DEBUG] 聚类验证通过: {query_action} <-> {cached_action} (相似度: {action_similarity:.3f})"
                    )
                else:
                    print(
                        f"[DEBUG] 聚类验证失败: {query_action} <-> {cached_action} (相似度: {action_similarity:.3f})"
                    )

            except Exception as e:
                print(f"[DEBUG] 验证模块 {module_id} 时出错: {e}")
                continue

        return validated

    def _compute_action_similarity(self, action1: str, action2: str) -> float:
        """计算两个动作的语义相似度"""
        if not hasattr(self, "action_matcher"):
            self.action_matcher = SemanticActionMatcher(self)

        vector1 = self.action_matcher._get_action_vector(action1)
        vector2 = self.action_matcher._get_action_vector(action2)

        return self.action_matcher._compute_vector_similarity(vector1, vector2)

    def _validate_semantic_relevance(
        self, modules: List[Any], query_target: str, query_action: str
    ) -> List[Any]:
        """验证模块与查询的语义相关性"""
        validated_modules = []

        for module_data in modules:
            module_id, file_path, success_count, failure_count = module_data

            try:
                # 加载模块元数据
                with self._lock:
                    module_record = self.CodeModule.get(self.CodeModule.module_id == module_id)
                    metadata = json.loads(module_record.metadata)

                cached_instruction = metadata.get("standardized_instruction", {})
                cached_target = cached_instruction.get("target", "")
                cached_action = cached_instruction.get("action", "")

                # 严格的动作匹配
                if not self._actions_are_compatible(query_action, cached_action):
                    print(f"[DEBUG] 动作不兼容: {query_action} vs {cached_action}")
                    continue

                # 语义相关性检查
                if not self._targets_are_semantically_related(query_target, cached_target):
                    print(f"[DEBUG] 语义不相关: {query_target} vs {cached_target}")
                    continue

                validated_modules.append(module_data)

            except Exception as e:
                print(f"[DEBUG] 验证模块 {module_id} 失败: {e}")
                continue

        return validated_modules

    def _actions_are_compatible(self, query_action: str, cached_action: str) -> bool:
        """检查动作是否兼容"""
        # 定义动作兼容性映射
        action_groups = {
            "weather": ["获取天气信息", "fetch_weather", "天气查询"],
            "news": ["获取新闻", "获取实时新闻", "新闻查询", "fetch_news"],
            "data": ["数据获取", "数据查询", "fetch_data"],
        }

        query_group = None
        cached_group = None

        for group, actions in action_groups.items():
            if any(action in query_action for action in actions):
                query_group = group
            if any(action in cached_action for action in actions):
                cached_group = group

        # 只有同组动作才兼容
        return query_group == cached_group and query_group is not None

    def _targets_are_semantically_related(self, query_target: str, cached_target: str) -> bool:
        """检查目标是否语义相关"""
        # 关键词分组
        keyword_groups = {
            "weather": ["天气", "温度", "气温", "weather", "temperature"],
            "news": ["新闻", "消息", "资讯", "news", "information"],
            "finance": ["股票", "股价", "金融", "stock", "finance"],
        }

        query_keywords = set()
        cached_keywords = set()

        query_lower = query_target.lower()
        cached_lower = cached_target.lower()

        for group, keywords in keyword_groups.items():
            if any(keyword in query_lower for keyword in keywords):
                query_keywords.add(group)
            if any(keyword in cached_lower for keyword in keywords):
                cached_keywords.add(group)

        # 必须有共同的关键词组
        return bool(query_keywords & cached_keywords)

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

    def _get_semantic_matches(self, standardized_instruction: Dict[str, Any]) -> List[tuple]:
        """获取语义相似的模块 - 支持轻量级模式"""
        if not self.semantic_enabled:
            return []

        target = standardized_instruction.get("target", "")
        task_type = standardized_instruction.get("task_type", "")

        semantic_matches = []

        with self._lock:
            try:
                all_modules = self.CodeModule.select()

                for module in all_modules:
                    try:
                        metadata = json.loads(module.metadata)
                        cached_target = metadata.get("standardized_instruction", {}).get(
                            "target", ""
                        )
                        if not cached_target:
                            continue

                        # 根据模式选择相似度计算方法
                        if self.use_lightweight_mode:
                            # 轻量级模式：直接文本相似度计算
                            similarity = self._compute_semantic_similarity_lightweight(
                                target, cached_target
                            )
                        else:
                            # 标准模式：使用向量相似度
                            if module.module_id in self.command_vectors:
                                cached_vector = self.command_vectors[module.module_id]
                            else:
                                try:
                                    query_vector = self.semantic_model.encode(target)
                                    cached_vector = self.semantic_model.encode(cached_target)
                                    self.command_vectors[module.module_id] = cached_vector
                                except Exception:
                                    continue

                            similarity = self._compute_semantic_similarity(
                                query_vector, cached_vector
                            )

                        # 任务类型匹配加分
                        cached_task_type = metadata.get("task_type", "")
                        if task_type == cached_task_type:
                            similarity += 0.1

                        # 调整阈值：轻量级模式使用较低阈值
                        threshold = (
                            0.4
                            if self.use_lightweight_mode
                            else self.config.get("semantic_threshold", 0.6)
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

        # 按相似度排序
        semantic_matches.sort(key=lambda x: x[1], reverse=True)
        return semantic_matches[:5]

    def _get_parameter_matches(self, standardized_instruction: Dict[str, Any]) -> List[tuple]:
        """获取参数结构相似的模块"""
        current_params = standardized_instruction.get("required_parameters", {})
        if not current_params:
            current_params = standardized_instruction.get("parameters", {})

        param_matches = []

        with self._lock:
            try:
                all_modules = self.CodeModule.select()

                for module in all_modules:
                    try:
                        metadata = json.loads(module.metadata)
                        cached_instruction = metadata.get("standardized_instruction", {})
                        cached_params = cached_instruction.get("required_parameters", {})
                        if not cached_params:
                            cached_params = cached_instruction.get("parameters", {})

                        # 计算参数相似度
                        param_similarity = self._calculate_parameter_similarity(
                            current_params, cached_params
                        )

                        if param_similarity > 0.5:  # 参数相似度阈值
                            param_matches.append(
                                (
                                    (
                                        module.module_id,
                                        module.file_path,
                                        module.success_count,
                                        module.failure_count,
                                    ),
                                    param_similarity,
                                )
                            )

                    except Exception:
                        continue

            except Exception:
                pass

        # 按相似度排序
        param_matches.sort(key=lambda x: x[1], reverse=True)
        return param_matches[:3]  # 返回前3个最相似的

    def _rank_and_deduplicate_results(self, results: List[tuple]) -> List[Any]:
        """对结果进行排序和去重"""
        strategy_priority = {
            "exact": 10,  # 精确匹配最高优先级
            "query_action": 8,  # 查询动作匹配
            "type_action": 6,  # 类型动作匹配
            "semantic": 4,  # 语义匹配
            "parameter": 2,  # 参数匹配
            "general": 1,  # 通用匹配最低优先级
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
                final_score = (
                    strategy_priority.get(strategy, 1) + success_rate + (score - 1.0) * 0.5
                )

                ranked_results.append(
                    (module_id, file_path, success_count, failure_count, final_score)
                )

        # 按综合分数排序
        ranked_results.sort(key=lambda x: x[4], reverse=True)

        # 返回原格式
        return [(m[0], m[1], m[2], m[3]) for m in ranked_results]

    def save_standardized_module(
        self, standardized_instruction: Dict[str, Any], code: str, metadata: dict | None = None
    ) -> str | None:
        """保存标准化模块"""
        if not CodeValidator.validate_code(code):
            return None

        task_type = standardized_instruction.get("task_type", "general")
        action = standardized_instruction.get("action", "process")
        target = standardized_instruction.get("target", "")

        # 生成缓存键
        cache_key = hashlib.md5(f"{task_type}_{action}".encode()).hexdigest()

        print(f"[DEBUG] 保存增强模块: task_type={task_type}, action={action}")

        module_id = f"enhanced_{task_type}_{action}_{int(time.time())}"
        file_path = self.modules_dir / f"{module_id}.py"

        try:
            # 保存代码文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            # 生成语义特征
            semantic_hash = None
            intent_category = None
            param_signature = None

            if self.semantic_enabled:
                # 生成语义哈希
                semantic_hash = self._generate_semantic_hash(target)
                # 提取意图分类
                intent_category = self._extract_intent_category(target)
                # 生成参数签名
                params = standardized_instruction.get("required_parameters", {})
                if not params:
                    params = standardized_instruction.get("parameters", {})
                param_signature = self._generate_param_signature(params)

            # 扩展元数据
            extended_metadata = {
                "standardized_instruction": standardized_instruction,
                "task_type": task_type,
                "action": action,
                "cache_key": cache_key,
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
                    instruction_hash=cache_key,
                    file_path=str(file_path),
                    created_at=current_time,
                    last_used=current_time,
                    metadata=json.dumps(extended_metadata),
                    semantic_hash=semantic_hash,
                    intent_category=intent_category,
                    param_signature=param_signature,
                )

                # 更新向量存储
                if self.semantic_enabled:
                    self._update_vector_storage(module_id, target, intent_category, params)
                    # 在向量存储更新完成后，检查是否需要重新聚类
                    if hasattr(self, "action_matcher") and len(self.command_vectors) % 10 == 0:
                        self.action_matcher.update_action_clusters_from_usage()

            print(f"[DEBUG] 增强模块保存成功: {module_id}")
            return module_id

        except Exception as e:
            print(f"[DEBUG] 增强模块保存失败: {e}")
            if file_path.exists():
                file_path.unlink()
            return None

    def _generate_semantic_hash(self, target: str) -> str:
        """生成语义哈希"""
        if not target or not self.semantic_enabled:
            return None

        try:
            # 提取关键词并生成稳定哈希
            features = self._extract_semantic_features(target)
            content = "_".join(sorted(features[:5]))  # 取前5个特征
            return hashlib.md5(content.encode()).hexdigest()[:16]
        except Exception:
            return None

    def _extract_semantic_features(self, text: str) -> List[str]:
        """提取语义特征"""
        if not text:
            return []

        # 简化的特征提取
        import re

        # 修复：去掉多余的反斜杠
        words = re.findall(r"\w+", text.lower())

        # 过滤停用词
        stop_words = {
            "的",
            "是",
            "在",
            "了",
            "和",
            "与",
            "或",
            "但",
            "如果",
            "那么",
            "这",
            "那",
            "我",
            "你",
            "他",
        }
        features = [word for word in words if len(word) > 1 and word not in stop_words]

        return features[:10]  # 返回前10个特征

    def _compute_semantic_similarity(self, vec1, vec2):
        """计算语义向量相似度"""
        try:
            import numpy as np

            # 计算余弦相似度
            dot_product = np.dot(vec1, vec2)
            norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
            if norm_product == 0:
                return 0.0
            return dot_product / norm_product
        except Exception:
            return 0.0

    def _calculate_parameter_similarity(self, params1: Dict, params2: Dict) -> float:
        """计算参数结构相似度"""
        if not params1 or not params2:
            return 0.0

        keys1, keys2 = set(params1.keys()), set(params2.keys())

        # 参数名相似度
        intersection = len(keys1 & keys2)
        union = len(keys1 | keys2)

        key_similarity = intersection / union if union > 0 else 0.0

        # 参数值类型相似度
        type_matches = 0
        total_comparisons = 0

        for key in keys1 & keys2:
            val1 = params1[key]
            val2 = params2[key]

            if isinstance(val1, dict) and isinstance(val2, dict):
                type1 = val1.get("type", "")
                type2 = val2.get("type", "")
                if type1 == type2:
                    type_matches += 1
                total_comparisons += 1

        type_similarity = type_matches / total_comparisons if total_comparisons > 0 else 0.0

        # 综合相似度
        return 0.6 * key_similarity + 0.4 * type_similarity

    def _extract_intent_category(self, target: str) -> str:
        """提取意图分类"""
        if not target:
            return "general"

        # 基于关键词的简单意图分类
        intent_keywords = {
            "calculation": ["计算", "算", "求", "平方", "和", "平均"],
            "data_processing": ["处理", "分析", "排序", "筛选", "统计"],
            "file_operation": ["文件", "读取", "保存", "写入", "导入", "导出"],
            "web_request": ["获取", "下载", "请求", "爬取", "搜索"],
            "text_processing": ["文本", "字符串", "替换", "提取", "解析"],
        }

        target_lower = target.lower()
        for intent, keywords in intent_keywords.items():
            if any(keyword in target_lower for keyword in keywords):
                return intent

        return "general"

    def _generate_param_signature(self, params: Dict) -> str:
        """生成参数签名"""
        if not params:
            return "no_params"

        # 生成参数结构签名
        param_keys = sorted(params.keys())
        return "_".join(param_keys)

    def _update_vector_storage(
        self, module_id: str, target: str, intent_category: str, params: Dict
    ):
        """更新向量存储"""
        if not self.semantic_enabled:
            return

        try:
            print(f"[DEBUG] 开始更新向量存储: module_id={module_id}")

            if not self.use_lightweight_mode:
                # 标准模式：生成并存储向量
                vector = self.semantic_model.encode(target)
                self.command_vectors[module_id] = vector
                print("[DEBUG] 向量生成成功")
            else:
                # 轻量级模式：只存储文本特征
                features = self._extract_semantic_features(target)
                self.command_vectors[module_id] = {"text": target, "features": features}
                print("[DEBUG] 轻量级特征提取成功")

            # 更新意图聚类
            if intent_category:
                if intent_category not in self.intent_clusters:
                    self.intent_clusters[intent_category] = []
                self.intent_clusters[intent_category].append(module_id)
                print(f"[DEBUG] 意图聚类更新成功: {intent_category}")

            # 更新参数模板
            param_signature = self._generate_param_signature(params)
            print(f"[DEBUG] 生成参数签名: {param_signature}")
            if param_signature not in self.param_templates:
                self.param_templates[param_signature] = []
            self.param_templates[param_signature].append(module_id)
            print("[DEBUG] 参数模板更新成功")

            # 初始化使用统计
            self.usage_stats[module_id] = {"hits": 0, "misses": 0, "last_used": time.time()}

            # 保存向量存储
            self._save_vector_storage()

        except Exception as e:
            print(f"[DEBUG] 更新向量存储失败: {e}")
            import traceback

            traceback.print_exc()

    def _save_vector_storage(self):
        """保存向量存储到文件"""
        try:
            vector_data = {
                "command_vectors": self.command_vectors,
                "intent_clusters": dict(self.intent_clusters),
                "param_templates": dict(self.param_templates),
                "usage_stats": self.usage_stats,
            }

            # 如果有动作匹配器，也保存聚类信息
            if hasattr(self, "action_matcher"):
                vector_data["action_clusters"] = self.action_matcher.action_clusters
                vector_data["action_vectors"] = self.action_matcher.action_vectors

            with open(self.vector_store_path, "wb") as f:
                pickle.dump(vector_data, f)

            # 定期优化聚类
            if hasattr(self, "action_matcher") and len(self.command_vectors) % 20 == 0:
                self.action_matcher.update_action_clusters_from_usage()

        except Exception as e:
            print(f"[DEBUG] 保存向量存储失败: {e}")

    def _compute_lightweight_similarity(self, text1: str, text2: str) -> float:
        """轻量级文本相似度计算 - 增强语义理解"""
        if not text1 or not text2:
            return 0.0

        # 1. 关键词匹配相似度（权重最高）
        def extract_domain_keywords(text):
            domain_keywords = {
                "weather": ["天气", "温度", "气温", "weather", "temperature", "wttr"],
                "news": ["新闻", "消息", "资讯", "news", "information", "报道"],
                "finance": ["股票", "股价", "金融", "stock", "finance", "价格"],
            }

            text_lower = text.lower()
            found_domains = set()

            for domain, keywords in domain_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    found_domains.add(domain)

            return found_domains

        domains1 = extract_domain_keywords(text1)
        domains2 = extract_domain_keywords(text2)

        # 如果领域不匹配，直接返回低相似度
        if domains1 and domains2 and not (domains1 & domains2):
            return 0.1  # 给一个很低的分数，基本不匹配

        # 2. 词汇重叠相似度
        def preprocess_text(text):
            import re

            text = text.lower()
            chinese_chars = re.findall(r"[\\u4e00-\\u9fff]", text)
            english_words = re.findall(r"[a-zA-Z]+", text)
            return chinese_chars + english_words

        words1 = set(preprocess_text(text1))
        words2 = set(preprocess_text(text2))

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)
        jaccard_similarity = intersection / union if union > 0 else 0.0

        # 3. 综合评分（领域匹配权重更高）
        domain_similarity = 1.0 if (domains1 & domains2) else 0.0

        final_similarity = 0.7 * domain_similarity + 0.3 * jaccard_similarity

        return min(final_similarity, 1.0)

    def _compute_semantic_similarity_lightweight(self, text1: str, text2: str) -> float:
        """轻量级语义相似度计算的统一接口"""
        return self._compute_lightweight_similarity(text1, text2)

    def update_action_clusters_from_usage(self):
        """基于使用统计动态优化动作聚类"""

        print("[DEBUG] 开始基于使用统计优化动作聚类")

        # 收集所有已缓存的动作及其统计信息
        all_actions = []
        with self._lock:
            try:
                modules = self.cache.CodeModule.select()
                for module in modules:
                    try:
                        metadata = json.loads(module.metadata)
                        standardized_instruction = metadata.get("standardized_instruction", {})
                        action = standardized_instruction.get("action", "")

                        if action:
                            success_rate = module.success_count / max(
                                1, module.success_count + module.failure_count
                            )
                            all_actions.append(
                                {
                                    "action": action,
                                    "module_id": module.module_id,
                                    "success_count": module.success_count,
                                    "failure_count": module.failure_count,
                                    "success_rate": success_rate,
                                    "total_usage": module.success_count + module.failure_count,
                                }
                            )
                    except Exception as e:
                        print(f"[DEBUG] 解析模块元数据失败: {e}")
                        continue
            except Exception as e:
                print(f"[DEBUG] 查询缓存模块失败: {e}")
                return

        if len(all_actions) < 2:
            print("[DEBUG] 动作数量不足，跳过聚类优化")
            return

        print(f"[DEBUG] 收集到 {len(all_actions)} 个动作，开始重新聚类")

        # 基于成功率和使用频率重新计算聚类
        self._recompute_clusters_with_weights(all_actions)

        # 清理低质量聚类
        self._cleanup_poor_clusters()

        print(f"[DEBUG] 聚类优化完成，当前聚类数: {len(self.action_clusters)}")

    def _recompute_clusters_with_weights(self, actions_with_stats: List[Dict]):
        """基于统计数据重新计算聚类"""

        # 备份当前聚类
        # old_clusters = self.action_clusters.copy()

        # 重置聚类
        self.action_clusters = {}
        cluster_counter = 0

        # 按成功率和使用频率排序，优先处理高质量动作
        sorted_actions = sorted(
            actions_with_stats, key=lambda x: (x["success_rate"], x["total_usage"]), reverse=True
        )

        for action_data in sorted_actions:
            action = action_data["action"]
            success_rate = action_data["success_rate"]
            total_usage = action_data["total_usage"]

            # 计算权重：成功率高且使用频繁的动作权重更大
            weight = success_rate * (1 + min(total_usage / 10, 2))  # 最大权重为3

            # 获取动作向量
            action_vector = self._get_action_vector(action)

            # 寻找最佳聚类
            best_cluster = None
            best_similarity = 0.0

            for cluster_id, cluster_actions in self.action_clusters.items():
                # 计算加权相似度
                weighted_similarity = self._compute_weighted_cluster_similarity(
                    action_vector, cluster_actions, weight
                )

                if (
                    weighted_similarity > best_similarity
                    and weighted_similarity > self.cluster_threshold
                ):
                    best_similarity = weighted_similarity
                    best_cluster = cluster_id

            # 决定是否加入现有聚类或创建新聚类
            if best_cluster is not None:
                self.action_clusters[best_cluster].append(action)
                print(
                    f"[DEBUG] 动作 '{action}' 加入聚类 {best_cluster} (相似度: {best_similarity:.3f})"
                )
            else:
                # 创建新聚类
                new_cluster_id = f"cluster_{cluster_counter}"
                self.action_clusters[new_cluster_id] = [action]
                cluster_counter += 1
                print(f"[DEBUG] 为动作 '{action}' 创建新聚类 {new_cluster_id}")

        # 合并相似的聚类
        self._merge_similar_clusters()

    def _get_action_vector(self, action: str):
        """获取动作向量"""
        if not hasattr(self, "action_matcher"):
            self.action_matcher = SemanticActionMatcher(self)
        return self.action_matcher._get_action_vector(action)

    def _compute_weighted_cluster_similarity(
        self, action_vector, cluster_actions: List[str], weight: float
    ) -> float:
        """计算加权聚类相似度"""
        if not cluster_actions:
            return 0.0

        similarities = []
        for cluster_action in cluster_actions:
            cluster_vector = self._get_action_vector(cluster_action)
            similarity = self._compute_vector_similarity(action_vector, cluster_vector)
            similarities.append(similarity)

        # 计算加权平均相似度
        avg_similarity = sum(similarities) / len(similarities)

        # 应用权重：高权重的动作更容易形成聚类
        weighted_similarity = avg_similarity * (0.7 + 0.3 * min(weight, 2))

        return weighted_similarity

    def _merge_similar_clusters(self):
        """合并相似的聚类"""
        merge_threshold = 0.85  # 聚类间相似度阈值

        cluster_ids = list(self.action_clusters.keys())
        merged = set()

        for i, cluster_id1 in enumerate(cluster_ids):
            if cluster_id1 in merged:
                continue

            for j, cluster_id2 in enumerate(cluster_ids[i + 1 :], i + 1):  # noqa 203
                if cluster_id2 in merged:
                    continue

                # 计算两个聚类的相似度
                similarity = self._compute_inter_cluster_similarity(
                    self.action_clusters[cluster_id1], self.action_clusters[cluster_id2]
                )

                if similarity > merge_threshold:
                    # 合并聚类
                    self.action_clusters[cluster_id1].extend(self.action_clusters[cluster_id2])
                    del self.action_clusters[cluster_id2]
                    merged.add(cluster_id2)
                    print(
                        f"[DEBUG] 合并聚类 {cluster_id2} 到 {cluster_id1} (相似度: {similarity:.3f})"
                    )

    def _compute_inter_cluster_similarity(self, cluster1: List[str], cluster2: List[str]) -> float:
        """计算两个聚类间的相似度"""
        if not cluster1 or not cluster2:
            return 0.0

        similarities = []
        for action1 in cluster1:
            for action2 in cluster2:
                vector1 = self._get_action_vector(action1)
                vector2 = self._get_action_vector(action2)
                similarity = self._compute_vector_similarity(vector1, vector2)
                similarities.append(similarity)

        return sum(similarities) / len(similarities)

    def _cleanup_poor_clusters(self):
        """清理质量差的聚类"""
        min_cluster_size = 1  # 最小聚类大小

        clusters_to_remove = []
        for cluster_id, actions in self.action_clusters.items():
            if len(actions) < min_cluster_size:
                clusters_to_remove.append(cluster_id)

        for cluster_id in clusters_to_remove:
            print(f"[DEBUG] 移除小聚类: {cluster_id}")
            del self.action_clusters[cluster_id]

    def _compute_vector_similarity(self, vector1, vector2) -> float:
        """计算向量相似度"""
        if not hasattr(self, "action_matcher"):
            self.action_matcher = SemanticActionMatcher(self)
        return self.action_matcher._compute_vector_similarity(vector1, vector2)

    def _compute_feature_similarity(self, features1: Dict, features2: Dict) -> float:
        """计算特征向量相似度"""
        all_keys = set(features1.keys()) | set(features2.keys())
        if not all_keys:
            return 0.0

        dot_product = sum(features1.get(key, 0) * features2.get(key, 0) for key in all_keys)
        norm1 = sum(v**2 for v in features1.values()) ** 0.5
        norm2 = sum(v**2 for v in features2.values()) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)
