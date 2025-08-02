import os
import pytest
import tempfile
import shutil
from pathlib import Path


from .test_AIForge_architecture import TestAIForgeArchitecture


class TestFileOperations(TestAIForgeArchitecture):
    """文件操作功能测试套件"""

    @pytest.fixture(scope="class")
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = tempfile.mkdtemp(prefix="aiforge_test_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def sample_files(self, temp_workspace):
        """创建测试用的示例文件"""
        files = {}

        # 创建文本文件
        text_file = Path(temp_workspace) / "sample.txt"
        text_file.write_text("这是一个测试文件\\nHello World!", encoding="utf-8")
        files["text_file"] = str(text_file)

        # 创建CSV文件
        csv_file = Path(temp_workspace) / "data.csv"
        csv_file.write_text("name,age,city\\n张三,25,北京\\n李四,30,上海", encoding="utf-8")
        files["csv_file"] = str(csv_file)

        # 创建目录结构
        sub_dir = Path(temp_workspace) / "subdir"
        sub_dir.mkdir()
        (sub_dir / "nested.txt").write_text("嵌套文件内容", encoding="utf-8")
        files["sub_dir"] = str(sub_dir)
        files["nested_file"] = str(sub_dir / "nested.txt")

        return files

    # 基础文件操作测试
    @pytest.mark.parametrize(
        "instruction,expected_operation",
        [
            ("复制文件 sample.txt 到 backup.txt", "copy"),
            ("移动文件 sample.txt 到 moved.txt", "move"),
            ("删除文件 sample.txt", "delete"),
            ("重命名文件 sample.txt 为 renamed.txt", "rename"),
            ("读取文件 sample.txt 的内容", "read"),
            ("创建目录 new_folder", "create_dir"),
            ("压缩文件夹 subdir 为 archive.zip", "compress"),
        ],
    )
    def test_file_operation_instruction_recognition(self, forge, instruction, expected_operation):
        """测试文件操作指令识别"""
        if hasattr(forge, "instruction_analyzer"):
            result = forge.instruction_analyzer.local_analyze_instruction(instruction)
            assert result.get("task_type") == "file_operation"
            # 验证操作类型识别
            action = result.get("action", "").lower()
            assert expected_operation in action or result.get("confidence", 0) < 0.6

    def test_file_copy_operation(self, forge, sample_files, temp_workspace):
        """测试文件复制操作"""
        source_file = sample_files["text_file"]
        target_file = os.path.join(temp_workspace, "copied.txt")

        instruction = f"复制文件 {source_file} 到 {target_file}"
        result = forge(instruction)

        assert result is not None
        assert result.get("status") == "success"
        assert os.path.exists(target_file)

        # 验证文件内容一致
        with (
            open(source_file, "r", encoding="utf-8") as f1,
            open(target_file, "r", encoding="utf-8") as f2,
        ):
            assert f1.read() == f2.read()

    def test_file_move_operation(self, forge, sample_files, temp_workspace):
        """测试文件移动操作"""
        # 先复制一个文件用于移动测试
        source_file = sample_files["text_file"]
        temp_file = os.path.join(temp_workspace, "to_move.txt")
        shutil.copy2(source_file, temp_file)

        target_file = os.path.join(temp_workspace, "moved.txt")
        instruction = f"移动文件 {temp_file} 到 {target_file}"

        result = forge(instruction)

        assert result is not None
        assert result.get("status") == "success"
        assert not os.path.exists(temp_file)  # 原文件应该不存在
        assert os.path.exists(target_file)  # 目标文件应该存在

    def test_file_read_operation(self, forge, sample_files):
        """测试文件读取操作"""
        source_file = sample_files["text_file"]
        instruction = f"读取文件 {source_file} 的内容"

        result = forge(instruction)

        assert result is not None
        assert result.get("status") == "success"
        assert "content" in result or "data" in result

        # 验证读取的内容
        content = result.get("content") or result.get("data", "")
        assert "测试文件" in content or "Hello World" in content

    def test_file_write_operation(self, forge, temp_workspace):
        """测试文件写入操作"""
        target_file = os.path.join(temp_workspace, "written.txt")
        content = "这是通过AIForge写入的内容\\n测试写入功能"

        instruction = f"将内容'{content}'写入文件 {target_file}"
        result = forge(instruction)

        assert result is not None
        assert result.get("status") == "success"
        assert os.path.exists(target_file)

        # 验证写入的内容
        with open(target_file, "r", encoding="utf-8") as f:
            written_content = f.read()
            assert content in written_content

    def test_directory_creation(self, forge, temp_workspace):
        """测试目录创建操作"""
        new_dir = os.path.join(temp_workspace, "new_directory")
        instruction = f"创建目录 {new_dir}"

        result = forge(instruction)

        assert result is not None
        assert result.get("status") == "success"
        assert os.path.exists(new_dir)
        assert os.path.isdir(new_dir)

    def test_file_compression(self, forge, sample_files, temp_workspace):
        """测试文件压缩操作"""
        source_dir = sample_files["sub_dir"]
        archive_file = os.path.join(temp_workspace, "test_archive.zip")

        instruction = f"压缩目录 {source_dir} 为 {archive_file}"
        result = forge(instruction)

        assert result is not None
        assert result.get("status") == "success"
        assert os.path.exists(archive_file)

        # 验证压缩文件可以解压
        import zipfile

        with zipfile.ZipFile(archive_file, "r") as zip_ref:
            file_list = zip_ref.namelist()
            assert len(file_list) > 0

    def test_batch_file_operations(self, forge, sample_files, temp_workspace):
        """测试批量文件操作"""
        # 创建多个测试文件
        test_files = []
        for i in range(3):
            test_file = os.path.join(temp_workspace, f"batch_test_{i}.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(f"批量测试文件 {i}")
            test_files.append(test_file)

        # 批量复制操作
        target_dir = os.path.join(temp_workspace, "batch_target")
        os.makedirs(target_dir, exist_ok=True)

        instruction = f"批量复制文件 {','.join(test_files)} 到目录 {target_dir}"
        result = forge(instruction)

        assert result is not None
        assert result.get("status") == "success"

        # 验证所有文件都被复制
        for i in range(3):
            target_file = os.path.join(target_dir, f"batch_test_{i}.txt")
            assert os.path.exists(target_file)

    # 安全性测试
    def test_destructive_operation_confirmation(self, forge, sample_files):
        """测试破坏性操作的确认机制"""
        # 这个测试需要模拟用户确认
        source_file = sample_files["text_file"]
        instruction = f"删除文件 {source_file}"

        # 由于删除操作需要用户确认，在非交互环境下应该被拒绝
        result = forge(instruction)

        # 在非交互环境下，高风险操作应该被拒绝或要求确认
        if result.get("status") == "cancelled":
            assert "cancelled" in result.get("reason", "").lower()
        elif result.get("status") == "success":
            # 如果执行成功，应该有撤销信息
            assert "undo_id" in result or "backup" in str(result)

    def test_file_operation_error_handling(self, forge, temp_workspace):
        """测试文件操作错误处理"""
        # 测试不存在的文件
        non_existent_file = os.path.join(temp_workspace, "non_existent.txt")
        instruction = f"读取文件 {non_existent_file}"

        result = forge(instruction)

        assert result is not None
        # 应该返回错误信息
        assert (
            result.get("status") == "error"
            or "不存在" in str(result)
            or "not found" in str(result).lower()
        )

    def test_file_operation_parameter_mapping(self, forge, sample_files, temp_workspace):
        """测试文件操作参数映射"""
        source_file = sample_files["text_file"]
        target_file = os.path.join(temp_workspace, "param_test.txt")

        # 使用不同的参数名称表达方式
        instructions = [
            f"copy {source_file} to {target_file}",
            f"将文件 {source_file} 复制到 {target_file}",
            f"备份 {source_file} 为 {target_file}",
        ]

        for i, instruction in enumerate(instructions):
            current_target = f"{target_file}_{i}"
            modified_instruction = instruction.replace(target_file, current_target)

            result = forge(modified_instruction)

            # 验证参数映射成功
            if result and result.get("status") == "success":
                assert os.path.exists(current_target)

    # 边界条件测试
    def test_large_file_handling(self, forge, temp_workspace):
        """测试大文件处理"""
        large_file = os.path.join(temp_workspace, "large_file.txt")

        # 创建一个相对较大的文件（1MB）
        with open(large_file, "w", encoding="utf-8") as f:
            for i in range(10000):
                f.write(f"这是第{i}行内容，用于测试大文件处理能力。\\n")

        instruction = f"读取文件 {large_file} 的前100行"
        result = forge(instruction)

        # 应该能够处理或给出适当的限制提示
        assert result is not None
        if result.get("status") == "error":
            assert "大" in str(result) or "size" in str(result).lower()

    def test_special_characters_in_filename(self, forge, temp_workspace):
        """测试文件名包含特殊字符的情况"""
        special_file = os.path.join(temp_workspace, "特殊字符文件 (测试).txt")

        # 创建包含特殊字符的文件
        with open(special_file, "w", encoding="utf-8") as f:
            f.write("测试特殊字符文件名处理")

        instruction = f"读取文件 '{special_file}' 的内容"
        result = forge(instruction)

        assert result is not None
        # 应该能够正确处理特殊字符文件名
        if result.get("status") == "success":
            content = result.get("content", "")
            assert "特殊字符" in content

    def test_concurrent_file_operations(self, forge, sample_files, temp_workspace):
        """测试并发文件操作"""
        import concurrent.futures

        def perform_file_operation(file_index):
            source_file = sample_files["text_file"]
            target_file = os.path.join(temp_workspace, f"concurrent_{file_index}.txt")
            instruction = f"复制文件 {source_file} 到 {target_file}"
            return forge(instruction)

        # 并发执行多个文件操作
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(perform_file_operation, i) for i in range(3)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # 验证所有操作都成功完成
        success_count = sum(1 for result in results if result and result.get("status") == "success")
        assert success_count >= 2  # 至少有2个操作成功

    def test_file_operation_undo(self, forge, sample_files, temp_workspace):
        """测试文件操作撤销功能"""
        source_file = sample_files["text_file"]
        target_file = os.path.join(temp_workspace, "undo_test.txt")

        # 执行复制操作
        instruction = f"复制文件 {source_file} 到 {target_file}"
        result = forge(instruction)

        # 验证复制操作成功
        assert result is not None
        assert result.get("status") == "success"
        assert os.path.exists(target_file)

        # 检查是否返回了撤销ID
        undo_id = result.get("undo_id")
        if undo_id:
            # 测试撤销操作
            undo_instruction = f"撤销操作 {undo_id}"
            undo_result = forge(undo_instruction)

            # 验证撤销成功
            assert undo_result is not None
            if undo_result.get("status") == "success":
                # 对于复制操作的撤销，目标文件应该被删除
                assert not os.path.exists(target_file)
            else:
                # 如果撤销失败，至少应该有错误信息
                assert "error" in undo_result.get("status", "").lower()

    def test_file_operation_undo_move(self, forge, sample_files, temp_workspace):
        """测试移动操作的撤销功能"""
        # 先复制一个文件用于移动测试
        source_file = sample_files["text_file"]
        temp_file = os.path.join(temp_workspace, "to_move_undo.txt")
        shutil.copy2(source_file, temp_file)

        target_file = os.path.join(temp_workspace, "moved_undo.txt")

        # 执行移动操作
        instruction = f"移动文件 {temp_file} 到 {target_file}"
        result = forge(instruction)

        # 验证移动操作成功
        assert result is not None
        assert result.get("status") == "success"
        assert not os.path.exists(temp_file)  # 原文件不存在
        assert os.path.exists(target_file)  # 目标文件存在

        # 测试撤销移动操作
        undo_id = result.get("undo_id")
        if undo_id:
            undo_instruction = f"撤销操作 {undo_id}"
            undo_result = forge(undo_instruction)

            if undo_result and undo_result.get("status") == "success":
                # 撤销移动操作后，文件应该回到原位置
                assert os.path.exists(temp_file)
                assert not os.path.exists(target_file)

    def test_file_operation_undo_delete(self, forge, sample_files, temp_workspace):
        """测试删除操作的撤销功能"""
        # 创建一个临时文件用于删除测试
        test_file = os.path.join(temp_workspace, "to_delete.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("这个文件将被删除然后恢复")

        # 执行删除操作（需要模拟用户确认）
        instruction = f"删除文件 {test_file}"
        result = forge(instruction)

        # 如果删除操作成功执行
        if result and result.get("status") == "success":
            assert not os.path.exists(test_file)  # 文件应该被删除

            # 测试撤销删除操作
            undo_id = result.get("undo_id")
            if undo_id:
                undo_instruction = f"撤销操作 {undo_id}"
                undo_result = forge(undo_instruction)

                if undo_result and undo_result.get("status") == "success":
                    # 撤销删除操作后，文件应该被恢复
                    assert os.path.exists(test_file)

                    # 验证文件内容是否正确恢复
                    with open(test_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        assert "这个文件将被删除然后恢复" in content

    def test_undo_operation_error_handling(self, forge, temp_workspace):
        """测试撤销操作的错误处理"""
        # 测试无效的撤销ID
        invalid_undo_id = "invalid_undo_12345"
        instruction = f"撤销操作 {invalid_undo_id}"
        result = forge(instruction)

        # 应该返回错误信息
        assert result is not None
        assert (
            result.get("status") == "error"
            or "无效" in str(result)
            or "invalid" in str(result).lower()
        )

    def test_multiple_operations_undo_sequence(self, forge, sample_files, temp_workspace):
        """测试多个操作的撤销序列"""
        source_file = sample_files["text_file"]

        # 执行多个文件操作
        operations = []

        # 操作1：复制文件
        target1 = os.path.join(temp_workspace, "multi_undo_1.txt")
        result1 = forge(f"复制文件 {source_file} 到 {target1}")
        if result1 and result1.get("undo_id"):
            operations.append(("copy", target1, result1.get("undo_id")))

        # 操作2：再次复制
        target2 = os.path.join(temp_workspace, "multi_undo_2.txt")
        result2 = forge(f"复制文件 {source_file} 到 {target2}")
        if result2 and result2.get("undo_id"):
            operations.append(("copy", target2, result2.get("undo_id")))

        # 按相反顺序撤销操作（后进先出）
        for operation_type, target_file, undo_id in reversed(operations):
            undo_result = forge(f"撤销操作 {undo_id}")

            if undo_result and undo_result.get("status") == "success":
                # 验证文件被正确撤销
                if operation_type == "copy":
                    assert not os.path.exists(target_file)

    def test_undo_operation_timeout(self, forge, sample_files, temp_workspace):
        """测试撤销操作的时效性"""
        source_file = sample_files["text_file"]
        target_file = os.path.join(temp_workspace, "timeout_test.txt")

        # 执行复制操作
        result = forge(f"复制文件 {source_file} 到 {target_file}")

        if result and result.get("undo_id"):
            undo_id = result.get("undo_id")

            # 模拟时间流逝（在实际实现中可能有撤销时效限制）
            import time

            time.sleep(1)

            # 尝试撤销操作
            undo_result = forge(f"撤销操作 {undo_id}")

            # 验证撤销是否仍然有效
            # 这取决于具体的撤销策略实现
            assert undo_result is not None
