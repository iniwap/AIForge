from typing import Dict, Any, Optional, List
import time


class AIForgeResult:
    """统一的 AIForge 执行结果格式"""

    # 定义必需字段
    REQUIRED_FIELDS = ["data", "status", "summary", "metadata", "task_type"]

    def __init__(
        self,
        data: Any = None,
        status: str = "success",
        summary: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        task_type: Optional[str] = None,
    ):
        self.data = data
        self.status = status
        self.summary = summary
        self.metadata = metadata or {}
        self.task_type = task_type

        # 确保 metadata 包含基础字段
        if "timestamp" not in self.metadata:
            self.metadata["timestamp"] = time.time()
        if task_type and "task_type" not in self.metadata:
            self.metadata["task_type"] = task_type

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "data": self.data,
            "status": self.status,
            "summary": self.summary,
            "metadata": self.metadata,
            "task_type": self.task_type,
        }

    @classmethod
    def is_valid_format(cls, data: Dict[str, Any]) -> bool:
        """检查数据是否符合 AIForgeResult 格式"""
        if not isinstance(data, dict):
            return False
        return all(key in data for key in cls.REQUIRED_FIELDS)

    @classmethod
    def get_required_fields(cls) -> List[str]:
        """获取必需字段列表"""
        return cls.REQUIRED_FIELDS.copy()


def convert_to_aiforge_result(
    internal_result: Any, context_data: Optional[Dict[str, Any]] = None
) -> AIForgeResult:
    """将 AIForge 内部各种格式统一为 AIForgeResult 标准格式

    Args:
        internal_result: 来自各个管理器的内部结果
        context_data: 上下文数据，用于获取任务类型等信息

    Returns:
        统一的 AIForgeResult 字典格式
    """
    if not isinstance(internal_result, dict):
        # 非字典类型，包装为标准格式
        return AIForgeResult(
            data=internal_result,
            summary="执行结果",
            task_type=context_data.get("task_type") if context_data else None,
        )

    # 提取任务类型
    task_type = None
    if context_data:
        task_type = context_data.get("task_type")
    if not task_type and "metadata" in internal_result:
        task_type = internal_result["metadata"].get("task_type")

    # 1. 处理内容生成管理器格式
    # 格式：{"data": {"content": "...", "format": "...", "content_type": "..."}, "status": "success", "summary": "...", "metadata": {...}} # noqa 501
    if (
        "data" in internal_result
        and isinstance(internal_result["data"], dict)
        and "content" in internal_result["data"]
    ):

        content_data = internal_result["data"]
        return AIForgeResult(
            data=content_data["content"],  # 提取实际内容
            status=internal_result.get("status", "success"),
            summary=internal_result.get("summary", "内容生成完成"),
            metadata={
                **internal_result.get("metadata", {}),
                "output_format": content_data.get("format", "markdown"),
                "content_type": content_data.get("content_type", "text/plain"),
            },
            task_type=task_type or "content_generation",
        )

    # 2. 处理搜索管理器格式
    # 格式：{"data": [results], "status": "success", "summary": "...", "metadata": {...}}
    elif (
        "data" in internal_result
        and isinstance(internal_result["data"], list)
        and internal_result.get("metadata", {}).get("task_type") == "data_fetch"
    ):

        return AIForgeResult(
            data=internal_result["data"],
            status=internal_result.get("status", "success"),
            summary=internal_result.get(
                "summary", f"搜索完成，共 {len(internal_result['data'])} 条结果"
            ),
            metadata=internal_result.get("metadata", {}),
            task_type=task_type or "data_fetch",
        )

    # 3. 处理执行管理器的直接响应格式
    # 格式：{"data": "ai_response", "status": "success", "summary": "...", "metadata": {...}}
    elif (
        "metadata" in internal_result
        and internal_result["metadata"].get("execution_type") == "direct_ai_response"
    ):

        return AIForgeResult(
            data=internal_result.get("data", ""),
            status=internal_result.get("status", "success"),
            summary=internal_result.get("summary", "直接响应完成"),
            metadata=internal_result.get("metadata", {}),
            task_type=task_type or "direct_response",
        )

    # 4. 处理代码执行结果格式
    # 格式：{"success": True, "result": {...}, "code": "..."}
    elif "success" in internal_result and "result" in internal_result and "code" in internal_result:

        execution_data = internal_result["result"]
        return AIForgeResult(
            data=execution_data,
            status="success" if internal_result["success"] else "error",
            summary="代码执行完成" if internal_result["success"] else "代码执行失败",
            metadata={
                "execution_type": "code_execution",
                "code_length": len(internal_result.get("code", "")),
                "timestamp": time.time(),
            },
            task_type=task_type or "code_execution",
        )

    # 5. 处理已经是标准 AIForgeResult 格式的数据
    elif all(key in internal_result for key in ["data", "status", "summary", "metadata"]):
        # 已经是标准格式，转换为 AIForgeResult 对象
        return AIForgeResult(
            data=internal_result.get("data"),
            status=internal_result.get("status", "success"),
            summary=internal_result.get("summary", ""),
            metadata=internal_result.get("metadata", {}),
            task_type=internal_result.get("task_type") or task_type,
        )

    # 6. 处理通用数据格式
    elif "data" in internal_result:
        return AIForgeResult(
            data=internal_result["data"],
            status=internal_result.get("status", "success"),
            summary=internal_result.get("summary", "执行完成"),
            metadata=internal_result.get("metadata", {}),
            task_type=task_type,
        )

    # 7. 处理文件操作结果格式
    elif "processed_files" in internal_result:
        return AIForgeResult(
            data=internal_result["processed_files"],
            status=internal_result.get("status", "success"),
            summary=internal_result.get(
                "summary", f"文件处理完成，共 {len(internal_result['processed_files'])} 个文件"
            ),
            metadata=internal_result.get("metadata", {}),
            task_type=task_type or "file_operation",
        )

    # 8. 处理错误结果格式
    elif "error" in internal_result:
        return AIForgeResult(
            data=None,
            status="error",
            summary=f"执行失败: {internal_result['error']}",
            metadata={
                "error_type": "execution_error",
                "timestamp": time.time(),
                **internal_result.get("metadata", {}),
            },
            task_type=task_type,
        )

    # 9. 回退处理：将整个结果作为数据
    else:
        return AIForgeResult(
            data=internal_result,
            status="success",
            summary="执行完成",
            metadata={"timestamp": time.time()},
            task_type=task_type,
        )
