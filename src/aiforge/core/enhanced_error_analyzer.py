import re
from typing import Dict, List, Any


class EnhancedErrorAnalyzer:
    """增强的错误分析器 - 专注于错误分析和建议生成"""

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
    def generate_execution_feedback(error_info: str, traceback_info: str) -> Dict[str, Any]:
        """生成代码执行失败的反馈 - 直接传递具体错误信息"""
        error_analysis = EnhancedErrorAnalyzer.analyze_error(error_info, traceback_info)

        # 构建包含具体错误信息的反馈
        feedback = {
            "error_type": error_analysis["error_type"],
            "specific_error": error_info,  # 直接传递完整错误信息
            "suggestion": (
                error_analysis["fix_suggestions"][0]
                if error_analysis["fix_suggestions"]
                else "检查代码逻辑"
            ),
            "severity": error_analysis["severity"],
        }

        # 针对特定错误类型优化建议
        if error_analysis["error_type"] == "import_error" and "No module named" in error_info:
            module_name = re.search(r"No module named '([^']+)'", error_info)
            if module_name:
                module = module_name.group(1)
                # 检查是否是已知的不可用模块
                unavailable_modules = {
                    "feedparser": "feedparser 模块不可用，请使用 requests + BeautifulSoup",
                    "newspaper": "newspaper 模块不可用，请使用 requests + BeautifulSoup 爬取网页内容",
                    "scrapy": "scrapy 模块不可用，请使用 requests + BeautifulSoup 进行网页爬取",
                }

                if module in unavailable_modules:
                    feedback["suggestion"] = unavailable_modules[module]
                else:
                    feedback["suggestion"] = f"模块 {module} 不可用，请使用标准库替代"

        return feedback

    @staticmethod
    def analyze_basic_failure_reason(result: Dict[str, Any]) -> str:
        """分析基础验证失败的具体原因"""
        if not result.get("success", False):
            error = result.get("error", "未知错误")
            return f"代码执行失败: {error}"

        result_content = result.get("result")
        if result_content is None:
            return "执行结果为空"

        if isinstance(result_content, dict):
            status = result_content.get("status")
            if status == "error":
                summary = result_content.get("summary", "未知业务错误")
                return f"业务逻辑错误: {summary}"

            if "error" in result_content or "exception" in result_content:
                return "结果包含错误信息"

            data = result_content.get("data")
            if data is None:
                return "数据字段为空，未获取到有效数据"

            if isinstance(data, (list, dict)) and len(data) == 0:
                return "数据字段为空列表或字典，未获取到有效数据"

            if any(
                indicator in str(result_content).lower()
                for indicator in ["failed", "timeout", "connection error"]
            ):
                return "执行结果包含失败指标"

        if isinstance(result_content, str):
            if any(
                indicator in result_content.lower()
                for indicator in ["error", "failed", "exception", "timeout"]
            ):
                return "字符串结果包含错误信息"

            if not result_content.strip():
                return "字符串结果为空"

        if isinstance(result_content, (list, tuple)) and len(result_content) == 0:
            return "结果列表为空"

        return "验证失败，原因不明"

    @staticmethod
    def _generate_fix_suggestions(error_type: str, error_message: str) -> List[str]:
        """根据错误类型生成修复建议"""
        suggestions = []

        if error_type == "import_error":
            if "No module named" in error_message:
                module_match = re.search(r"No module named '([^']+)'", error_message)
                if module_match:
                    module_name = module_match.group(1)
                    if module_name == "feedparser":
                        suggestions.extend(
                            [
                                "使用 requests + xml.etree.ElementTree 解析 RSS",
                                "使用 requests + BeautifulSoup 爬取新闻网站",
                                "避免使用第三方 RSS 解析库",
                            ]
                        )
                    else:
                        suggestions.extend(
                            [
                                f"模块 {module_name} 不可用，请使用标准库替代",
                                "检查模块名拼写是否正确",
                                "使用内置库实现相同功能",
                            ]
                        )

        elif error_type == "name_error":
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
            msg = (
                analysis["error_message"][:50] + "..."
                if len(analysis["error_message"]) > 50
                else analysis["error_message"]
            )
            parts.append(f"消息:{msg}")

        if analysis["fix_suggestions"]:
            parts.append(f"建议:{analysis['fix_suggestions'][0]}")

        return " | ".join(parts)
