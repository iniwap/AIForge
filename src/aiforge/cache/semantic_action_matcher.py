from typing import Dict, List


class SemanticActionMatcher:
    """基于语义向量的动作匹配器"""

    def __init__(self, cache_instance):
        self.cache = cache_instance
        self.action_clusters = {}
        self.action_vectors = {}
        self.cluster_threshold = 0.75  # 聚类阈值

    def get_action_cluster(self, action: str) -> str:
        """获取动作所属的语义聚类"""
        if not self.cache.semantic_enabled:
            return self._fallback_action_matching(action)

        # 生成动作向量
        action_vector = self._get_action_vector(action)

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
            best_cluster = self._create_new_cluster(action)
        else:
            # 将动作添加到现有聚类
            self._add_to_cluster(best_cluster, action)

        return best_cluster

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
        """轻量级模式：提取动作特征向量"""
        features = {}

        # 1. 动词特征
        action_verbs = {
            "获取": ["获取", "get", "fetch", "retrieve"],
            "查询": ["查询", "query", "search", "find"],
            "分析": ["分析", "analyze", "process"],
            "生成": ["生成", "generate", "create"],
        }

        for verb_type, verbs in action_verbs.items():
            features[f"verb_{verb_type}"] = 1.0 if any(v in action for v in verbs) else 0.0

        # 2. 领域特征（动态提取）
        domain_indicators = self._extract_domain_indicators(action)
        for domain, score in domain_indicators.items():
            features[f"domain_{domain}"] = score

        # 3. 时效性特征
        temporal_words = ["实时", "今天", "当前", "最新", "real-time", "current"]
        features["temporal"] = 1.0 if any(w in action for w in temporal_words) else 0.0

        return features

    def _extract_domain_indicators(self, action: str) -> Dict[str, float]:
        """动态提取领域指示词"""
        # 使用 TF-IDF 或其他统计方法动态识别领域特征
        # 这里简化为基础实现
        domains = {}

        # 基于上下文词汇推断领域
        if any(w in action for w in ["天气", "温度", "气温", "weather"]):
            domains["weather"] = 1.0
        elif any(w in action for w in ["新闻", "消息", "资讯", "news"]):
            domains["news"] = 1.0
        elif any(w in action for w in ["股票", "金融", "finance"]):
            domains["finance"] = 1.0
        else:
            # 使用更复杂的语义分析
            domains["general"] = 0.5

        return domains

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
        """语义模型不可用时的回退匹配"""
        # 简单的基于关键词的分组
        if any(w in action for w in ["天气", "weather"]):
            return "weather_cluster"
        elif any(w in action for w in ["新闻", "news"]):
            return "news_cluster"
        else:
            return "general_cluster"

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
