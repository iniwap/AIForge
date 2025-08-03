from typing import Dict, List


class SemanticActionMatcher:
    """基于语义向量的动作匹配器"""

    def __init__(self, cache_instance):
        self.cache = cache_instance
        self.action_clusters = {}
        self.action_vectors = {}
        # 较低阈值（0.6-0.7）：更宽松的聚类，更多动作会被归为相似
        # 较高阈值（0.8-0.9）：更严格的聚类，只有非常相似的动作才会聚类
        self.cluster_threshold = cache_instance.config.get("action_cluster_threshold", 0.75)
        self.cluster_threshold = (
            self.cluster_threshold if 0 <= self.cluster_threshold <= 1 else 0.75
        )

    def _get_dynamic_cluster_threshold(self, action: str) -> float:
        """根据动作特征动态调整聚类阈值"""
        base_threshold = self.cluster_threshold

        # 根据动作长度调整
        if len(action) < 5:
            # 短动作降低阈值，更容易聚类
            return base_threshold - 0.1
        elif len(action) > 15:
            # 长动作提高阈值，更严格聚类
            return base_threshold + 0.1

        # 根据动作类型调整
        if any(verb in action for verb in ["获取", "查询", "搜索"]):
            # 查询类动作更容易聚类
            return base_threshold - 0.05
        elif any(verb in action for verb in ["生成", "创建", "制作"]):
            # 生成类动作更严格聚类
            return base_threshold + 0.05

        return base_threshold

    def get_action_cluster(self, action: str, source: str = "unknown") -> str:
        """获取动作所属的语义聚类，支持来源区分"""
        if not self.cache.semantic_enabled:
            return self._fallback_action_matching(action)

        # 对于 AI 生成的动作，保持原始语义
        if source == "ai_analysis":
            standardized_action = action  # 保持原样
        else:
            # 只对本地分析结果进行标准化
            standardized_action = self._standardize_action_before_clustering(action)

        # 生成动作向量（使用标准化后的动作）
        action_vector = self._get_action_vector(standardized_action)

        # 寻找最相似的聚类
        best_cluster = None
        best_similarity = 0.0

        for cluster_id, cluster_actions in self.action_clusters.items():
            cluster_similarity = self._compute_cluster_similarity(action_vector, cluster_actions)
            if cluster_similarity > best_similarity and cluster_similarity > self.cluster_threshold:
                best_similarity = cluster_similarity
                best_cluster = cluster_id

        # 如果没有找到合适的聚类，创建新聚类
        if best_cluster is None:
            best_cluster = self._create_new_cluster(standardized_action)
        else:
            # 将标准化后的动作添加到现有聚类
            self._add_to_cluster(best_cluster, standardized_action)

        return best_cluster

    def _standardize_action_before_clustering(self, action: str) -> str:
        """聚类前的动作标准化"""

        # 1. 提取语义特征
        features = self._extract_action_semantic_features(action)

        # 2. 基于语义特征生成标准化动作
        if features.get("is_retrieval", False):
            base_verb = "fetch"
        elif features.get("is_processing", False):
            base_verb = "process"
        elif features.get("is_creation", False):
            base_verb = "generate"
        elif features.get("is_interaction", False):
            base_verb = "respond"
        else:
            base_verb = "execute"

        # 3. 添加语言和复杂度标识
        language_suffix = self._get_language_suffix(action)
        complexity_suffix = self._get_complexity_suffix(action)

        # 4. 生成最终的标准化动作名
        standardized = f"{base_verb}_{language_suffix}_{complexity_suffix}"

        return standardized

    def _extract_action_semantic_features(self, action: str) -> Dict[str, bool]:
        """提取动作的语义特征"""
        action_lower = action.lower()

        # 基于语言学模式的特征提取
        retrieval_patterns = [
            "取",
            "得",
            "获",
            "查",
            "找",
            "搜",
            "get",
            "fetch",
            "find",
            "search",
            "retrieve",
        ]
        processing_patterns = [
            "析",
            "理",
            "算",
            "计",
            "process",
            "analyze",
            "compute",
            "handle",
            "transform",
        ]
        creation_patterns = [
            "生",
            "创",
            "建",
            "制",
            "产",
            "generate",
            "create",
            "build",
            "make",
            "produce",
        ]
        interaction_patterns = [
            "答",
            "应",
            "复",
            "互",
            "respond",
            "answer",
            "reply",
            "interact",
            "communicate",
        ]

        return {
            "is_retrieval": any(pattern in action_lower for pattern in retrieval_patterns),
            "is_processing": any(pattern in action_lower for pattern in processing_patterns),
            "is_creation": any(pattern in action_lower for pattern in creation_patterns),
            "is_interaction": any(pattern in action_lower for pattern in interaction_patterns),
        }

    def _get_language_suffix(self, action: str) -> str:
        """获取语言后缀"""
        has_chinese = any("\u4e00" <= char <= "\u9fff" for char in action)
        has_english = action.isascii() and any(c.isalpha() for c in action)

        if has_chinese and has_english:
            return "mixed"
        elif has_chinese:
            return "zh"
        elif has_english:
            return "en"
        else:
            return "other"

    def _get_complexity_suffix(self, action: str) -> str:
        """获取复杂度后缀"""
        word_count = len(action.split())
        char_count = len(action)

        if word_count <= 2 and char_count <= 10:
            return "simple"
        elif word_count >= 4 or char_count >= 20:
            return "complex"
        else:
            return "medium"

    def _get_action_vector(self, action: str):
        """获取动作的语义向量"""
        if action not in self.action_vectors:
            if self.cache.use_lightweight_mode:
                # 轻量级模式：使用特征向量
                self.action_vectors[action] = self._extract_action_features(action)
            else:
                # 标准模式：使用语义模型
                self.action_vectors[action] = self.cache.semantic_model.encode(action)
        return self.action_vectors[action]

    def _compute_cluster_similarity(self, action_vector, cluster_actions: List[str]) -> float:
        """计算动作与聚类的相似度"""
        if not cluster_actions:
            return 0.0

        similarities = []
        for cluster_action in cluster_actions:
            cluster_vector = self._get_action_vector(cluster_action)
            similarity = self._compute_vector_similarity(action_vector, cluster_vector)
            similarities.append(similarity)

        # 返回平均相似度
        return sum(similarities) / len(similarities)

    def _extract_action_features(self, action: str) -> Dict[str, float]:
        """基于通用语义特征的动作特征提取"""
        features = {}
        action_lower = action.lower()

        # 1. 语义动词特征
        semantic_features = self._extract_action_semantic_features(action)
        for feature_name, feature_value in semantic_features.items():
            features[feature_name] = 1.0 if feature_value else 0.0

        # 2. 语言特征
        features["is_chinese"] = (
            1.0 if any("\u4e00" <= char <= "\u9fff" for char in action) else 0.0
        )
        features["is_english"] = (
            1.0 if action.isascii() and any(c.isalpha() for c in action) else 0.0
        )
        features["is_mixed"] = (
            1.0 if features["is_chinese"] > 0 and features["is_english"] > 0 else 0.0
        )

        # 3. 结构特征
        features["has_underscore"] = 1.0 if "_" in action else 0.0
        features["word_count"] = min(len(action.split()), 5) / 5.0
        features["char_length"] = min(len(action), 20) / 20.0

        # 4. 复杂度特征
        complexity_suffix = self._get_complexity_suffix(action)
        features["complexity_simple"] = 1.0 if complexity_suffix == "simple" else 0.0
        features["complexity_medium"] = 1.0 if complexity_suffix == "medium" else 0.0
        features["complexity_complex"] = 1.0 if complexity_suffix == "complex" else 0.0

        # 5. 时效性特征
        temporal_words = [
            "实时",
            "今天",
            "当前",
            "最新",
            "real-time",
            "current",
            "today",
            "now",
            "latest",
        ]
        features["temporal"] = 1.0 if any(w in action_lower for w in temporal_words) else 0.0

        return features

    def _compute_vector_similarity(self, vector1, vector2) -> float:
        """计算向量相似度"""
        if self.cache.use_lightweight_mode:
            # 轻量级模式：特征向量相似度
            return self._compute_feature_similarity(vector1, vector2)
        else:
            # 标准模式：余弦相似度
            import numpy as np

            return float(
                np.dot(vector1, vector2) / (np.linalg.norm(vector1) * np.linalg.norm(vector2))
            )

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

    def _fallback_action_matching(self, action: str) -> str:
        """语义模型不可用时的通用回退匹配"""
        # 提取通用语义特征
        features = self._extract_action_semantic_features(action)

        # 基于语义特征进行聚类
        if features.get("is_retrieval", False):
            return "retrieval_cluster"
        elif features.get("is_processing", False):
            return "processing_cluster"
        elif features.get("is_creation", False):
            return "creation_cluster"
        elif features.get("is_interaction", False):
            return "interaction_cluster"
        else:
            # 基于语言和复杂度的细分
            language_suffix = self._get_language_suffix(action)
            complexity_suffix = self._get_complexity_suffix(action)
            return f"general_{language_suffix}_{complexity_suffix}"

    def _create_new_cluster(self, action: str) -> str:
        """创建新聚类"""
        cluster_id = f"cluster_{len(self.action_clusters)}"
        self.action_clusters[cluster_id] = [action]
        return cluster_id

    def _add_to_cluster(self, cluster_id: str, action: str):
        """将动作添加到现有聚类"""
        if cluster_id in self.action_clusters:
            if action not in self.action_clusters[cluster_id]:
                self.action_clusters[cluster_id].append(action)
