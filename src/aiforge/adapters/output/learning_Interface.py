from typing import Dict, Any


class LearningInterface:
    """学习优化接口"""

    def __init__(self):
        self.adaptation_history = []
        self.rule_usage_stats = {}
        self.ai_usage_stats = {}
        self.user_feedback = []
        self.performance_metrics = {}

    def record_adaptation_request(self, data: Dict[str, Any], task_type: str, ui_type: str):
        """记录适配请求"""
        import time

        self.adaptation_history.append(
            {
                "timestamp": time.time(),
                "task_type": task_type,
                "ui_type": ui_type,
                "data_structure": self._analyze_data_structure(data),
                "data_size": len(str(data)),
            }
        )

    def record_rule_adaptation(self, task_type: str, ui_type: str, result: Dict[str, Any]):
        """记录规则适配结果"""
        import time

        key = f"{task_type}_{ui_type}"

        if key not in self.rule_usage_stats:
            self.rule_usage_stats[key] = {
                "count": 0,
                "success_rate": 1.0,
                "avg_response_time": 0.0,
                "last_used": time.time(),
            }

        self.rule_usage_stats[key]["count"] += 1
        self.rule_usage_stats[key]["last_used"] = time.time()

        # 记录性能指标
        self._record_performance("rule_based", key, 0.001)  # 规则适配通常很快

    def record_ai_adaptation(
        self, task_type: str, ui_type: str, data: Dict[str, Any], result: Dict[str, Any]
    ):
        """记录AI适配结果"""
        import time

        key = f"{task_type}_{ui_type}"

        if key not in self.ai_usage_stats:
            self.ai_usage_stats[key] = {
                "count": 0,
                "patterns": [],
                "avg_response_time": 0.0,
                "success_rate": 0.8,  # AI适配的默认成功率
            }

        self.ai_usage_stats[key]["count"] += 1
        self.ai_usage_stats[key]["patterns"].append(
            {
                "data_pattern": self._analyze_data_structure(data),
                "result_pattern": self._analyze_result_structure(result),
                "timestamp": time.time(),
            }
        )

        # 记录性能指标（AI适配通常较慢）
        self._record_performance("ai_based", key, 2.5)

    def record_user_feedback(self, adaptation_id: str, feedback: Dict[str, Any]):
        """记录用户反馈"""
        import time

        self.user_feedback.append(
            {
                "adaptation_id": adaptation_id,
                "feedback": feedback,
                "timestamp": time.time(),
                "rating": feedback.get("rating", 3),  # 1-5分评分
                "comments": feedback.get("comments", ""),
            }
        )

    def _record_performance(self, method: str, key: str, response_time: float):
        """记录性能指标"""
        if method not in self.performance_metrics:
            self.performance_metrics[method] = {}

        if key not in self.performance_metrics[method]:
            self.performance_metrics[method][key] = {"total_time": 0.0, "count": 0, "avg_time": 0.0}

        metrics = self.performance_metrics[method][key]
        metrics["total_time"] += response_time
        metrics["count"] += 1
        metrics["avg_time"] = metrics["total_time"] / metrics["count"]

    def get_stats(self) -> Dict[str, Any]:
        """获取完整统计信息"""
        return {
            "total_adaptations": len(self.adaptation_history),
            "rule_usage": self.rule_usage_stats,
            "ai_usage": self.ai_usage_stats,
            "feedback_count": len(self.user_feedback),
            "performance_metrics": self.performance_metrics,
            "avg_user_rating": self._calculate_avg_rating(),
            "adaptation_trends": self._analyze_trends(),
        }

    def _calculate_avg_rating(self) -> float:
        """计算平均用户评分"""
        if not self.user_feedback:
            return 0.0

        total_rating = sum(feedback["rating"] for feedback in self.user_feedback)
        return total_rating / len(self.user_feedback)

    def _analyze_trends(self) -> Dict[str, Any]:
        """分析适配趋势"""
        if len(self.adaptation_history) < 2:
            return {}

        recent_adaptations = self.adaptation_history[-10:]  # 最近10次

        task_type_counts = {}
        ui_type_counts = {}

        for adaptation in recent_adaptations:
            task_type = adaptation["task_type"]
            ui_type = adaptation["ui_type"]

            task_type_counts[task_type] = task_type_counts.get(task_type, 0) + 1
            ui_type_counts[ui_type] = ui_type_counts.get(ui_type, 0) + 1

        return {
            "popular_task_types": sorted(
                task_type_counts.items(), key=lambda x: x[1], reverse=True
            ),
            "popular_ui_types": sorted(ui_type_counts.items(), key=lambda x: x[1], reverse=True),
            "rule_vs_ai_ratio": self._calculate_method_ratio(),
        }

    def _calculate_method_ratio(self) -> Dict[str, float]:
        """计算规则适配vs AI适配的比例"""
        total_rule = sum(stats["count"] for stats in self.rule_usage_stats.values())
        total_ai = sum(stats["count"] for stats in self.ai_usage_stats.values())
        total = total_rule + total_ai

        if total == 0:
            return {"rule_based": 0.0, "ai_based": 0.0}

        return {"rule_based": total_rule / total, "ai_based": total_ai / total}

    def _analyze_data_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """分析数据结构模式"""
        return {
            "keys": list(data.keys()) if isinstance(data, dict) else [],
            "types": (
                {k: type(v).__name__ for k, v in data.items()} if isinstance(data, dict) else {}
            ),
            "depth": self._calculate_depth(data),
            "has_lists": (
                any(isinstance(v, list) for v in data.values()) if isinstance(data, dict) else False
            ),
            "has_nested_dicts": (
                any(isinstance(v, dict) for v in data.values()) if isinstance(data, dict) else False
            ),
        }

    def _analyze_result_structure(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """分析结果结构模式"""
        return {
            "display_items_count": len(result.get("display_items", [])),
            "layout_type": result.get("layout_hints", {}).get("layout_type", ""),
            "actions_count": len(result.get("actions", [])),
            "has_summary": bool(result.get("summary_text")),
        }

    def _calculate_depth(self, obj, depth=0):
        """计算数据结构深度"""
        if isinstance(obj, dict):
            return max([self._calculate_depth(v, depth + 1) for v in obj.values()], default=depth)
        elif isinstance(obj, list) and obj:
            return max([self._calculate_depth(item, depth + 1) for item in obj], default=depth)
        return depth
