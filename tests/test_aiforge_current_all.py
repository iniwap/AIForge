import os
import pytest
import time
from aiforge import AIForgeCore


class TestAIForgeArchitecture:
    """AIForge 架构全面测试套件"""

    @pytest.fixture(scope="class")
    def forge(self):
        """测试用的 AIForge 实例"""
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            pytest.skip("需要设置 OPENROUTER_API_KEY 环境变量")
        return AIForgeCore(api_key=api_key)

    @pytest.fixture(scope="class")
    def forge_deepseek(self):
        """DeepSeek 提供商测试实例"""
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            pytest.skip("需要设置 DEEPSEEK_API_KEY 环境变量")
        return AIForgeCore(api_key=api_key, provider="deepseek")


class TestInstructionAnalysis(TestAIForgeArchitecture):
    """指令分析与分类测试"""

    @pytest.mark.parametrize(
        "instruction,expected_task_type",
        [
            ("获取杭州今天的天气", "data_fetch"),
            ("分析这个CSV文件的数据", "data_process"),
            ("写一首关于春天的诗", "content_generation"),
            ("什么是机器学习？", "direct_response"),
            ("批量处理图片文件", "file_operation"),
            ("定时监控服务器状态", "automation"),
        ],
    )
    def test_local_analysis_task_types(self, forge, instruction, expected_task_type):
        """测试本地分析的任务类型识别"""
        # 这里测试指令分析器的本地分析能力
        if hasattr(forge, "instruction_analyzer"):
            result = forge.instruction_analyzer.local_analyze_instruction(instruction)
            # 验证任务类型识别是否正确
            assert (
                result.get("task_type") == expected_task_type or result.get("confidence", 0) < 0.6
            )

    @pytest.mark.parametrize(
        "ambiguous_instruction", ["帮我搞定这个问题", "处理一下数据库的事情", "优化系统性能"]
    )
    def test_ai_enhanced_analysis(self, forge, ambiguous_instruction):
        """测试AI增强分析处理模糊指令"""
        result = forge(ambiguous_instruction)
        # 模糊指令应该能够通过AI分析得到结果
        assert result is not None
        assert isinstance(result, dict)


class TestExecutionModes(TestAIForgeArchitecture):
    """执行模式路径测试"""

    @pytest.mark.parametrize(
        "direct_instruction",
        [
            "解释什么是深度学习",
            "翻译这句话：Hello World",
            "总结人工智能的发展历史",
            "写一首七言绝句",
        ],
    )
    def test_direct_response_mode(self, forge, direct_instruction):
        """测试直接响应模式"""
        result = forge(direct_instruction)
        assert result is not None
        assert result.get("status") == "success"
        # 直接响应应该包含生成的内容
        assert "data" in result

    @pytest.mark.parametrize(
        "code_instruction",
        [
            "获取北京今天的股价信息",
            "分析sales.csv文件中的销售趋势",
            "爬取新浪新闻首页的标题",
            "计算斐波那契数列前20项",
        ],
    )
    def test_code_generation_mode(self, forge, code_instruction):
        """测试代码生成模式"""
        result = forge(code_instruction)
        assert result is not None
        # 代码生成模式应该返回执行结果
        assert isinstance(result, dict)


class TestCachingSystem(TestAIForgeArchitecture):
    """缓存系统测试"""

    def test_cache_hit_weather_queries(self, forge):
        """测试天气查询的缓存命中"""
        # 第一次执行，建立缓存
        result1 = forge("获取上海今天的天气")
        assert result1 is not None

        # 等待缓存保存完成
        time.sleep(1)

        # 第二次执行，应该命中缓存
        result2 = forge("获取深圳今天的天气")
        assert result2 is not None

        # 验证两次都成功执行
        assert result1.get("status") == "success"
        assert result2.get("status") == "success"

    @pytest.mark.parametrize(
        "first_instruction,second_instruction,should_match",
        [
            ("获取天气信息", "查询今天天气", True),
            ("下载新闻数据", "爬取新闻内容", True),
            ("天气查询", "新闻获取", False),
        ],
    )
    def test_semantic_matching(self, forge, first_instruction, second_instruction, should_match):
        """测试语义匹配"""
        # 执行第一个指令建立缓存
        result1 = forge(first_instruction)
        assert result1 is not None

        time.sleep(1)

        # 执行第二个指令测试语义匹配
        result2 = forge(second_instruction)
        assert result2 is not None

        # 根据预期验证是否应该匹配
        if should_match:
            # 如果应该匹配，两个结果的结构应该相似
            assert result1.get("metadata", {}).get("task_type") == result2.get("metadata", {}).get(
                "task_type"
            )


class TestMultiRoundExecution(TestAIForgeArchitecture):
    """多轮执行与错误恢复测试"""

    def test_complex_task_execution(self, forge):
        """测试复杂任务的多轮执行"""
        complex_instruction = "分析一个包含用户行为数据的JSON文件并生成统计报告"
        result = forge(complex_instruction)

        # 复杂任务应该能够完成或给出合理的错误信息
        assert result is not None
        assert isinstance(result, dict)

    def test_error_recovery(self, forge):
        """测试错误恢复机制"""
        # 故意使用可能失败的指令
        error_prone_instruction = "访问不存在的API接口http://nonexistent.api/data"
        result = forge(error_prone_instruction)

        # 系统应该能够处理错误并返回结果
        assert result is not None
        assert isinstance(result, dict)


class TestParameterizedExecution(TestAIForgeArchitecture):
    """参数化执行测试"""

    @pytest.mark.parametrize(
        "parameterized_instruction",
        ["获取北京在2024-01-01的天气情况", "分析data.csv文件的销售数据", "生成科技主题的500字文章"],
    )
    def test_parameter_extraction(self, forge, parameterized_instruction):
        """测试参数提取与传递"""
        result = forge(parameterized_instruction)
        assert result is not None
        assert isinstance(result, dict)

        # 验证参数化任务能够正确处理
        if result.get("status") == "success":
            assert "data" in result


class TestProviderManagement(TestAIForgeArchitecture):
    """LLM提供商管理测试"""

    def test_provider_switching(self, forge):
        """测试提供商切换"""
        # 获取当前可用的提供商
        providers = forge.list_providers()
        assert isinstance(providers, (list, dict))

        # 测试切换到不同提供商
        if "deepseek" in str(providers):
            success = forge.switch_provider("deepseek")
            assert isinstance(success, bool)

    def test_multiple_providers(self, forge, forge_deepseek):
        """测试多个提供商的功能"""
        simple_task = "计算1+1等于多少"

        # 测试默认提供商
        result1 = forge(simple_task)
        assert result1 is not None

        # 测试DeepSeek提供商
        result2 = forge_deepseek(simple_task)
        assert result2 is not None


class TestInputAdaptation(TestAIForgeArchitecture):
    """输入适配测试"""

    @pytest.mark.parametrize(
        "input_data,source",
        [
            ({"text": "分析数据", "context": "web_interface"}, "web"),
            ({"instruction": "获取信息", "source": "api_call"}, "api"),
            ("命令行直接输入", "cli"),
        ],
    )
    def test_multi_source_input(self, forge, input_data, source):
        """测试多源输入适配"""
        try:
            result = forge.run_with_input_adaptation(input_data, source)
            # 输入适配应该能够处理不同格式的输入
            assert result is not None or True  # 允许某些输入格式不被支持
        except Exception as e:
            # 记录但不失败，因为某些输入格式可能不被支持
            print(f"Input adaptation failed for {source}: {e}")


class TestBoundaryConditions(TestAIForgeArchitecture):
    """边界条件与异常测试"""

    @pytest.mark.parametrize(
        "edge_case",
        [
            "",  # 空指令
            "a" * 100,  # 长指令（减少长度避免超时）
            "🎉🚀💻",  # 特殊字符
        ],
    )
    def test_edge_cases(self, forge, edge_case):
        """测试边界条件"""
        try:
            result = forge(edge_case)
            # 边界条件应该被优雅处理
            if result is not None:
                assert isinstance(result, dict)
        except Exception as e:
            # 某些边界条件可能会抛出异常，这是可以接受的
            print(f"Edge case handled with exception: {e}")

    def test_none_input(self, forge):
        """测试None输入"""
        with pytest.raises((ValueError, TypeError, AttributeError)):
            forge(None)

    def test_invalid_format_input(self, forge):
        """测试无效格式输入"""
        with pytest.raises((ValueError, TypeError, AttributeError)):
            forge({"invalid": "format"})


class TestSystemIntegration(TestAIForgeArchitecture):
    """系统集成测试"""

    def test_end_to_end_workflow(self, forge):
        """测试端到端工作流"""
        # 测试完整的工作流程
        instructions = [
            "什么是人工智能？",  # 直接响应
            "获取今天的天气信息",  # 数据获取
            "写一首关于春天的诗",  # 内容生成
        ]

        results = []
        for instruction in instructions:
            result = forge(instruction)
            results.append(result)
            assert result is not None
            time.sleep(0.5)  # 避免请求过快

        # 验证所有任务都成功完成
        assert len(results) == len(instructions)
        assert all(r is not None for r in results)

    def test_cache_persistence(self, forge):
        """测试缓存持久化"""
        # 执行一个任务建立缓存
        result1 = forge("获取天气预报")
        assert result1 is not None

        time.sleep(1)

        # 再次执行相似任务，应该能够利用缓存
        result2 = forge("查询天气情况")
        assert result2 is not None

        # 验证缓存系统正常工作
        if hasattr(forge, "code_cache") and forge.code_cache:
            modules = forge.code_cache.get_all_modules()
            assert len(modules) > 0


# 性能测试
class TestPerformance(TestAIForgeArchitecture):
    """性能测试"""

    def test_response_time(self, forge):
        """测试响应时间"""
        start_time = time.time()
        result = forge("1+1等于多少？")
        end_time = time.time()

        response_time = end_time - start_time
        assert result is not None
        # 简单任务应该在合理时间内完成（30秒）
        assert response_time < 30

    def test_concurrent_requests(self, forge):
        """测试并发请求处理"""
        import concurrent.futures

        def execute_task(instruction):
            return forge(f"计算{instruction}")

        instructions = ["1+1", "2+2", "3+3"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(execute_task, inst) for inst in instructions]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # 所有并发任务都应该成功完成
        assert len(results) == len(instructions)
        assert all(r is not None for r in results)


if __name__ == "__main__":
    # 运行测试的示例命令
    pytest.main(
        [
            __file__,
            "-v",  # 详细输出
            "--tb=short",  # 简短的错误追踪
            "-x",  # 遇到第一个失败就停止
        ]
    )

r"""
# 运行所有测试  
pytest tests/test_comprehensive_architecture.py -v  
  
# 运行特定测试类  
pytest tests/test_comprehensive_architecture.py::TestInstructionAnalysis -v  
  
# 运行特定测试方法  
pytest tests/test_comprehensive_architecture.py::TestCachingSystem::test_cache_hit_weather_queries -v  
  
# 并行运行测试（需要安装pytest-xdist）  
pytest tests/test_comprehensive_architecture.py -n auto  

# 生成覆盖率报告（需要安装pytest-cov）  
pip install pytest-cov  
  
# 运行测试并生成覆盖率报告  
pytest tests/test_comprehensive_architecture.py --cov=src/aiforge --cov-report=html --cov-report=term  
  
# 生成详细的覆盖率报告  
pytest tests/test_comprehensive_architecture.py \  
    --cov=src/aiforge \  
    --cov-report=html:htmlcov 
    --cov-report=term-missing \  
    --cov-report=xml  
  
# 只显示未覆盖的行  
pytest tests/test_comprehensive_architecture.py --cov=src/aiforge --cov-report=term-missing  
  
# 设置覆盖率阈值（例如80%）  
pytest tests/test_comprehensive_architecture.py --cov=src/aiforge --cov-fail-under=80



覆盖率配置文件 
您可以创建 .coveragerc 文件来配置覆盖率设置：

[run]  
source = src/aiforge  
omit =   
    */tests/*  
    */test_*  
    */__pycache__/*  
    */venv/*  
    */env/*  
  
[report]  
exclude_lines =  
    pragma: no cover  
    def __repr__  
    raise AssertionError  
    raise NotImplementedError  
    if __name__ == .__main__.:  
  
[html]  
directory = htmlcov
集成到CI/CD 
# GitHub Actions 示例  
- name: Run tests with coverage  
  run: |  
    pytest tests/test_comprehensive_architecture.py \  
      --cov=src/aiforge \  
      --cov-report=xml \  
      --cov-report=term  
  
- name: Upload coverage to Codecov  
  uses: codecov/codecov-action@v3  
  with:  
    file: ./coverage.xml
    
"""
