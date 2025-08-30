import time
from typing import Dict, Any, List, Optional, Protocol, Tuple
from enum import Enum


class ExecutionMode(Enum):
    DIRECT_AI_RESPONSE = "direct_ai_response"
    CODE_GENERATION = "code_generation"


class SecurityLevel(Enum):
    SAFE = "safe"  # 纯LLM操作，无风险
    LOW = "low"  # 读取操作，低风险
    MEDIUM = "medium"  # 网络访问，中等风险
    HIGH = "high"  # 文件写入，高风险
    CRITICAL = "critical"  # 系统级操作，严重风险


# 基础任务类型定义
BASE_TASK_TYPES = {
    # 第一层：核心任务类型
    "knowledge_response": {
        "execution_mode": ExecutionMode.DIRECT_AI_RESPONSE,
        "security_level": SecurityLevel.SAFE,
        "subtypes": {
            "qa": {"actions": ["answer"], "params": ["content"]},
            "explanation": {"actions": ["explain"], "params": ["content", "level"]},
            "advice": {"actions": ["suggest"], "params": ["content", "context"]},
            "translation": {
                "actions": ["translate"],
                "params": ["content", "source_lang", "target_lang"],
            },
            "summarization": {"actions": ["summarize"], "params": ["content", "length"]},
            "chat_ai": {"actions": ["chat"], "params": ["content", "context"]},
        },
        "data_patterns": ["response", "answer", "explanation", "suggestion", "advice"],
        "structure_patterns": ["simple_response", "detailed_response"],
        "ui_types": ["card", "editor", "text"],
    },
    "content_creation": {
        "execution_mode": ExecutionMode.CODE_GENERATION,
        "security_level": SecurityLevel.SAFE,
        "subtypes": {
            "article": {"actions": ["generate", "write"], "params": ["topic", "style", "length"]},
            "document": {"actions": ["create", "generate"], "params": ["template", "format"]},
            "report": {"actions": ["generate", "create"], "params": ["data_source", "template"]},
            "creative": {"actions": ["create", "compose"], "params": ["style", "theme"]},
        },
        "data_patterns": ["generated_content", "content", "text", "article", "document"],
        "structure_patterns": ["single_content", "structured_content"],
        "ui_types": ["editor", "card"],
    },
    "information_retrieval": {
        "execution_mode": ExecutionMode.CODE_GENERATION,
        "security_level": SecurityLevel.MEDIUM,
        "subtypes": {
            "web_search": {"actions": ["search"], "params": ["query", "max_results", "time_range"]},
            "api_query": {"actions": ["fetch"], "params": ["endpoint", "params", "auth"]},
            "file_read": {"actions": ["read", "extract"], "params": ["file_path", "format"]},
            "db_query": {"actions": ["query"], "params": ["connection", "sql", "table"]},
        },
        "data_patterns": ["content", "source", "title", "url", "results", "query"],
        "structure_patterns": ["search_results", "result_list", "single_item"],
        "ui_types": ["card", "table", "list", "map"],
    },
    # 第二层：扩展任务类型
    "data_processing": {
        "execution_mode": ExecutionMode.CODE_GENERATION,
        "security_level": SecurityLevel.LOW,
        "subtypes": {
            "data_cleaning": {"actions": ["clean"], "params": ["data_source", "rules"]},
            "data_transformation": {
                "actions": ["transform"],
                "params": ["data_source", "target_format"],
            },
            "data_analysis": {"actions": ["analyze"], "params": ["data_source", "method"]},
            "data_visualization": {
                "actions": ["visualize"],
                "params": ["data_source", "chart_type"],
            },
            "statistical_computation": {
                "actions": ["calculate"],
                "params": ["data_source", "metrics"],
            },
        },
        "data_patterns": ["processed_data", "analysis", "metrics", "trends", "chart_data"],
        "structure_patterns": ["processing_result", "analysis_report", "statistical_data"],
        "ui_types": ["dashboard", "chart", "table", "timeline"],
    },
    "code_development": {
        "execution_mode": ExecutionMode.CODE_GENERATION,
        "security_level": SecurityLevel.MEDIUM,
        "subtypes": {
            "script_generation": {"actions": ["generate"], "params": ["language", "purpose"]},
            "function_creation": {"actions": ["create"], "params": ["signature", "logic"]},
            "code_analysis": {"actions": ["analyze"], "params": ["file_path", "metrics"]},
            "testing": {"actions": ["test"], "params": ["target_code", "test_type"]},
            "refactoring": {"actions": ["refactor"], "params": ["file_path", "strategy"]},
        },
        "data_patterns": ["generated_code", "code", "script", "function", "language"],
        "structure_patterns": ["code_block", "code_file", "code_snippet"],
        "ui_types": ["editor", "card"],
    },
    # 第三层：高级任务类型（包含系统交互）
    "system_interaction": {
        "execution_mode": ExecutionMode.CODE_GENERATION,
        "security_level": SecurityLevel.CRITICAL,
        "subtypes": {
            # 基础文件系统操作
            "file_management": {
                "actions": ["create", "delete", "copy", "move", "rename"],
                "params": ["source_path", "target_path", "recursive", "force"],
            },
            # Windows注册表操作
            "registry_operations": {
                "actions": ["read", "write", "modify", "delete", "backup"],
                "params": ["key_path", "value_name", "value", "value_type", "backup_path"],
            },
            # 批处理和脚本执行
            "batch_execution": {
                "actions": ["execute", "run", "call"],
                "params": ["script_path", "args", "working_dir", "timeout", "admin_required"],
            },
            # 进程和服务管理
            "process_management": {
                "actions": ["start", "stop", "kill", "monitor", "list"],
                "params": ["process_name", "args", "priority", "user"],
            },
            # 系统监控
            "system_monitoring": {
                "actions": ["monitor", "check", "report"],
                "params": ["resource_type", "interval", "threshold", "alert"],
            },
            # Windows服务管理
            "service_management": {
                "actions": ["start", "stop", "restart", "enable", "disable"],
                "params": ["service_name", "startup_type"],
            },
            # 环境变量配置
            "environment_config": {
                "actions": ["set", "get", "delete", "list"],
                "params": ["var_name", "value", "scope", "persistent"],
            },
            # 网络诊断
            "network_diagnostics": {
                "actions": ["ping", "tracert", "nslookup", "netstat", "scan"],
                "params": ["target", "port", "protocol", "timeout"],
            },
        },
        "data_patterns": [
            "system_status",
            "process_info",
            "file_info",
            "registry_data",
            "service_status",
            "network_info",
        ],
        "structure_patterns": [
            "system_report",
            "operation_result",
            "status_list",
            "diagnostic_result",
        ],
        "ui_types": ["table", "progress", "timeline", "dashboard", "text"],
    },
    "automation_workflow": {
        "execution_mode": ExecutionMode.CODE_GENERATION,
        "security_level": SecurityLevel.HIGH,
        "subtypes": {
            "task_scheduling": {
                "actions": ["schedule"],
                "params": ["task", "interval", "condition"],
            },
            "workflow_orchestration": {
                "actions": ["orchestrate"],
                "params": ["steps", "dependencies"],
            },
            "notification": {"actions": ["notify"], "params": ["message", "channel", "recipients"]},
            "browser_automation": {"actions": ["automate"], "params": ["url", "actions", "data"]},
            "desktop_automation": {"actions": ["automate"], "params": ["application", "actions"]},
        },
        "data_patterns": ["automation_steps", "workflow", "status", "schedule", "notification"],
        "structure_patterns": ["automation_result", "workflow_status", "schedule_info"],
        "ui_types": ["timeline", "calendar", "progress", "table"],
    },
    "multimedia_processing": {
        "execution_mode": ExecutionMode.CODE_GENERATION,
        "security_level": SecurityLevel.MEDIUM,
        "subtypes": {
            "image_processing": {
                "actions": ["process", "convert"],
                "params": ["input_file", "operations"],
            },
            "audio_processing": {
                "actions": ["process", "convert"],
                "params": ["input_file", "format"],
            },
            "video_processing": {
                "actions": ["process", "convert"],
                "params": ["input_file", "operations"],
            },
            "ocr": {"actions": ["recognize"], "params": ["input_file", "language"]},
            "document_processing": {
                "actions": ["extract", "convert"],
                "params": ["input_file", "target_format"],
            },
        },
        "data_patterns": ["processed_media", "image", "audio", "video", "text", "document"],
        "structure_patterns": ["media_result", "processing_summary", "extraction_result"],
        "ui_types": ["gallery", "player", "editor", "table"],
    },
}

# 扩展机制：动态任务类型注册
DYNAMIC_TASK_TYPES = {}


class TaskTypeRegistry:
    """任务类型注册器 - 支持动态扩展而不影响核心功能"""

    @classmethod
    def register_task_type(cls, task_type: str, definition: Dict[str, Any]) -> bool:
        """注册新的任务类型"""
        if task_type in BASE_TASK_TYPES:
            return False  # 不允许覆盖基础类型

        # 验证定义格式
        if cls._validate_task_definition(definition):
            DYNAMIC_TASK_TYPES[task_type] = definition
            return True
        return False

    @classmethod
    def get_all_task_types(cls) -> Dict[str, Any]:
        """获取所有任务类型（基础+动态）"""
        return {**BASE_TASK_TYPES, **DYNAMIC_TASK_TYPES}

    @classmethod
    def _validate_task_definition(cls, definition: Dict[str, Any]) -> bool:
        """验证任务类型定义的完整性"""
        required_fields = [
            "execution_mode",
            "security_level",
            "subtypes",
            "data_patterns",
            "structure_patterns",
            "ui_types",
        ]
        return all(field in definition for field in required_fields)


class TaskTypeProvider(Protocol):
    """任务类型提供者协议"""

    def get_task_config(self, task_type: str) -> Optional[Dict[str, Any]]:
        """获取任务类型配置"""
        ...

    def get_execution_mode(self, task_type: str) -> Optional[ExecutionMode]:
        """获取执行模式"""
        ...

    def get_security_level(self, task_type: str) -> Optional[SecurityLevel]:
        """获取安全级别"""
        ...

    def get_subtypes(self, task_type: str) -> Dict[str, Dict[str, Any]]:
        """获取子类型定义"""
        ...

    def supports_task_type(self, task_type: str) -> bool:
        """检查是否支持指定任务类型"""
        ...


class TaskTypeResolver:
    """任务类型解析器 - 支持多提供者和层级查找"""

    def __init__(self):
        self._providers: List[Tuple[TaskTypeProvider, int]] = []  # (provider, priority)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def register_provider(self, provider: TaskTypeProvider, priority: int = 0):
        """注册任务类型提供者"""
        self._providers.append((provider, priority))
        self._providers.sort(key=lambda x: x[1], reverse=True)
        self._cache.clear()

    def resolve_task_type(self, task_type: str) -> Optional[Dict[str, Any]]:
        """解析任务类型，支持层级查找"""
        if task_type in self._cache:
            return self._cache[task_type]

        # 支持点分隔的层级结构
        parts = task_type.split(".")
        for i in range(len(parts), 0, -1):
            current_type = ".".join(parts[:i])

            for provider, _ in self._providers:
                if provider.supports_task_type(current_type):
                    config = provider.get_task_config(current_type)
                    if config:
                        # 如果是子类型查找，需要进一步解析
                        if i < len(parts):
                            config = self._resolve_subtype_config(config, parts[i:])
                            if config is None:
                                # 子类型解析失败，记录日志
                                continue

                        self._cache[task_type] = config
                        return config

        return None

    def _resolve_subtype_config(
        self, parent_config: Dict[str, Any], subtype_path: List[str]
    ) -> Dict[str, Any]:
        """解析子类型配置"""
        current = parent_config
        for subtype in subtype_path:
            if "subtypes" in current and subtype in current["subtypes"]:
                # 合并父类型和子类型配置
                subtype_config = current["subtypes"][subtype].copy()
                merged_config = {
                    **parent_config,
                    **subtype_config,
                    "parent_type": current.get("type", ""),
                    "subtype": subtype,
                }
                current = merged_config
            else:
                return None
        return current


class EnhancedTaskTypeRegistry(TaskTypeProvider):
    """增强的任务类型注册器"""

    def __init__(self):
        self._base_types = BASE_TASK_TYPES.copy()
        self._dynamic_types = DYNAMIC_TASK_TYPES.copy()
        self._version = "1.0.0"
        self._migration_rules = []

    def get_task_config(self, task_type: str) -> Optional[Dict[str, Any]]:
        """获取任务配置，支持版本迁移"""
        all_types = {**self._base_types, **self._dynamic_types}

        if task_type in all_types:
            config = all_types[task_type].copy()
            return self._migrate_config(config)
        return None

    def get_execution_mode(self, task_type: str) -> Optional[ExecutionMode]:
        config = self.get_task_config(task_type)
        return config.get("execution_mode") if config else None

    def get_security_level(self, task_type: str) -> Optional[SecurityLevel]:
        config = self.get_task_config(task_type)
        return config.get("security_level") if config else None

    def get_subtypes(self, task_type: str) -> Dict[str, Dict[str, Any]]:
        config = self.get_task_config(task_type)
        return config.get("subtypes", {}) if config else {}

    def supports_task_type(self, task_type: str) -> bool:
        all_types = {**self._base_types, **self._dynamic_types}
        return task_type in all_types

    def register_task_type(self, task_type: str, definition: Dict[str, Any]) -> bool:
        """注册新任务类型，支持版本验证"""
        if task_type in self._base_types:
            return False

        if self._validate_task_definition(definition):
            # 添加版本信息
            definition["version"] = definition.get("version", self._version)
            definition["registered_at"] = time.time()

            self._dynamic_types[task_type] = definition
            return True
        return False

    def _migrate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """配置版本迁移"""
        config_version = config.get("version", "1.0.0")
        if config_version == self._version:
            return config

        # 应用迁移规则
        for rule in self._migration_rules:
            if rule.can_migrate(config_version, self._version):
                config = rule.migrate(config)

        return config

    def add_migration_rule(self, rule):
        """添加迁移规则"""
        self._migration_rules.append(rule)

    @classmethod
    def _validate_task_definition(cls, definition: Dict[str, Any]) -> bool:
        """增强的定义验证"""
        required_fields = [
            "execution_mode",
            "security_level",
            "subtypes",
            "data_patterns",
            "structure_patterns",
            "ui_types",
        ]

        # 基础字段验证
        if not all(field in definition for field in required_fields):
            return False

        # 枚举值验证
        if not isinstance(definition["execution_mode"], ExecutionMode):
            return False

        if not isinstance(definition["security_level"], SecurityLevel):
            return False

        # 子类型结构验证
        subtypes = definition.get("subtypes", {})
        for subtype_name, subtype_config in subtypes.items():
            if not isinstance(subtype_config, dict):
                return False
            if "actions" not in subtype_config or "params" not in subtype_config:
                return False

        return True


class TaskTypeContext:
    """任务类型上下文管理器 - 提供统一的任务类型访问接口"""

    def __init__(self):
        self.resolver = TaskTypeResolver()
        self._default_registry = EnhancedTaskTypeRegistry()
        self.resolver.register_provider(self._default_registry, priority=100)

    def get_task_info(self, task_type: str) -> Dict[str, Any]:
        """获取完整的任务类型信息"""
        config = self.resolver.resolve_task_type(task_type)
        if not config:
            return self._get_fallback_config(task_type)

        return {
            "task_type": task_type,
            "config": config,
            "execution_mode": config.get("execution_mode"),
            "security_level": config.get("security_level"),
            "subtypes": config.get("subtypes", {}),
            "supported_actions": self._extract_all_actions(config),
            "supported_params": self._extract_all_params(config),
            "ui_types": config.get("ui_types", []),
            "data_patterns": config.get("data_patterns", []),
            "structure_patterns": config.get("structure_patterns", []),
        }

    def _extract_all_actions(self, config: Dict[str, Any]) -> List[str]:
        """提取所有支持的动作"""
        actions = set()

        # 从子类型中提取动作
        for subtype_config in config.get("subtypes", {}).values():
            actions.update(subtype_config.get("actions", []))

        return list(actions)

    def _extract_all_params(self, config: Dict[str, Any]) -> List[str]:
        """提取所有支持的参数"""
        params = set()

        # 从子类型中提取参数
        for subtype_config in config.get("subtypes", {}).values():
            params.update(subtype_config.get("params", []))

        return list(params)

    def _get_fallback_config(self, task_type: str) -> Dict[str, Any]:
        """获取回退配置"""
        return {
            "task_type": task_type,
            "config": {
                "execution_mode": ExecutionMode.DIRECT_AI_RESPONSE,
                "security_level": SecurityLevel.SAFE,
                "subtypes": {},
                "data_patterns": ["content"],
                "structure_patterns": ["simple_response"],
                "ui_types": ["card", "text"],
            },
            "execution_mode": ExecutionMode.DIRECT_AI_RESPONSE,
            "security_level": SecurityLevel.SAFE,
            "subtypes": {},
            "supported_actions": ["respond"],
            "supported_params": ["content"],
            "ui_types": ["card", "text"],
            "data_patterns": ["content"],
            "structure_patterns": ["simple_response"],
        }

    def register_provider(self, provider: TaskTypeProvider, priority: int = 0):
        """注册新的任务类型提供者"""
        self.resolver.register_provider(provider, priority)

    def register_task_type(self, task_type: str, definition: Dict[str, Any]) -> bool:
        """注册新任务类型"""
        return self._default_registry.register_task_type(task_type, definition)
