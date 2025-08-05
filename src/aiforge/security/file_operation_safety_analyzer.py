from pathlib import Path
import re
from typing import Dict, Any, List
import os


class FileOperationSafetyAnalyzer:
    """文件操作安全分析器"""

    def __init__(self, workdir: str = None, user_allowed_paths: List[str] = None):
        """初始化安全分析器

        Args:
            workdir: 工作目录
            user_allowed_paths: 用户指定的允许访问路径列表
        """
        self.workdir = Path(workdir) if workdir else Path.cwd()
        self.user_allowed_paths = user_allowed_paths or []

    def analyze_operation_risk(self, code: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """分析文件操作风险等级"""
        risk_analysis = {
            "risk_level": "low",
            "destructive_operations": [],
            "affected_files": self._extract_affected_files(parameters),
            "backup_required": False,
            "confirmation_required": False,
            "path_validation": self._validate_operation_paths(parameters),  # 新增路径验证
        }

        # 检查路径访问权限
        if risk_analysis["path_validation"]["invalid_paths"]:
            risk_analysis["risk_level"] = "high"
            risk_analysis["confirmation_required"] = True

        # 修复正则表达式
        destructive_patterns = [
            r"\.delete\(\)",
            r"os\.remove\(",
            r"shutil\.rmtree\(",
            r"\.unlink\(\)",
            r"os\.rmdir\(",
            r"\.truncate\(",
        ]

        for pattern in destructive_patterns:
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
        """验证文件访问权限，支持用户指定的允许路径"""
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
        self.user_allowed_paths = paths or []
