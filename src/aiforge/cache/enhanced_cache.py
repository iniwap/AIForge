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


class EnhancedStandardizedCache(AiForgeCodeCache):
    """增强的标准化缓存"""

    def __init__(self, cache_dir: Path, config: dict | None = None):
        # 扩展配置以支持语义匹配功能
        enhanced_config = config or {}
        enhanced_config.update(
            {
                "semantic_threshold": enhanced_config.get("semantic_threshold", 0.6),
                "enable_semantic_matching": enhanced_config.get("enable_semantic_matching", True),
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
        """初始化语义分析组件"""
        if not self.config.get("enable_semantic_matching", True):
            self.semantic_enabled = False
            return

        # 标记为延迟加载模式
        self.semantic_enabled = True
        self._semantic_model = None
        self._tfidf = None
        self.fitted_tfidf = False
        print("[DEBUG] 语义匹配组件已启用（延迟加载模式）")

    @property
    def semantic_model(self):
        """延迟加载语义模型 - 指定缓存目录"""
        if self._semantic_model is None:
            try:
                print("[DEBUG] 正在加载语义模型...")
                from sentence_transformers import SentenceTransformer
                import os

                # 指定缓存目录
                cache_folder = os.path.expanduser("~/.aiforge_cache/sentence_transformers")
                os.makedirs(cache_folder, exist_ok=True)

                self._semantic_model = SentenceTransformer(
                    "paraphrase-MiniLM-L6-v2", cache_folder=cache_folder
                )
                print("[DEBUG] 语义模型加载完成")
            except ImportError:
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
        """增强的缓存模块查找"""
        # 1. 优先检查模板扩展（保留原有功能）
        template_match = self.extension_manager.find_template_match(standardized_instruction)
        if template_match:
            template_results = self._get_template_cached_modules(
                template_match, standardized_instruction
            )
            if template_results:
                return template_results

        # 2. 标准化指令匹配
        cache_key = standardized_instruction.get("cache_key")
        task_type = standardized_instruction.get("task_type", "general")
        action = standardized_instruction.get("action", "process")
        # target = standardized_instruction.get("target", "")

        print(f"[DEBUG] 增强缓存查找: task_type={task_type}, action={action}")

        results = []

        # 策略1: 精确匹配cache_key
        if cache_key:
            exact_matches = self._get_modules_by_key(cache_key)
            results.extend([(m, "exact") for m in exact_matches])

        # 策略2: 任务类型+查询动作匹配（保留原有逻辑）
        if task_type == "data_fetch" and action == "search":
            query_action_key = f"{task_type}_查询"
            query_action_hash = hashlib.md5(query_action_key.encode()).hexdigest()
            query_matches = self._get_modules_by_key(query_action_hash)
            results.extend([(m, "query_action") for m in query_matches])

        # 策略3: 任务类型+动作匹配
        type_action_key = f"{task_type}_{action}"
        type_action_hash = hashlib.md5(type_action_key.encode()).hexdigest()
        type_matches = self._get_modules_by_key(type_action_hash)
        results.extend([(m, "type_action") for m in type_matches])

        # 策略4: 通用任务类型匹配
        general_key = f"{task_type}_general"
        general_hash = hashlib.md5(general_key.encode()).hexdigest()
        general_matches = self._get_modules_by_key(general_hash)
        results.extend([(m, "general") for m in general_matches])

        # 策略5: 语义相似度匹配（新增）
        if self.semantic_enabled and not results:
            semantic_matches = self._get_semantic_matches(standardized_instruction)
            results.extend([(m, "semantic") for m, score in semantic_matches])

        # 策略6: 参数结构匹配（新增）
        if not results:
            param_matches = self._get_parameter_matches(standardized_instruction)
            results.extend([(m, "parameter") for m, score in param_matches])

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
        """获取语义相似的模块"""
        if not self.semantic_enabled:
            return []

        target = standardized_instruction.get("target", "")
        task_type = standardized_instruction.get("task_type", "")

        # 生成查询向量
        try:
            query_vector = self.semantic_model.encode(target)
        except Exception as e:
            print(f"[DEBUG] 生成查询向量失败: {e}")
            return []

        semantic_matches = []

        with self._lock:
            try:
                all_modules = self.CodeModule.select()

                for module in all_modules:
                    try:
                        # 获取缓存的向量
                        if module.module_id in self.command_vectors:
                            cached_vector = self.command_vectors[module.module_id]
                        else:
                            # 重新生成向量
                            metadata = json.loads(module.metadata)
                            cached_target = metadata.get("standardized_instruction", {}).get(
                                "target", ""
                            )
                            if not cached_target:
                                continue

                            try:
                                cached_vector = self.semantic_model.encode(cached_target)
                                # 缓存向量以备后用
                                self.command_vectors[module.module_id] = cached_vector
                            except Exception:
                                continue

                        # 计算语义相似度
                        similarity = self._compute_semantic_similarity(query_vector, cached_vector)

                        # 任务类型匹配加分
                        cached_task_type = json.loads(module.metadata).get("task_type", "")
                        if task_type == cached_task_type:
                            similarity += 0.1  # 任务类型匹配加分

                        if similarity > self.config.get("semantic_threshold", 0.6):
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
        return semantic_matches[:5]  # 返回前5个最相似的

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
        # 按策略优先级排序: exact > query_action > type_action > semantic > parameter > general
        strategy_priority = {
            "exact": 6,
            "query_action": 5,
            "type_action": 4,
            "semantic": 3,
            "parameter": 2,
            "general": 1,
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

    # 继续添加其他必要的方法...
    def save_standardized_module(
        self, standardized_instruction: Dict[str, Any], code: str, metadata: dict | None = None
    ) -> str | None:
        """保存标准化模块"""
        if not self._validate_code(code):
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

            # 生成并存储向量
            vector = self.semantic_model.encode(target)
            self.command_vectors[module_id] = vector
            print(f"[DEBUG] 向量生成成功")

            # 更新意图聚类
            if intent_category:
                self.intent_clusters[intent_category].append(module_id)
                print(f"[DEBUG] 意图聚类更新成功: {intent_category}")

            # 更新参数模板
            param_signature = self._generate_param_signature(params)
            print(f"[DEBUG] 生成参数签名: {param_signature}")
            self.param_templates[param_signature].append(module_id)
            print(f"[DEBUG] 参数模板更新成功")

            # 初始化使用统计
            self.usage_stats[module_id] = {"hits": 0, "misses": 0, "last_used": time.time()}

            # 保存向量存储
            self._save_vector_storage()

        except Exception as e:
            print(f"[DEBUG] 更新向量存储失败: {e}")

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
        except Exception as e:
            print(f"[DEBUG] 保存向量存储失败: {e}")

    def _validate_code(self, code: str) -> bool:
        """验证代码有效性"""
        if not code or len(code.strip()) < 10:
            return False

        try:
            compile(code, "<string>", "exec")
            return True
        except SyntaxError:
            return False
