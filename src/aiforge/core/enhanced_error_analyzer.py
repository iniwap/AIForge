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
    def generate_execution_feedback(error_info: str, traceback_info: str) -> Dict[str, Any]:
        """生成代码执行失败的反馈"""
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

    @staticmethod
    def generate_validation_feedback(
        failure_reason: str,
        validation_details: Dict[str, Any],
        attempt_num: int,
        expected_output: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """生成验证失败的反馈"""

        # 分析验证失败类型
        validation_type = validation_details.get("validation_type", "unknown")

        # 解析失败原因中的关键信息
        failure_analysis = EnhancedErrorAnalyzer._analyze_validation_failure(failure_reason)

        # 构建基础反馈结构
        feedback = {
            "validation_type": validation_type,
            "specific_failure": failure_reason,
            "suggestion": "",
            "severity": "medium",
            "attempt_context": f"第{attempt_num}次尝试",
            "failure_category": failure_analysis["category"],
        }

        # 根据验证类型生成具体建议
        if validation_type == "local_basic":
            feedback["suggestion"] = EnhancedErrorAnalyzer._generate_basic_validation_suggestions(
                failure_reason, attempt_num
            )
            feedback["severity"] = "high"

        elif validation_type == "local_business":
            feedback["suggestion"] = (
                EnhancedErrorAnalyzer._generate_business_validation_suggestions(
                    failure_reason, expected_output, attempt_num
                )
            )
            feedback["severity"] = "medium"

        elif validation_type == "ai_deep":
            feedback["suggestion"] = EnhancedErrorAnalyzer._generate_ai_validation_suggestions(
                failure_reason, attempt_num
            )
            feedback["severity"] = "low"
        else:
            feedback["suggestion"] = "请检查代码逻辑，确保输出符合预期格式"

        # 根据尝试次数调整建议的具体程度
        if attempt_num >= 2:
            feedback["suggestion"] += f" (已尝试{attempt_num}次，请仔细检查数据获取逻辑)"

        return feedback

    @staticmethod
    def _analyze_validation_failure(failure_reason: str) -> Dict[str, str]:
        """分析验证失败原因的类别"""
        failure_reason_lower = failure_reason.lower()

        if "数据字段为空" in failure_reason_lower or "未获取到有效数据" in failure_reason_lower:
            return {"category": "empty_data", "type": "数据为空"}
        elif "缺少必需字段" in failure_reason_lower:
            return {"category": "missing_field", "type": "字段缺失"}
        elif "结果数量" in failure_reason_lower and "少于最小要求" in failure_reason_lower:
            return {"category": "insufficient_data", "type": "数据不足"}
        elif "字段" in failure_reason_lower and "不应为空" in failure_reason_lower:
            return {"category": "empty_field", "type": "字段为空"}
        elif "状态为错误" in failure_reason_lower:
            return {"category": "error_status", "type": "状态错误"}
        else:
            return {"category": "unknown", "type": "未知错误"}

    @staticmethod
    def _generate_basic_validation_suggestions(failure_reason: str, attempt_num: int) -> str:
        """生成基础验证失败的建议"""
        failure_reason_lower = failure_reason.lower()

        if "代码执行失败" in failure_reason_lower:
            return "检查代码语法和逻辑错误，确保所有变量都已正确定义"
        elif "执行结果为None" in failure_reason_lower:
            return "确保代码中有 __result__ = 结果 的赋值语句"
        elif "执行结果为空" in failure_reason_lower:
            return "检查数据获取逻辑，确保能够获取到有效数据"
        elif "数据字段为空" in failure_reason_lower:
            return "优化数据获取策略，检查API调用或网页爬取逻辑是否正确"
        else:
            return "检查代码基础逻辑，确保执行成功并返回有效结果"

    @staticmethod
    def _generate_business_validation_suggestions(
        failure_reason: str, expected_output: Dict[str, Any], attempt_num: int
    ) -> str:
        """生成业务逻辑验证失败的建议"""
        if "缺少必需字段" in failure_reason:
            # 提取缺少的字段名
            field_match = re.search(r"缺少必需字段: (\\w+)", failure_reason)
            if field_match:
                missing_field = field_match.group(1)
                if expected_output:
                    required_fields = expected_output.get("required_fields", [])
                    return f"请在结果中添加 '{missing_field}' 字段。必需字段包括: {', '.join(required_fields)}"
                else:
                    return f"请在结果中添加 '{missing_field}' 字段"
            else:
                return "检查输出格式，确保包含所有必需字段"

        elif "结果数量" in failure_reason and "少于最小要求" in failure_reason:
            # 提取数量信息
            count_match = re.search(r"结果数量 (\\d+) 少于最小要求 (\\d+)", failure_reason)
            if count_match:
                actual_count = count_match.group(1)
                required_count = count_match.group(2)
                return f"当前获取到{actual_count}条数据，需要至少{required_count}条。请优化搜索策略或扩大搜索范围"
            else:
                return "增加数据获取数量，优化搜索关键词或扩大搜索范围"

        elif "字段" in failure_reason and "不应为空" in failure_reason:
            field_match = re.search(r"字段 (\\w+) 不应为空", failure_reason)
            if field_match:
                empty_field = field_match.group(1)
                return f"确保 '{empty_field}' 字段包含有效内容，不能为空值、空字符串或空列表"
            else:
                return "检查所有字段内容，确保非空字段都包含有效数据"

        elif "未找到成功执行的指示器" in failure_reason:
            return "确保数据获取成功，检查 data 字段是否包含有效内容"

        else:
            return "检查业务逻辑，确保输出数据符合预期格式和内容要求"

    @staticmethod
    def _generate_ai_validation_suggestions(failure_reason: str, attempt_num: int) -> str:
        """生成AI深度验证失败的建议"""
        if "AI验证失败" in failure_reason:
            return "结果虽然格式正确但内容质量不符合要求，请优化数据获取的准确性和完整性"
        else:
            return "提升结果质量，确保数据内容真实有效且符合用户需求"
