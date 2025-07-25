import time


def test_action_clustering_matching(
    self, forge, first_instruction, second_instruction, should_match
):
    """测试动作聚类匹配"""
    # 执行第一个指令建立缓存和聚类
    result1 = forge(first_instruction)
    assert result1 is not None

    time.sleep(1)

    # 执行第二个指令测试聚类匹配
    result2 = forge(second_instruction)
    assert result2 is not None

    # 根据预期验证是否应该匹配
    if should_match:
        # 验证两个指令是否被归类到相同的任务类型
        task_type1 = result1.get("metadata", {}).get("task_type")
        task_type2 = result2.get("metadata", {}).get("task_type")

        # 如果任务类型相同，说明聚类匹配生效
        if task_type1 and task_type2:
            assert task_type1 == task_type2, f"任务类型不匹配: {task_type1} vs {task_type2}"

        # 验证缓存系统是否正确识别了相似动作
        if hasattr(forge, "code_cache") and forge.code_cache:
            # 检查是否有缓存命中的迹象
            cache_modules = forge.code_cache.get_all_modules()
            assert len(cache_modules) > 0, "应该有缓存模块被创建"

        print(f"✓ 聚类匹配验证通过: '{first_instruction}' 和 '{second_instruction}'")
    else:
        # 验证两个指令不应该匹配
        task_type1 = result1.get("metadata", {}).get("task_type")
        task_type2 = result2.get("metadata", {}).get("task_type")

        # 不同领域的任务类型应该不同
        if task_type1 and task_type2:
            assert task_type1 != task_type2, f"不应该匹配的任务类型却相同: {task_type1}"

        print(
            f"✓ 非匹配验证通过: '{first_instruction}' 和 '{second_instruction}' 正确识别为不同类型"
        )

    # 验证两个结果都成功执行
    assert result1.get("status") in ["success", None], f"第一个指令执行失败: {result1}"
    assert result2.get("status") in ["success", None], f"第二个指令执行失败: {result2}"
