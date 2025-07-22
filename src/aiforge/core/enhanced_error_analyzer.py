import re
from typing import Dict, List, Any


class EnhancedErrorAnalyzer:
    """增强的错误分析器"""

    @staticmethod
    def analyze_error(error_info: str, traceback_info: str) -> Dict[str, Any]:
        """分析错误信息，提取关键信息和修复建议"""
        analysis = {
            "error_type": "unknown",
            "error_message": "",
            "line_number": None,
            "file_name": None,
            "root_cause": "",
            "fix_suggestions": [],
            "severity": "medium",
            "compressed_info": "",
        }

        # 1. 提取错误类型和消息
        error_patterns = {
            r"(NameError): (.+)": ("name_error", "变量或函数未定义"),
            r"(TypeError): (.+)": ("type_error", "类型错误"),
            r"(ValueError): (.+)": ("value_error", "值错误"),
            r"(AttributeError): (.+)": ("attribute_error", "属性错误"),
            r"(ImportError|ModuleNotFoundError): (.+)": ("import_error", "导入错误"),
            r"(SyntaxError): (.+)": ("syntax_error", "语法错误"),
            r"(KeyError): (.+)": ("key_error", "键错误"),
            r"(IndexError): (.+)": ("index_error", "索引错误"),
        }

        for pattern, (error_type, description) in error_patterns.items():
            match = re.search(pattern, error_info)
            if match:
                analysis["error_type"] = error_type
                analysis["error_message"] = match.group(2).strip()
                analysis["root_cause"] = description
                break

        # 2. 提取行号和文件信息
        line_match = re.search(r"line (\d+)", traceback_info)
        if line_match:
            analysis["line_number"] = int(line_match.group(1))

        file_match = re.search(r'File "([^"]+)"', traceback_info)
        if file_match:
            analysis["file_name"] = file_match.group(1)

        # 3. 生成修复建议
        analysis["fix_suggestions"] = EnhancedErrorAnalyzer._generate_fix_suggestions(
            analysis["error_type"], analysis["error_message"]
        )

        # 4. 确定严重程度
        analysis["severity"] = EnhancedErrorAnalyzer._determine_severity(analysis["error_type"])

        # 5. 生成压缩信息
        analysis["compressed_info"] = EnhancedErrorAnalyzer._compress_error_info(analysis)

        return analysis

    @staticmethod
    def _generate_fix_suggestions(error_type: str, error_message: str) -> List[str]:
        """根据错误类型生成修复建议"""
        suggestions = []

        if error_type == "name_error":
            if "not defined" in error_message:
                var_name = re.search(r"'([^']+)' is not defined", error_message)
                if var_name:
                    suggestions.extend(
                        [
                            f"检查变量 '{var_name.group(1)}' 是否正确定义",
                            "确保变量在使用前已经赋值",
                            "检查变量名拼写是否正确",
                        ]
                    )

        elif error_type == "import_error":
            if "No module named" in error_message:
                module_match = re.search(r"No module named '([^']+)'", error_message)
                if module_match:
                    module_name = module_match.group(1)
                    suggestions.extend(
                        [
                            f"安装缺失的模块: pip install {module_name}",
                            "检查模块名拼写是否正确",
                            "确保模块在 Python 路径中",
                        ]
                    )

        elif error_type == "attribute_error":
            if "has no attribute" in error_message:
                suggestions.extend(
                    [
                        "检查对象是否有该属性或方法",
                        "确认对象类型是否正确",
                        "查看相关文档确认正确的属性名",
                    ]
                )

        elif error_type == "syntax_error":
            suggestions.extend(
                [
                    "检查代码语法，特别是括号、引号匹配",
                    "确认缩进是否正确",
                    "检查是否有多余的逗号或分号",
                ]
            )

        elif error_type == "type_error":
            suggestions.extend(
                ["检查函数参数类型是否正确", "确认操作符是否适用于该数据类型", "添加类型转换或验证"]
            )

        # 通用建议
        if not suggestions:
            suggestions.extend(["仔细阅读错误信息", "检查相关代码逻辑", "添加调试输出确认变量值"])

        return suggestions

    @staticmethod
    def _determine_severity(error_type: str) -> str:
        """确定错误严重程度"""
        high_severity = ["syntax_error", "import_error"]
        medium_severity = ["name_error", "attribute_error", "type_error"]
        low_severity = ["key_error", "index_error", "value_error"]

        if error_type in high_severity:
            return "high"
        elif error_type in medium_severity:
            return "medium"
        elif error_type in low_severity:
            return "low"
        else:
            return "medium"

    @staticmethod
    def _compress_error_info(analysis: Dict[str, Any]) -> str:
        """压缩错误信息为简洁格式"""
        parts = []

        if analysis["error_type"] != "unknown":
            parts.append(f"类型:{analysis['error_type']}")

        if analysis["line_number"]:
            parts.append(f"行:{analysis['line_number']}")

        if analysis["error_message"]:
            # 截取错误消息的关键部分
            msg = (
                analysis["error_message"][:50] + "..."
                if len(analysis["error_message"]) > 50
                else analysis["error_message"]
            )
            parts.append(f"消息:{msg}")

        if analysis["fix_suggestions"]:
            # 只取第一个建议
            parts.append(f"建议:{analysis['fix_suggestions'][0]}")

        return " | ".join(parts)
