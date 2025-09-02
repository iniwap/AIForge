from pathlib import Path
from typing import Dict, Any, List, Optional
import time
import sys
import shutil
import json
from ...core.path_manager import AIForgePathManager


class FileOperationConfirmationManager:
    """文件操作确认管理器"""

    def __init__(self):
        self.confirmation_history = []

    def require_user_confirmation(self, operation_summary: Dict[str, Any]) -> bool:
        """要求用户确认操作"""
        if operation_summary["risk_level"] in ["high", "critical"]:
            # 生成确认提示
            confirmation_prompt = self._generate_confirmation_prompt(operation_summary)
            # 等待用户确认（通过UI或CLI接口）
            confirmed = self._wait_for_user_confirmation(confirmation_prompt)

            # 记录确认历史
            self.confirmation_history.append(
                {
                    "timestamp": time.time(),
                    "operation_summary": operation_summary,
                    "confirmed": confirmed,
                }
            )

            return confirmed
        return True

    def _generate_confirmation_prompt(self, operation_summary: Dict[str, Any]) -> str:
        """生成确认提示信息"""
        risk_level = operation_summary.get("risk_level", "unknown")
        destructive_operations = operation_summary.get("destructive_operations", [])
        affected_files = operation_summary.get("affected_files", [])

        prompt_parts = [f"⚠️  检测到 {risk_level.upper()} 风险的文件操作", ""]

        if destructive_operations:
            prompt_parts.extend(
                ["🔥 破坏性操作:", *[f"  - {op}" for op in destructive_operations], ""]
            )

        if affected_files:
            prompt_parts.extend(
                [
                    "📁 受影响的文件:",
                    *[f"  - {file}" for file in affected_files[:5]],  # 最多显示5个文件
                    (
                        ""
                        if len(affected_files) <= 5
                        else f"  ... 以及其他 {len(affected_files) - 5} 个文件"
                    ),
                    "",
                ]
            )

        prompt_parts.extend(
            [
                "❓ 是否继续执行此操作？",
                "   输入 'yes' 或 'y' 确认",
                "   输入 'no' 或 'n' 取消",
                "   输入 'backup' 先备份再执行",
            ]
        )

        return "\n".join(prompt_parts)

    def _wait_for_user_confirmation(self, confirmation_prompt: str) -> bool:
        """等待用户确认（支持CLI和UI接口）"""
        # 检查是否在交互式环境中
        if not sys.stdin.isatty():
            # 非交互式环境，默认拒绝高风险操作
            print("[WARNING] 非交互式环境，自动拒绝高风险文件操作")
            return False

        print(confirmation_prompt)

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                user_input = input("请输入您的选择: ").strip().lower()

                if user_input in ["yes", "y", "是", "确认"]:
                    return True
                elif user_input in ["no", "n", "否", "取消"]:
                    return False
                elif user_input == "backup":
                    # 用户要求先备份
                    print("✅ 将在执行前创建备份")
                    return True
                else:
                    remaining = max_attempts - attempt - 1
                    if remaining > 0:
                        print(f"❌ 无效输入，请重新输入 (剩余 {remaining} 次机会)")
                    else:
                        print("❌ 输入次数过多，操作已取消")
                        return False

            except (KeyboardInterrupt, EOFError):
                print("\n❌ 操作已被用户中断")
                return False

        return False

    def get_confirmation_history(self) -> List[Dict[str, Any]]:
        """获取确认历史记录"""
        return self.confirmation_history.copy()


class FileOperationBackupManager:
    """文件操作备份管理器"""

    def __init__(self):
        self.backup_root = AIForgePathManager.get_backup_dir()
        self.manifest_file = self.backup_root / "backup_manifest.json"
        self.backup_manifest = self._load_manifest()

    def _load_manifest(self) -> Dict[str, Any]:
        """加载备份清单"""
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_manifest(self):
        """保存备份清单"""
        try:
            with open(self.manifest_file, "w", encoding="utf-8") as f:
                json.dump(self.backup_manifest, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def create_operation_backup(self, affected_files: List[str]) -> str:
        """为即将操作的文件创建备份"""
        backup_id = f"backup_{int(time.time())}"
        backup_dir = self.backup_root / backup_id
        backup_dir = AIForgePathManager.ensure_directory_exists(backup_dir)

        backup_manifest = {
            "backup_id": backup_id,
            "timestamp": time.time(),
            "original_files": [],
            "backup_files": [],
        }

        for file_path in affected_files:
            if Path(file_path).exists():
                try:
                    relative_path = Path(file_path).resolve().relative_to(Path.cwd())
                except ValueError:
                    # 文件在工作目录外，使用绝对路径的安全版本
                    relative_path = Path(file_path).name
                    if not relative_path:  # 处理根目录等特殊情况
                        relative_path = f"file_{int(time.time())}"
                backup_path = backup_dir / relative_path

                AIForgePathManager.ensure_directory_exists(backup_path.parent)

                shutil.copy2(file_path, backup_path)
                backup_manifest["original_files"].append(file_path)
                backup_manifest["backup_files"].append(str(backup_path))

        # 保存备份清单到文件
        self.backup_manifest[backup_id] = backup_manifest
        self._save_manifest()
        return backup_id

    def restore_from_backup(self, backup_id: str) -> bool:
        """从备份恢复文件"""
        if backup_id not in self.backup_manifest:
            return False

        manifest = self.backup_manifest[backup_id]
        try:
            for original_file, backup_file in zip(
                manifest["original_files"], manifest["backup_files"]
            ):
                if Path(backup_file).exists():
                    shutil.copy2(backup_file, original_file)
            return True
        except Exception:
            return False


class FileOperationUndoManager:
    """文件操作撤销管理器"""

    def __init__(self, backup_manager: Optional[FileOperationBackupManager] = None):
        self.undo_registry = {}
        self.backup_manager = backup_manager or FileOperationBackupManager()

    def register_operation(
        self, operation_type: str, backup_id: str, operation_details: Dict[str, Any]
    ) -> str:
        """注册可撤销的操作"""
        undo_id = f"undo_{int(time.time())}"
        self.undo_registry[undo_id] = {
            "operation_type": operation_type,
            "backup_id": backup_id,
            "operation_details": operation_details,
            "timestamp": time.time(),
            "can_undo": True,
        }
        return undo_id

    def undo_operation(self, undo_id: str) -> bool:
        """撤销指定操作"""
        if undo_id not in self.undo_registry:
            return False

        operation = self.undo_registry[undo_id]
        if not operation["can_undo"]:
            return False

        return self._execute_undo(operation)

    def _execute_undo(self, operation: Dict[str, Any]) -> bool:
        """执行撤销逻辑"""
        operation_type = operation["operation_type"]
        backup_id = operation["backup_id"]

        # 根据操作类型执行相应的撤销逻辑
        if operation_type in ["delete", "move"]:
            # 使用共享的备份管理器实例
            return self.backup_manager.restore_from_backup(backup_id)
        elif operation_type == "copy":
            # 对于复制操作，删除目标文件
            operation_details = operation["operation_details"]
            target_path = operation_details.get("parameters", {}).get("target_path")
            if target_path and Path(target_path).exists():
                try:
                    Path(target_path).unlink()
                    return True
                except Exception:
                    return False

        return True
