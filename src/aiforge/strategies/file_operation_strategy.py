from typing import Any, Dict, Optional
from .execution_strategy import ExecutionStrategy
from .file_operation_safety import (
    FileOperationSafetyAnalyzer,
    FileOperationConfirmationManager,
    FileOperationBackupManager,
    FileOperationUndoManager,
)


class FileOperationStrategy(ExecutionStrategy):
    """文件操作执行策略"""

    def __init__(self, parameter_mapping_service=None):
        super().__init__(parameter_mapping_service)
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
        self.safety_analyzer = FileOperationSafetyAnalyzer()
        self.confirmation_manager = FileOperationConfirmationManager()
        self.backup_manager = FileOperationBackupManager()
        self.undo_manager = FileOperationUndoManager()

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

        print("[DEBUG] 任务已重新分类为 data_process，原任务类型: file_operation")

    def get_priority(self) -> int:
        return 95  # 高优先级，仅次于搜索策略

    def execute(self, module: Any, **kwargs) -> Optional[Any]:
        standardized_instruction = kwargs.get("standardized_instruction", {})

        # 1. 安全分析
        code = self._extract_code_from_module(module)
        risk_analysis = self.safety_analyzer.analyze_operation_risk(
            code, standardized_instruction.get("parameters", {})
        )

        # 2. 用户确认
        if not self.confirmation_manager.require_user_confirmation(risk_analysis):
            return {"status": "cancelled", "reason": "User cancelled operation"}

        # 3. 创建备份
        backup_id = None
        if risk_analysis["backup_required"]:
            backup_id = self.backup_manager.create_operation_backup(risk_analysis["affected_files"])

        # 4. 执行操作
        try:
            result = super().execute(module, **kwargs)

            # 5. 注册撤销操作
            if backup_id:
                undo_id = self.undo_manager.register_operation(
                    standardized_instruction.get("action", ""), backup_id, standardized_instruction
                )
                result["undo_id"] = undo_id

            return result

        except Exception as e:
            # 6. 操作失败时自动恢复
            if backup_id:
                self.backup_manager.restore_from_backup(backup_id)
            raise e

    def _extract_code_from_module(self, module: Any) -> str:
        """从模块中提取代码"""
        if module is None:
            return ""

        try:
            import inspect

            return inspect.getsource(module)
        except Exception:
            return str(module)

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
        """批量文件操作"""
        operation = parameters.get("operation")
        file_list = parameters.get("file_list", [])
        pattern = parameters.get("pattern")

        if not operation:
            return {"status": "error", "reason": "Missing operation type"}

        if not file_list and not pattern:
            return {"status": "error", "reason": "Missing file list or pattern"}

        try:
            import glob

            # 如果提供了模式，使用glob匹配文件
            if pattern:
                file_list = glob.glob(pattern)

            results = []
            success_count = 0

            for file_path in file_list:
                # 为每个文件创建参数副本
                file_params = parameters.copy()
                file_params["file_path"] = file_path

                # 执行对应操作
                if operation in self.supported_operations:
                    result = self.supported_operations[operation](file_params)
                    results.append({"file": file_path, "result": result})
                    if result.get("status") == "success":
                        success_count += 1
                else:
                    results.append(
                        {
                            "file": file_path,
                            "result": {
                                "status": "error",
                                "reason": f"Unsupported operation: {operation}",
                            },
                        }
                    )

            return {
                "status": "success",
                "operation": "batch_operation",
                "total_files": len(file_list),
                "success_count": success_count,
                "failed_count": len(file_list) - success_count,
                "results": results,
            }
        except Exception as e:
            return {"status": "error", "reason": str(e)}
