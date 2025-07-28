class CodeValidator:
    @staticmethod
    def validate_code(code: str) -> bool:
        """验证代码的基本可执行性和实用性"""
        if not code or not isinstance(code, str):
            return False

        # 检查语法
        try:
            compile(code, "<string>", "exec")
        except (SyntaxError, TypeError, ValueError):
            return False
        except Exception:
            return False

        # 拒绝只是简单数据赋值的代码
        lines = [line.strip() for line in code.strip().split("\n") if line.strip()]

        # 如果只有1-3行且都是简单赋值，认为不是有用的代码
        if len(lines) <= 3:
            assignment_lines = sum(
                1 for line in lines if "=" in line and not line.startswith("def ")
            )
            if assignment_lines == len(lines):
                return False

        # 必须包含一些实际的编程结构
        has_structure = any(
            keyword in code
            for keyword in ["def ", "class ", "import ", "from ", "if ", "for ", "while ", "try:"]
        )

        return has_structure
