from typing import Dict, Any, List
import re
import os
from ..core.path_manager import AIForgePathManager


class FileSecurityController:
    """文件安全控制器"""

    def __init__(self, components: Dict[str, Any] = None):
        self.components = components
        self.config_manager = self.components.get("config_manager")

        self.file_config = self.config_manager.get_security_file_access_config()

        # 初始化工作目录和允许路径
        self.workdir = AIForgePathManager.get_workdir()
        self.user_allowed_paths = self.file_config.get("default_allowed_paths", [])

        # 初始化文件操作检测模式
        self._init_file_patterns()

    def _init_file_patterns(self):
        """初始化文件操作检测模式"""
        self.destructive_patterns = [
            r"\.delete\(\)",
            r"os\.remove\(",
            r"shutil\.rmtree\(",
            r"\.unlink\(\)",
            r"os\.rmdir\(",
            r"\.truncate\(",
        ]

        self.file_operation_patterns = [
            r"open\s*\(",
            r"with\s+open\s*\(",
            r"shutil\.",
            r"os\.remove",
            r"os\.rmdir",
            r"os\.unlink",
            r"pathlib\.Path",
            r"\.unlink\(\)",
            r"\.rmdir\(\)",
            r"\.write_text\(",
            r"\.write_bytes\(",
        ]

    def validate_file_access(self, code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """文件访问验证"""
        parameters = context.get("parameters", {})

        # 执行完整的文件操作风险分析
        risk_analysis = self.analyze_operation_risk(code, parameters)

        # 检查路径访问权限
        if risk_analysis["path_validation"]["invalid_paths"]:
            return {
                "allowed": False,
                "status": "error",
                "error_type": "access_denied",
                "message": "Access denied to specified paths",
                "invalid_paths": risk_analysis["path_validation"]["invalid_paths"],
                "access_denied": risk_analysis["path_validation"]["access_denied"],
            }

        return {"allowed": True, "risk_analysis": risk_analysis}

    def analyze_operation_risk(self, code: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """完整的文件操作风险分析"""
        risk_analysis = {
            "risk_level": "low",
            "destructive_operations": [],
            "affected_files": self._extract_affected_files(parameters),
            "backup_required": False,
            "confirmation_required": False,
            "path_validation": self._validate_operation_paths(parameters),
        }

        # 检查路径访问权限
        if risk_analysis["path_validation"]["invalid_paths"]:
            risk_analysis["risk_level"] = "high"
            risk_analysis["confirmation_required"] = True

        # 检查破坏性操作模式
        for pattern in self.destructive_patterns:
            if re.search(pattern, code):
                risk_analysis["risk_level"] = "high"
                risk_analysis["confirmation_required"] = True
                risk_analysis["backup_required"] = True
                risk_analysis["destructive_operations"].append(pattern)

        return risk_analysis

    def _extract_affected_files(self, parameters: Dict[str, Any]) -> List[str]:
        """提取受影响的文件列表"""
        affected_files = []
        file_path_keys = [
            "file_path",
            "source_path",
            "target_path",
            "path",
            "filename",
            "dir_path",
            "directory",
            "extract_to",
            "file_list",
        ]

        for key in file_path_keys:
            if key in parameters:
                param_info = parameters[key]

                # 处理字典格式的参数
                if isinstance(param_info, dict) and "value" in param_info:
                    file_path = param_info["value"]
                else:
                    file_path = param_info

                # 处理文件列表
                if key == "file_list" and isinstance(file_path, list):
                    for file_item in file_path:
                        file_str = str(file_item)
                        if file_str and file_str not in affected_files:
                            affected_files.append(file_str)
                else:
                    file_str = str(file_path) if file_path else ""
                    if file_str and file_str not in affected_files:
                        affected_files.append(file_str)

        return affected_files

    def _validate_file_access(self, file_path: str, additional_paths: List[str] = None) -> bool:
        """验证文件访问权限"""
        # 默认允许的目录
        allowed_dirs = [str(self.workdir), "/tmp", "/var/tmp"]

        # 添加用户指定的路径
        if self.user_allowed_paths:
            allowed_dirs.extend(self.user_allowed_paths)

        # 添加临时的额外路径
        if additional_paths:
            allowed_dirs.extend(additional_paths)

        abs_path = os.path.abspath(file_path)
        return any(
            abs_path.startswith(os.path.abspath(allowed_dir)) for allowed_dir in allowed_dirs
        )

    def _validate_operation_paths(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证操作中涉及的所有路径"""
        affected_files = self._extract_affected_files(parameters)
        validation_result = {"valid_paths": [], "invalid_paths": [], "access_denied": []}

        for file_path in affected_files:
            if self._validate_file_access(file_path):
                validation_result["valid_paths"].append(file_path)
            else:
                validation_result["invalid_paths"].append(file_path)
                validation_result["access_denied"].append(f"Access denied: {file_path}")

        return validation_result

    def set_user_allowed_paths(self, paths: List[str]):
        """设置用户允许的路径"""
        self.user_allowed_paths = paths
