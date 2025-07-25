from typing import Optional, Dict, Any


def get_task_specific_format(task_type: str, expected_output: Dict[str, Any] = None) -> str:
    """基于AI分析结果动态生成输出格式要求"""
    if not expected_output:
        # 回退到基础格式
        return """
# 输出格式要求：
__result__ = {
    "data": main_result,
    "status": "success/error",
    "summary": "结果摘要",
    "metadata": {"timestamp": "...", "task_type": "..."}
}"""

    # 基于AI分析的预期输出规则生成格式
    required_fields = expected_output.get("required_fields", [])
    expected_data_type = expected_output.get("expected_data_type", "dict")

    # 构建data字段示例
    data_example = {}
    for field in required_fields:
        data_example[field] = f"{field}_value"

    # 添加验证规则中的非空字段说明
    validation_rules = expected_output.get("validation_rules", {})
    non_empty_fields = validation_rules.get("non_empty_fields", [])

    format_str = f"""
# 基于AI分析的输出格式要求：
__result__ = {{
    "data": {data_example},
    "status": "success",
    "summary": "任务完成描述",
    "metadata": {{"timestamp": "...", "task_type": "{task_type}"}}
}}

# 必需字段：{', '.join(required_fields)}
# 非空字段：{', '.join(non_empty_fields)}
# 数据类型：{expected_data_type}
"""
    return format_str


def get_base_aiforge_prompt(optimize_tokens: bool = True) -> str:
    """生成基础的AIForge系统提示"""
    # 基础代码生成规则
    code_rule = """
- 生成的代码必须能在标准 Python 环境中直接执行
- 使用标准 Markdown 代码块格式：```python ... ```，不要输出任何解释性文字
- 使用预装库：requests, BeautifulSoup, pandas, numpy 等
- 实现完整的错误处理和异常捕获
"""

    if optimize_tokens:
        code_rule += "\n- 生成极简代码，无注释，无空行\n- 使用最短变量名(a,b,c,d等)"

    # 构建基础 prompt
    base_prompt = f"""
# AIForge：Python 代码生成和执行助手

# 代码生成规范
{code_rule}

# 执行规范
执行代码，并将执行结果赋值给 __result__

"""
    return base_prompt


def _get_enhanced_aiforge_prompt_with_universal_validation(
    optimize_tokens: bool = True,
    task_type: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    expected_output: Optional[Dict[str, Any]] = None,  # 新增参数
) -> str:
    """生成带通用参数验证约束的增强系统提示"""

    base_prompt = get_base_aiforge_prompt(optimize_tokens)

    execution_guidance = ""
    if parameters:
        param_analysis = _analyze_parameters_for_execution(parameters)

        execution_guidance = f"""
## 🔧 智能参数化执行指导

基于任务分析，生成以下参数化函数：

def execute_task({param_analysis['signature']}):
    '''
    {param_analysis['docstring']}
    '''
    # 🚨 通用参数使用要求：
    # 1. 每个参数都必须在函数逻辑中被实际使用
    # 2. 参数值必须影响函数的执行结果或返回值
    # 3. 不得硬编码任何可以从参数获取的值
    # 4. 参数应该用于控制函数的行为、数据源或输出格式

    # 实现逻辑应该基于参数的实际含义和任务需求
    return result_data

# 参数说明：
{param_analysis['param_docs']}

🚨 必须在函数定义后立即调用：
__result__ = execute_task({param_analysis['call_args']})

## 📋 通用参数使用验证标准：
1. 参数必须在函数体内被引用和使用
2. 参数的值必须影响函数的执行路径或结果
3. 避免硬编码任何可以通过参数传递的值
4. 参数应该用于：
   - 控制函数行为（条件判断、循环控制）
   - 作为数据源（API调用、文件路径、查询条件）
   - 影响输出格式（格式化、过滤、排序）
   - 配置执行参数（超时、重试次数、精度）

## ❌ 通用禁止模式：
- 定义参数但不在函数体中使用
- 参数仅用于字符串拼接显示，不影响核心逻辑
- 硬编码值而忽略相应参数
- 参数仅用于注释或日志，不参与业务逻辑
"""

    enhanced_prompt = f"""
{base_prompt}

{execution_guidance}
"""

    # 使用AI分析结果生成格式要求，而不是内置格式
    enhanced_prompt += f"\n\n{get_task_specific_format(task_type, expected_output)}"

    return enhanced_prompt


def _analyze_parameters_for_execution(parameters: Dict[str, Any]) -> Dict[str, str]:
    """分析参数结构，生成执行指导"""
    param_names = []
    param_docs = []
    call_args = []

    for param_name, param_info in parameters.items():
        if isinstance(param_info, dict):
            value = param_info.get("value")
            param_type = param_info.get("type", "str")
            description = param_info.get("description", "")
            required = param_info.get("required", True)

            # 构建函数签名
            if required and value is not None:
                param_names.append(param_name)
                call_args.append(f'"{value}"' if param_type == "str" else str(value))
            elif not required:
                default_val = param_info.get("default", "None")
                param_names.append(f"{param_name}={default_val}")
                if value is not None:
                    call_args.append(f'"{value}"' if param_type == "str" else str(value))
                else:
                    if default_val is None:
                        call_args.append("None")
                    else:
                        call_args.append(str(default_val))

            # 构建参数文档
            param_docs.append(f"- {param_name} ({param_type}): {description}")
        else:
            # 简单参数处理
            param_names.append(param_name)
            call_args.append(f'"{param_info}"' if isinstance(param_info, str) else str(param_info))
            param_docs.append(f"- {param_name}: {param_info}")

    signature = ", ".join(param_names)
    call_signature = ", ".join(call_args)
    docstring = f"执行任务，使用提供的参数: {', '.join(param_names)}"

    return {
        "signature": signature,
        "call_args": call_signature,
        "param_docs": "\n".join(param_docs),
        "docstring": docstring,
    }


def get_direct_response_prompt(action: str, standardized_instruction: Dict[str, Any]) -> str:
    """构建直接响应专用提示词"""
    # 基础提示词映射
    prompts = {
        "answer": "你是一个知识助手，请直接回答用户的问题。要求准确、简洁、有用。",
        "respond": "你是一个知识助手，请直接回答用户的问题。要求准确、简洁、有用。",
        "create": "你是一个内容创作助手，请根据用户要求创作内容。注意风格和格式要求。",
        "translate": "你是一个翻译助手，请准确翻译用户提供的内容。保持原意和语言风格。",
        "summarize": "你是一个文本分析助手，请总结和分析用户提供的文本内容。",
        "suggest": "你是一个咨询顾问，请根据用户需求提供建议和意见。",
    }

    base_prompt = prompts.get(action, "你是一个AI助手，请直接响应用户的需求。")

    # 从 standardized_instruction 中提取增强信息
    target = standardized_instruction.get("target", "")
    output_format = standardized_instruction.get("output_format", "text")
    parameters = standardized_instruction.get("parameters", {})
    task_type = standardized_instruction.get("task_type", "")

    # 构建增强的提示词
    enhanced_sections = []

    # 1. 任务上下文增强
    if target:
        enhanced_sections.append(f"任务目标: {target}")

    # 2. 输出格式指导
    format_guidance = {
        "text": "以纯文本形式回答",
        "markdown": "使用Markdown格式，包含适当的标题、列表和强调",
        "structured_text": "使用结构化的文本格式，包含清晰的段落和要点",
    }

    if output_format in format_guidance:
        enhanced_sections.append(f"输出要求: {format_guidance[output_format]}")

    # 3. 参数上下文增强
    if parameters:
        param_context = []
        for param_name, param_value in parameters.items():
            if param_value:
                param_context.append(f"- {param_name}: {param_value}")

        if param_context:
            enhanced_sections.append("相关参数:\n" + "\n".join(param_context))

    # 4. 任务类型特定指导
    task_specific_guidance = {
        "direct_response": "专注于直接回答，避免冗余信息",
        "content_generation": "注重创意和原创性",
        "data_process": "提供清晰的分析思路",
    }

    if task_type in task_specific_guidance:
        enhanced_sections.append(f"特殊要求: {task_specific_guidance[task_type]}")

    # 组装最终提示词
    enhanced_prompt = base_prompt

    if enhanced_sections:
        enhanced_prompt += "\n\n## 任务详情\n" + "\n\n".join(enhanced_sections)

    enhanced_prompt += """

## 重要限制
- 直接提供最终答案，不要生成代码
- 如果任务需要实时数据或文件操作，请说明无法完成
- 保持回答的专业性和准确性
"""

    return enhanced_prompt


def get_enhanced_system_prompt_universal(
    standardized_instruction: Dict[str, Any], optimize_tokens=True, original_prompt: str = None
) -> str:
    """基于标准化指令构建通用增强系统提示词"""
    task_type = standardized_instruction.get("task_type", "general")

    # 获取参数信息
    parameters = standardized_instruction.get("required_parameters", {})
    if not parameters:
        parameters = standardized_instruction.get("parameters", {})

    # 获取AI分析的预期输出规则
    expected_output = standardized_instruction.get("expected_output")

    # 最后的回退：确保有基本的指令参数
    if not parameters:
        parameters = {
            "instruction": {
                "value": standardized_instruction.get("target", ""),
                "type": "str",
                "description": "用户输入的指令内容",
                "required": True,
            }
        }

    # 使用通用增强版提示词生成，传递预期输出规则
    enhanced_prompt = _get_enhanced_aiforge_prompt_with_universal_validation(
        optimize_tokens=optimize_tokens,
        task_type=task_type,
        parameters=parameters,
        expected_output=expected_output,  # 传递AI分析结果
    )

    if original_prompt:
        enhanced_prompt += f"\n\n# 原始指令补充\n{original_prompt}"

    return enhanced_prompt


def get_base_prompt_sections() -> Dict[str, str]:
    """构建基础提示词各个部分"""
    return {
        "role": "你是 AIForge 智能任务分析器，负责理解用户指令并分析完成任务所需的必要信息。",
        "execution_mode": """
## 直接响应类型特征：
- 纯知识问答、概念解释、定义说明（非时效性）
- 文本创作、写作、翻译、改写
- 历史信息查询、理论分析
- 建议咨询、意见评价（基于已有知识）
- 对话延续和情感支持（感谢、追问、补充说明等）
- 可以通过AI的知识和语言能力直接完成且不需要最新数据

## 代码执行类型特征：
- 需要访问外部数据源（API、网页、文件系统）
- 需要实时信息获取（天气、股价、新闻、汇率等）
- 需要最新数据的查询和分析
- 需要数据计算、统计、处理、转换
- 需要文件操作、系统交互、自动化任务
""",
        "analysis_steps": """
## 对于直接响应类型：
1. 理解用户想要获得什么信息或内容
2. 确认信息不涉及时效性要求
3. 确认可以通过AI知识直接提供
4. 判断是否为对话延续（感谢、追问、情感表达等）

## 对于代码执行类型：
1. 理解用户想要完成什么任务
2. 识别是否需要最新数据或实时信息
3. 思考完成这个任务的必要条件和输入信息
4. 从用户指令中提取这些信息的具体值

## 对话上下文判断：
如果用户指令是对话的延续（如感谢、追问、补充说明、情感表达等），请：
1. 设置 execution_mode 为 "direct_ai_response"
2. 在 reasoning 中说明这是对话延续
3. 适当提高 confidence 值到 0.8 以上

## 动作命名规范：
1. 基于任务类型生成标准化动作名
2. 使用语义特征而非特定领域词汇
3. 保持动作名称的一致性和可扩展性
4. 优先使用英文动作名确保系统兼容性
""",
        "action_vocabulary": """
## 标准动作生成规则：
- 数据获取类任务 → fetch_{task_type_suffix}
- 数据处理类任务 → process_{task_type_suffix}
- 内容生成类任务 → generate_{task_type_suffix}
- 文件操作类任务 → transform_{task_type_suffix}
- 直接响应类任务 → respond_{task_type_suffix}

## 语义特征识别：
- 包含获取、查询、搜索等语义 → 归类为数据获取
- 包含分析、处理、计算等语义 → 归类为数据处理
- 包含生成、创建、制作等语义 → 归类为内容生成
- 包含回答、解释、响应等语义 → 归类为直接响应

注意：避免硬编码特定领域词汇，使用通用语义特征进行分类
""",
        "output_format": """{
    "task_type": "任务类型",
    "action": "具体动作",
    "target": "任务描述",
    "execution_mode": "direct_ai_response 或 code_generation",
    "confidence": "置信度",
    "reasoning": "判断理由",
    "required_parameters": {
        "param_name": {
            "value": "从指令中提取的值或null",
            "type": "参数类型",
            "description": "参数用途说明",
            "required": true/false,
            "default": "默认值或null"
        }
    },
    "execution_logic": "完成任务的基本逻辑描述",
    "output_format": "期望输出格式"
}""",
        "principles": """
- 专注于任务完成的必要性，而非指令的字面内容
- 参数应该是执行任务的最小必要集合
- **预期输出应采用最低限度满足用户需求的策略**
- **避免过度详细的验证规则，优先保证任务成功执行**
- 优先从指令中提取具体值，无法提取时考虑合理默认值
- 参数命名应该清晰反映其在任务中的作用
""",
        "examples": """
用户指令："北京今天的天气如何"
思考：要获取天气信息，我需要知道：
1. 地点：北京
2. 时间：今天
3. 信息类型：天气
执行模式：code_generation

用户指令："解释什么是机器学习"
思考：这是纯知识问答，不需要外部数据
执行模式：direct_ai_response

用户指令："谢谢你的解释，我还想了解深度学习"
思考：这是对话延续，用户在感谢并追问相关问题
执行模式：direct_ai_response
""",
    }
