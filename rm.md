# AIForge  
  
🔥 AIForge - AI驱动的代码生成执行引擎  
  
AIForge是一个基于大语言模型的智能代码生成和执行平台，支持自然语言指令到可执行代码的自动转换。  
  
## 特性  
  
- 🚀 **零配置启动** - 仅需API Key即可快速开始  
- 🔄 **多轮对话** - 支持代码生成、执行、调试的完整循环  
- 💾 **智能缓存** - 自动缓存成功的代码模块，提高执行效率  
- 🔌 **多提供商支持** - 支持OpenRouter、DeepSeek、Gemini、Ollama等多种LLM  
- ⚡ **懒加载架构** - 按需创建客户端，优化启动性能  
- 🛠️ **可扩展执行器** - 支持自定义模块执行策略  
  
## 快速开始  
  
### 安装  
  
```bash  
pip install aiforge  
```  
  
### 基础使用  
  
#### 方式1：快速启动（推荐）  
```python  
from aiforge import AIForgeCore  
  
# 只需要API Key即可开始使用  [header-1](#header-1)
forge = AIForgeCore(api_key="your-openrouter-key")  
result = forge("获取今天的天气信息")  
print(result)  
```  
  
#### 方式2：指定提供商  
```python  
# 使用DeepSeek  [header-2](#header-2)
forge = AIForgeCore(  
    api_key="your-deepseek-key",   
    provider="deepseek",  
    max_rounds=3  
)  
result = forge("分析数据文件")  
```  
  
#### 方式3：配置文件方式  
```python  
# 使用配置文件  [header-3](#header-3)
forge = AIForgeCore(config_file="aiforge.toml")  
result = forge.run("处理任务", system_prompt="你是专业助手")  
```  
  
### 配置文件示例  
  
```toml  
workdir = "aiforge_work"  
max_tokens = 4096  
max_rounds = 5  
default_llm_provider = "openrouter"  
  
[llm.openrouter]  
type = "openai"  
model = "deepseek/deepseek-chat-v3-0324:free"  
api_key = "your-api-key"  
base_url = "https://openrouter.ai/api/v1"  
timeout = 30  
max_tokens = 8192  
  
[cache.code]  
enabled = true  
max_modules = 20  
failure_threshold = 0.8  
max_age_days = 30  
  
[optimization]  
enabled = false  
aggressive_minify = true  
max_feedback_length = 200  
```  
  
## 核心功能  
  
### 智能代码生成  
- 自然语言到Python代码的自动转换  
- 多轮对话优化和错误修复  
- 上下文感知的代码生成  
  
### 执行引擎  
- 安全的代码执行环境  
- 多种执行策略支持  
- 自动依赖管理  
  
### 缓存系统  
- 智能代码模块缓存  
- 基于成功率的缓存策略  
- 自动清理过期缓存  
  
### 多提供商支持  
- OpenRouter（推荐，支持多种模型）  
- DeepSeek  
- Gemini  
- Ollama（本地部署）  
- 更多提供商持续添加中...  
  
## API参考  
  
### AIForgeCore  
  
主要的核心类，提供代码生成和执行功能。  
  
```python  
class AIForgeCore:  
    def __init__(self,   
                 config_file: Optional[str] = None,  
                 api_key: Optional[str] = None,  
                 provider: str = "openrouter",  
                 **kwargs):  
        """  
        初始化AIForge核心  
          
        Args:  
            config_file: 配置文件路径（可选）  
            api_key: API密钥（快速启动模式）  
            provider: LLM提供商名称  
            **kwargs: 其他配置参数  
        """  
      
    def run(self, instruction: str,   
            system_prompt: Optional[str] = None,   
            provider: Optional[str] = None) -> Optional[Dict[str, Any]]:  
        """执行任务 - 统一入口"""  
      
    def __call__(self, instruction: str, **kwargs) -> Optional[Dict[str, Any]]:  
        """支持直接调用"""  
```  
  
### 执行参数说明  
  
- `instruction`: 自然语言任务描述  
- `system_prompt`: 可选的系统提示词，用于定制AI行为  
- `provider`: 可选的LLM提供商名称，用于临时切换模型  
  
## 高级功能  
  
### 自定义执行器  
```python  
from aiforge.execution.executor_interface import CachedModuleExecutor  
  
class CustomExecutor(CachedModuleExecutor):  
    def can_handle(self, module):  
        return hasattr(module, 'custom_function')  
      
    def execute(self, module, instruction, **kwargs):  
        return module.custom_function(instruction)  
  
forge.add_module_executor(CustomExecutor())  
```  
  
### 提供商切换  
```python  
# 运行时切换提供商  [header-4](#header-4)
forge.switch_provider("deepseek")  
  
# 查看可用提供商  [header-5](#header-5)
providers = forge.list_providers()  
print(providers)  
```  
  
## 配置向导  
  
首次使用时，可以运行配置向导来快速设置：  
  
```python  
from aiforge.cli.wizard import create_config_wizard  
  
forge = create_config_wizard()  
```  
  
## 开发计划  
  
- [ ] 支持更多编程语言  
- [ ] Web界面  
- [ ] 插件系统  
- [ ] 多模态支持（图像、语音）  
- [ ] 企业级功能（权限管理、审计日志）  
  
## 许可证  
  
MIT License  
  
## 贡献  
  
欢迎提交Issue和Pull Request！