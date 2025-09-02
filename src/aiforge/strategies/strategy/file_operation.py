from pathlib import Path
import time
import os
import shutil
from typing import Any, Dict, Optional
from ..execution_strategy import ExecutionStrategy
from .file_operation_safety import (
    FileOperationConfirmationManager,
    FileOperationBackupManager,
    FileOperationUndoManager,
)


class FileOperationErrorClassifier:
    """文件操作错误分类器"""

    def __init__(self):
        self.error_patterns = {
            "permission_error": [
                "Permission denied",
                "Access is denied",
                "Operation not permitted",
                "权限被拒绝",
                "访问被拒绝",
            ],
            "disk_space_error": [
                "No space left on device",
                "Disk full",
                "磁盘空间不足",
                "设备上没有空间",
            ],
            "file_not_found": [
                "No such file or directory",
                "File not found",
                "找不到文件",
                "文件不存在",
            ],
            "network_error": [
                "Network is unreachable",
                "Connection refused",
                "Timeout",
                "网络不可达",
                "连接被拒绝",
            ],
            "encoding_error": ["UnicodeDecodeError", "UnicodeEncodeError", "编码错误", "字符编码"],
        }

    def classify_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """分类错误并提供建议"""
        error_message = str(error).lower()
        error_type = type(error).__name__

        # 基于错误消息匹配
        for category, patterns in self.error_patterns.items():
            if any(pattern.lower() in error_message for pattern in patterns):
                return self._generate_error_info(category, error, context)

        # 基于异常类型匹配
        type_mapping = {
            "PermissionError": "permission_error",
            "FileNotFoundError": "file_not_found",
            "OSError": "disk_space_error",
            "UnicodeError": "encoding_error",
            "ConnectionError": "network_error",
        }

        category = type_mapping.get(error_type, "unknown_error")
        return self._generate_error_info(category, error, context)

    def _generate_error_info(
        self, category: str, error: Exception, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成错误信息和建议"""
        suggestions = {
            "permission_error": [
                "检查文件权限设置",
                "尝试以管理员身份运行",
                "确认对目标目录有写权限",
            ],
            "disk_space_error": ["清理磁盘空间", "检查临时文件占用", "选择其他存储位置"],
            "file_not_found": ["检查文件路径是否正确", "确认文件是否存在", "使用绝对路径"],
            "network_error": ["检查网络连接", "重试操作", "检查防火墙设置"],
            "encoding_error": ["指定正确的文件编码", "使用UTF-8编码", "检查文件内容格式"],
        }

        return {
            "type": category,
            "original_error": str(error),
            "suggestions": suggestions.get(category, ["联系技术支持"]),
            "context": context,
            "file_path": self._extract_file_path(context),
        }

    def _extract_file_path(self, context: Dict[str, Any]) -> Optional[str]:
        """从上下文中提取文件路径"""
        params = context.get("parameters", {})
        return params.get("file_path") or params.get("source_path") or params.get("target_path")


class FileOperationTransactionManager:
    """文件操作事务管理器"""

    def __init__(self):
        self.active_transactions = {}
        self.transaction_log = []

    def begin_transaction(self, transaction_id: str, risk_analysis: Dict[str, Any]):
        """开始事务"""
        self.active_transactions[transaction_id] = {
            "status": "active",
            "start_time": time.time(),
            "operations": [],
            "backup": [],
            "risk_analysis": risk_analysis,
            "rollback_plan": [],
        }

    def register_operation(self, transaction_id: str, operation: Dict[str, Any]):
        """注册操作到事务"""
        if transaction_id in self.active_transactions:
            self.active_transactions[transaction_id]["operations"].append(operation)

    def register_backup(self, transaction_id: str, backup_id: str):
        """注册备份到事务"""
        if transaction_id in self.active_transactions:
            self.active_transactions[transaction_id]["backup"].append(backup_id)

    def commit_transaction(self, transaction_id: str) -> bool:
        """提交事务"""
        if transaction_id not in self.active_transactions:
            return False

        transaction = self.active_transactions[transaction_id]

        try:
            # 标记事务为已提交
            transaction["status"] = "committed"
            transaction["end_time"] = time.time()

            # 记录到事务日志
            self.transaction_log.append(
                {
                    "transaction_id": transaction_id,
                    "status": "committed",
                    "timestamp": time.time(),
                    "operations_count": len(transaction["operations"]),
                    "duration": transaction["end_time"] - transaction["start_time"],
                }
            )

            # 清理活跃事务
            del self.active_transactions[transaction_id]

            return True

        except Exception:
            return False

    def rollback_transaction(self, transaction_id: str) -> bool:
        """回滚事务"""
        if transaction_id not in self.active_transactions:
            return False

        transaction = self.active_transactions[transaction_id]

        try:
            # 执行回滚计划
            for rollback_action in reversed(transaction["rollback_plan"]):
                self._execute_rollback_action(rollback_action)

            # 恢复备份
            for backup_id in transaction["backup"]:
                self.backup_manager.restore_from_backup(backup_id)

            # 标记事务为已回滚
            transaction["status"] = "rolled_back"
            transaction["end_time"] = time.time()

            # 记录到事务日志
            self.transaction_log.append(
                {
                    "transaction_id": transaction_id,
                    "status": "rolled_back",
                    "timestamp": time.time(),
                    "operations_count": len(transaction["operations"]),
                    "duration": transaction["end_time"] - transaction["start_time"],
                }
            )

            # 清理活跃事务
            del self.active_transactions[transaction_id]

            return True

        except Exception:
            return False

    def _execute_rollback_action(self, action: Dict[str, Any]):
        """执行回滚动作"""
        action_type = action.get("type")

        if action_type == "delete_created_file":
            file_path = action.get("file_path")
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        elif action_type == "restore_moved_file":
            source = action.get("source")
            target = action.get("target")
            if source and target and os.path.exists(target):
                shutil.move(target, source)
        elif action_type == "remove_created_directory":
            dir_path = action.get("dir_path")
            if dir_path and os.path.exists(dir_path):
                shutil.rmtree(dir_path)


class FileOperationStrategy(ExecutionStrategy):
    """文件操作执行策略"""

    def __init__(self, components: Dict[str, Any] = None):
        super().__init__(components)

        self.supported_operations = {
            "copy": self._copy_file,
            "move": self._move_file,
            "delete": self._delete_file,
            "rename": self._rename_file,
            "create_dir": self._create_directory,
            "compress": self._compress_file,
            "extract": self._extract_file,
            "read": self._read_file,
            "write": self._write_file,
            "batch": self._batch_operation,
        }

        self.confirmation_manager = FileOperationConfirmationManager()
        self.backup_manager = FileOperationBackupManager()
        self.undo_manager = FileOperationUndoManager()

        # 错误分类器
        self.error_classifier = FileOperationErrorClassifier()
        # 事务管理器
        self.transaction_manager = FileOperationTransactionManager

    def can_handle(self, module: Any, standardized_instruction: Dict[str, Any]) -> bool:
        task_type = standardized_instruction.get("task_type", "")

        # 首先检查是否是文件操作任务
        if task_type != "file_operation":
            return False

        # 验证任务边界，确保不与数据处理重叠
        if not self._validate_task_boundary(standardized_instruction):
            # 如果检测到应该是数据处理任务，触发重新分类
            self._trigger_task_reclassification(standardized_instruction)
            return False

        return True

    def _validate_task_boundary(self, standardized_instruction: Dict[str, Any]) -> bool:
        """验证任务边界，避免与数据处理重叠"""
        target = standardized_instruction.get("target", "").lower()

        # 如果涉及数据分析关键词，应该重新分类为 data_process
        data_analysis_keywords = [
            "分析",
            "analyze",
            "统计",
            "statistics",
            "计算",
            "calculate",
            "清洗",
            "clean",
            "处理数据",
            "process data",
        ]

        if any(keyword in target for keyword in data_analysis_keywords):
            # 触发重新分类
            return False

        return True

    def _trigger_task_reclassification(self, standardized_instruction: Dict[str, Any]):
        """触发任务重新分类"""
        # 修改任务类型为数据处理
        standardized_instruction["task_type"] = "data_process"
        standardized_instruction["reclassified"] = True
        standardized_instruction["original_task_type"] = "file_operation"

    def get_priority(self) -> int:
        return 95  # 高优先级，仅次于搜索策略

    def execute(self, module: Any, **kwargs) -> Optional[Any]:
        standardized_instruction = kwargs.get("standardized_instruction", {})
        operation_id = f"op_{int(time.time())}"

        try:
            # 1. 安全分析（包含路径验证）
            security_result = self.perform_security_validation(module, **kwargs)
            if security_result:
                return security_result

            # 2. 获取风险分析（验证已通过，但仍需风险信息）
            risk_analysis = self._last_validation_result["file"]["risk_analysis"]

            # 3. 用户确认
            if not self.confirmation_manager.require_user_confirmation(risk_analysis):
                return {"status": "cancelled", "reason": "User cancelled operation"}

            # 4. 开始事务
            self.transaction_manager.begin_transaction(operation_id, risk_analysis)

            # 5. 创建备份
            backup_id = None
            if risk_analysis["backup_required"]:
                backup_id = self.backup_manager.create_operation_backup(
                    risk_analysis["affected_files"]
                )
                self.transaction_manager.register_backup(operation_id, backup_id)

            # 6. 执行操作
            result = super().execute(module, **kwargs)

            # 7. 提交事务
            self.transaction_manager.commit_transaction(operation_id)

            # 8. 注册撤销操作
            if backup_id:
                undo_id = self.undo_manager.register_operation(
                    standardized_instruction.get("action", ""), backup_id, standardized_instruction
                )
                result["undo_id"] = undo_id
                result["transaction_id"] = operation_id

            return result

        except Exception as e:
            # 增强的错误处理
            error_info = self.error_classifier.classify_error(e, standardized_instruction)

            # 回滚事务
            rollback_success = self.transaction_manager.rollback_transaction(operation_id)

            # 根据错误类型采取不同的恢复策略
            recovery_result = self._handle_classified_error(error_info, rollback_success)

            return {
                "status": "error",
                "error_type": error_info["type"],
                "error_message": str(e),
                "recovery_attempted": recovery_result["attempted"],
                "recovery_success": recovery_result["success"],
                "suggestions": error_info["suggestions"],
            }

    def _handle_classified_error(
        self, error_info: Dict[str, Any], rollback_success: bool
    ) -> Dict[str, Any]:
        """根据错误分类处理错误"""
        error_type = error_info["type"]
        recovery_result = {"attempted": False, "success": False}

        if error_type == "permission_error":
            # 尝试权限修复
            recovery_result["attempted"] = True
            recovery_result["success"] = self._attempt_permission_fix(error_info)
        elif error_type == "disk_space_error":
            # 尝试清理临时文件
            recovery_result["attempted"] = True
            recovery_result["success"] = self._attempt_space_cleanup(error_info)
        elif error_type == "file_not_found":
            # 尝试路径修正
            recovery_result["attempted"] = True
            recovery_result["success"] = self._attempt_path_correction(error_info)
        elif error_type == "network_error":
            # 尝试重试机制
            recovery_result["attempted"] = True
            recovery_result["success"] = self._attempt_retry(error_info)

        return recovery_result

    def _attempt_permission_fix(self, error_info: Dict[str, Any]) -> bool:
        """尝试修复权限问题"""
        try:
            import os
            import stat

            file_path = error_info.get("file_path")
            if file_path and os.path.exists(file_path):
                # 尝试添加写权限
                current_mode = os.stat(file_path).st_mode
                os.chmod(file_path, current_mode | stat.S_IWUSR)
                return True
        except Exception:
            pass
        return False

    def _attempt_space_cleanup(self, error_info: Dict[str, Any]) -> bool:
        """尝试清理磁盘空间"""
        try:
            import tempfile
            import shutil

            # 清理临时目录
            temp_dir = tempfile.gettempdir()
            for item in os.listdir(temp_dir):
                if item.startswith("aiforge_temp_"):
                    item_path = os.path.join(temp_dir, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
            return True
        except Exception:
            pass
        return False

    def _attempt_path_correction(self, error_info: Dict[str, Any]) -> bool:
        """尝试路径修正"""
        try:
            import os

            file_path = error_info.get("file_path")
            if file_path:
                # 尝试相对路径转绝对路径
                abs_path = os.path.abspath(file_path)
                if os.path.exists(abs_path):
                    error_info["corrected_path"] = abs_path
                    return True

                # 尝试在当前目录查找同名文件
                filename = Path(file_path).name
                for root, dirs, files in os.walk("."):
                    if filename in files:
                        error_info["corrected_path"] = os.path.join(root, filename)
                        return True
        except Exception:
            pass
        return False

    def _attempt_retry(self, error_info: Dict[str, Any]) -> bool:
        """尝试重试机制"""
        import time

        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                time.sleep(retry_delay * (attempt + 1))
                # 这里应该重新执行原始操作
                # 简化示例，实际需要重新调用具体操作
                return True
            except Exception:
                continue
        return False

    def _find_target_function(
        self, module: Any, standardized_instruction: Dict[str, Any]
    ) -> Optional[callable]:
        """查找目标函数"""
        if hasattr(module, "execute_task"):
            return getattr(module, "execute_task")

        # 基于任务类型查找函数
        task_type = standardized_instruction.get("task_type", "")
        if task_type == "file_operation":
            function_candidates = ["process_file", "handle_file", "transform_file"]
            for func_name in function_candidates:
                if hasattr(module, func_name):
                    return getattr(module, func_name)

        return None

    def _copy_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """复制文件"""
        import shutil

        source = parameters.get("source_path") or parameters.get("file_path")
        target = parameters.get("target_path") or parameters.get("output_path")

        if not source or not target:
            return {"status": "error", "reason": "Missing source or target path"}

        try:
            shutil.copy2(source, target)
            return {"status": "success", "operation": "copy", "source": source, "target": target}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def _move_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """移动文件"""
        import shutil

        source = parameters.get("source_path") or parameters.get("file_path")
        target = parameters.get("target_path") or parameters.get("output_path")

        if not source or not target:
            return {"status": "error", "reason": "Missing source or target path"}

        try:
            shutil.move(source, target)
            return {"status": "success", "operation": "move", "source": source, "target": target}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def _delete_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """删除文件"""
        import os

        file_path = parameters.get("file_path") or parameters.get("source_path")

        if not file_path:
            return {"status": "error", "reason": "Missing file path"}

        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            elif os.path.isdir(file_path):
                import shutil

                shutil.rmtree(file_path)
            return {"status": "success", "operation": "delete", "path": file_path}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def _rename_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """重命名文件"""
        import os

        source = parameters.get("source_path") or parameters.get("file_path")
        target = parameters.get("target_path") or parameters.get("new_name")

        if not source or not target:
            return {"status": "error", "reason": "Missing source path or new name"}

        try:
            # 如果target不是完整路径，则在同目录下重命名
            if not os.path.dirname(target):
                source_dir = os.path.dirname(source)
                target = os.path.join(source_dir, target)

            os.rename(source, target)
            return {"status": "success", "operation": "rename", "source": source, "target": target}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def _create_directory(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """创建目录"""
        import os

        dir_path = (
            parameters.get("dir_path") or parameters.get("path") or parameters.get("directory")
        )
        recursive = parameters.get("recursive", True)

        if not dir_path:
            return {"status": "error", "reason": "Missing directory path"}

        try:
            if recursive:
                os.makedirs(dir_path, exist_ok=True)
            else:
                os.mkdir(dir_path)
            return {"status": "success", "operation": "create_directory", "path": dir_path}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def _compress_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """压缩文件或目录"""
        import zipfile
        import tarfile
        import os

        source = parameters.get("source_path") or parameters.get("file_path")
        target = parameters.get("target_path") or parameters.get("output_path")
        format_type = parameters.get("format", "zip").lower()

        if not source or not target:
            return {"status": "error", "reason": "Missing source or target path"}

        try:
            if format_type == "zip":
                with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zipf:
                    if os.path.isfile(source):
                        zipf.write(source, os.path.basename(source))
                    elif os.path.isdir(source):
                        for root, dirs, files in os.walk(source):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, source)
                                zipf.write(file_path, arcname)

            elif format_type in ["tar", "tar.gz", "tgz"]:
                mode = "w:gz" if format_type in ["tar.gz", "tgz"] else "w"
                with tarfile.open(target, mode) as tarf:
                    tarf.add(source, arcname=os.path.basename(source))

            else:
                return {
                    "status": "error",
                    "reason": f"Unsupported compression format: {format_type}",
                }

            return {
                "status": "success",
                "operation": "compress",
                "source": source,
                "target": target,
                "format": format_type,
            }
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def _extract_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """解压文件"""
        import zipfile
        import tarfile
        import os

        source = parameters.get("source_path") or parameters.get("file_path")
        target = parameters.get("target_path") or parameters.get("extract_to")

        if not source:
            return {"status": "error", "reason": "Missing source archive path"}

        # 如果没有指定目标目录，使用源文件同目录
        if not target:
            target = os.path.dirname(source)

        try:
            # 自动检测文件类型
            if source.lower().endswith(".zip"):
                with zipfile.ZipFile(source, "r") as zipf:
                    zipf.extractall(target)
                    extracted_files = zipf.namelist()

            elif source.lower().endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2")):
                with tarfile.open(source, "r:*") as tarf:
                    tarf.extractall(target)
                    extracted_files = tarf.getnames()

            else:
                return {"status": "error", "reason": "Unsupported archive format"}

            return {
                "status": "success",
                "operation": "extract",
                "source": source,
                "target": target,
                "extracted_files": extracted_files[:10],  # 只显示前10个文件
            }
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def _read_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """读取文件内容"""
        file_path = parameters.get("file_path") or parameters.get("path")
        encoding = parameters.get("encoding", "utf-8")
        max_size = parameters.get("max_size", 10 * 1024 * 1024)  # 10MB限制

        if not file_path:
            return {"status": "error", "reason": "Missing file path"}

        try:
            import os

            if not os.path.exists(file_path):
                return {"status": "error", "reason": "File does not exist"}

            file_size = os.path.getsize(file_path)
            if file_size > max_size:
                return {
                    "status": "error",
                    "reason": f"File too large: {file_size} bytes (max: {max_size})",
                }

            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()

            return {
                "status": "success",
                "operation": "read",
                "path": file_path,
                "content": content,
                "size": file_size,
                "encoding": encoding,
            }
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def _write_file(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """写入文件内容"""
        file_path = parameters.get("file_path") or parameters.get("path")
        content = parameters.get("content", "")
        encoding = parameters.get("encoding", "utf-8")
        mode = parameters.get("mode", "w")  # w: 覆盖, a: 追加

        if not file_path:
            return {"status": "error", "reason": "Missing file path"}

        try:
            # 确保目录存在
            import os

            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, mode, encoding=encoding) as f:
                f.write(content)

            file_size = os.path.getsize(file_path)

            return {
                "status": "success",
                "operation": "write",
                "path": file_path,
                "size": file_size,
                "mode": mode,
                "encoding": encoding,
            }
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def _batch_operation(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """增强的批量文件操作（支持事务）"""
        operation = parameters.get("operation")
        file_list = parameters.get("file_list", [])
        pattern = parameters.get("pattern")
        transaction_id = f"batch_{int(time.time())}"

        if not operation:
            return {"status": "error", "reason": "Missing operation type"}

        if not file_list and not pattern:
            return {"status": "error", "reason": "Missing file list or pattern"}

        try:
            import glob

            # 开始批量事务
            self.transaction_manager.begin_transaction(
                transaction_id,
                {"operation": operation, "file_count": len(file_list) if file_list else 0},
            )

            # 如果提供了模式，使用glob匹配文件
            if pattern:
                file_list = glob.glob(pattern)

            results = []
            success_count = 0
            failed_operations = []

            for i, file_path in enumerate(file_list):
                try:
                    # 为每个文件创建参数副本
                    file_params = parameters.copy()
                    file_params["file_path"] = file_path

                    # 执行对应操作
                    if operation in self.supported_operations:
                        result = self.supported_operations[operation](file_params)

                        # 注册操作到事务
                        self.transaction_manager.register_operation(
                            transaction_id,
                            {
                                "file_path": file_path,
                                "operation": operation,
                                "result": result,
                                "index": i,
                            },
                        )

                        results.append({"file": file_path, "result": result})
                        if result.get("status") == "success":
                            success_count += 1
                        else:
                            failed_operations.append({"file": file_path, "error": result})
                    else:
                        error_result = {
                            "status": "error",
                            "reason": f"Unsupported operation: {operation}",
                        }
                        results.append({"file": file_path, "result": error_result})
                        failed_operations.append({"file": file_path, "error": error_result})

                except Exception as e:
                    # 单个文件操作失败，记录但继续处理其他文件
                    error_result = {"status": "error", "reason": str(e)}
                    results.append({"file": file_path, "result": error_result})
                    failed_operations.append({"file": file_path, "error": error_result})

            # 检查是否需要回滚
            failure_rate = len(failed_operations) / len(file_list)
            if failure_rate > 0.5:  # 超过50%失败则回滚
                self.transaction_manager.rollback_transaction(transaction_id)
                return {
                    "status": "rolled_back",
                    "reason": f"批量操作失败率过高 ({failure_rate:.1%})",
                    "failed_operations": failed_operations,
                }
            else:
                # 提交事务
                self.transaction_manager.commit_transaction(transaction_id)

            return {
                "status": "success",
                "operation": "batch_operation",
                "transaction_id": transaction_id,
                "total_files": len(file_list),
                "success_count": success_count,
                "failed_count": len(file_list) - success_count,
                "failure_rate": failure_rate,
                "results": results,
            }

        except Exception as e:
            # 整体操作失败，回滚事务
            self.transaction_manager.rollback_transaction(transaction_id)
            return {"status": "error", "reason": str(e), "transaction_rolled_back": True}
