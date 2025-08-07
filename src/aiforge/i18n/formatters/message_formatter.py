import re
from typing import Dict, Any


class ICUMessageFormatter:
    def format(self, message: str, **params) -> str:
        """支持ICU MessageFormat的格式化"""
        # 简单变量替换
        for key, value in params.items():
            message = message.replace(f"{{{key}}}", str(value))

        # 复数形式处理
        message = self._handle_plurals(message, params)

        # 选择形式处理
        message = self._handle_select(message, params)

        return message

    def _handle_select(self, message: str, params: Dict[str, Any]) -> str:
        """处理选择形式 {variable, select, option1{text1} option2{text2} other{default}}"""
        import re

        select_pattern = r"\{(\w+),\s*select,\s*([^}]+)\}"

        def replace_select(match):
            variable = match.group(1)
            options_str = match.group(2)

            # 解析选项
            option_pattern = r"(\w+)\{([^}]*)\}"
            options = {}

            for option_match in re.finditer(option_pattern, options_str):
                option_key = option_match.group(1)
                option_text = option_match.group(2)
                options[option_key] = option_text

            # 获取变量值
            value = str(params.get(variable, ""))

            # 选择对应的文本
            if value in options:
                return options[value]
            elif "other" in options:
                return options["other"]
            else:
                return f"{{{variable}}}"  # 回退到原始占位符

        return re.sub(select_pattern, replace_select, message)

    def _handle_plurals(self, message: str, params: Dict[str, Any]) -> str:
        """处理复数形式 {count, plural, =0{no items} =1{one item} other{# items}}"""
        plural_pattern = r"\{(\w+),\s*plural,\s*([^}]+)\}"

        def replace_plural(match):
            var_name = match.group(1)
            rules = match.group(2)
            count = params.get(var_name, 0)

            # 解析规则
            rule_pattern = r"(=\d+|zero|one|two|few|many|other)\{([^}]*)\}"
            rules_dict = {}
            for rule_match in re.finditer(rule_pattern, rules):
                rule_key = rule_match.group(1)
                rule_value = rule_match.group(2)
                rules_dict[rule_key] = rule_value

            # 选择合适的规则
            if f"={count}" in rules_dict:
                result = rules_dict[f"={count}"]
            elif count == 0 and "zero" in rules_dict:
                result = rules_dict["zero"]
            elif count == 1 and "one" in rules_dict:
                result = rules_dict["one"]
            else:
                result = rules_dict.get("other", str(count))

            return result.replace("#", str(count))

        return re.sub(plural_pattern, replace_plural, message)
