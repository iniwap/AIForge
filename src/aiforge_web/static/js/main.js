class AIForgeWebApp {  
    constructor() {
        this.configManager = new ConfigManager();    
        this.streamingClient = new StreamingClient();  
        this.uiAdapter = new WebUIAdapter();  
        this.currentTaskType = null;  
        this.isExecuting = false;  
          
        this.initializeEventListeners();  
        this.loadSettings();  
    }  
  
    async initializeApp() {  
        // 检查配置状态  
        const configStatus = await this.configManager.checkConfigStatus();  
        if (!configStatus.configured) {  
            this.configManager.showConfigModal();  
        }  
    }  

    initializeEventListeners() {  
        // 任务类型按钮  
        document.querySelectorAll('.task-type-btn').forEach(btn => {  
            btn.addEventListener('click', (e) => {  
                this.selectTaskType(e.target.dataset.type);  
            });  
        });  
  
        // 示例指令  
        document.querySelectorAll('.example-instruction').forEach(item => {  
            item.addEventListener('click', (e) => {  
                document.getElementById('instructionInput').value = e.target.dataset.instruction;  
            });  
        });  
  
        // 执行按钮  
        document.getElementById('executeBtn').addEventListener('click', () => {  
            this.executeInstruction();  
        });  
  
        // 停止按钮  
        document.getElementById('stopBtn').addEventListener('click', () => {  
            this.stopExecution();  
        });  
  
        // 设置相关  
        document.getElementById('settingsBtn').addEventListener('click', () => {  
            this.showSettings();  
        });  
  
        document.getElementById('saveSettings').addEventListener('click', () => {  
            this.saveSettings();  
        });  
  
        document.getElementById('cancelSettings').addEventListener('click', () => {  
            this.hideSettings();  
        });  
  
        // 结果操作  
        document.getElementById('copyResultBtn').addEventListener('click', () => {  
            this.copyResult();  
        });  
  
        document.getElementById('downloadResultBtn').addEventListener('click', () => {  
            this.downloadResult();  
        });  
    }  
  
    selectTaskType(taskType) {  
        // 更新按钮状态  
        document.querySelectorAll('.task-type-btn').forEach(btn => {  
            btn.classList.remove('active');  
        });  
        document.querySelector(`[data-type="${taskType}"]`).classList.add('active');  
          
        this.currentTaskType = taskType;  
          
        // 更新示例指令  
        this.updateExampleInstructions(taskType);  
    }  
  
    updateExampleInstructions(taskType) {  
        const examples = {  
            'data_fetch': [  
                '获取最新的股票价格信息',  
                '搜索关于气候变化的最新研究',  
                '查询今天的天气预报'  
            ],  
            'data_analysis': [  
                '分析销售数据的趋势',  
                '对用户反馈进行情感分析',  
                '计算数据集的统计指标'  
            ],  
            'content_generation': [  
                '写一篇关于AI发展的文章',  
                '生成产品介绍文案',  
                '创建会议纪要模板'  
            ],  
            'code_generation': [  
                '编写一个排序算法',  
                '创建数据库查询语句',  
                '生成API接口代码'  
            ],  
            'search': [  
                '搜索Python编程教程',  
                '查找机器学习相关论文',  
                '搜索最佳实践案例'  
            ],  
            'direct_response': [  
                '解释什么是深度学习',  
                '比较不同编程语言的特点',  
                '介绍项目管理方法'  
            ]  
        };  
  
        const exampleContainer = document.querySelector('.example-instruction').parentElement;  
        const taskExamples = examples[taskType] || examples['direct_response'];  
          
        exampleContainer.innerHTML = taskExamples.map(example =>   
            `<div class="example-instruction cursor-pointer hover:text-blue-600" data-instruction="${example}">💡 ${example}</div>`  
        ).join('');  
  
        // 重新绑定事件  
        exampleContainer.querySelectorAll('.example-instruction').forEach(item => {  
            item.addEventListener('click', (e) => {  
                document.getElementById('instructionInput').value = e.target.dataset.instruction;  
            });  
        });  
    }  
  
    async executeInstruction() {  
        const instruction = document.getElementById('instructionInput').value.trim();  
        if (!instruction) {  
            alert('请输入指令');  
            return;  
        }  
  
        this.setExecutionState(true);  
        this.clearResults();  
  
        const progressContainer = document.getElementById('progressContainer');  
        const resultContainer = document.getElementById('resultContainer');  
  
        try {  
            await this.streamingClient.executeInstruction(instruction, {  
                taskType: this.currentTaskType  
            }, {  
                onProgress: (message, type) => {  
                    this.addProgressMessage(message, type);  
                },  
                onResult: (data) => {  
                    this.displayResult(data, resultContainer);  
                    this.enableResultActions();  
                },  
                onError: (error) => {  
                    this.addProgressMessage(`错误: ${error.message}`, 'error');  
                },  
                onComplete: () => {  
                    this.addProgressMessage('执行完成', 'complete');  
                    this.setExecutionState(false);  
                }  
            });  
        } catch (error) {  
            this.addProgressMessage(`执行失败: ${error.message}`, 'error');  
            this.setExecutionState(false);  
        }  
    }  
  
    stopExecution() {  
        this.streamingClient.disconnect();  
        this.addProgressMessage('执行已停止', 'error');  
        this.setExecutionState(false);  
    }  
  
    setExecutionState(isExecuting) {  
        this.isExecuting = isExecuting;  
        const executeBtn = document.getElementById('executeBtn');  
        const stopBtn = document.getElementById('stopBtn');  
        const executeText = document.getElementById('executeText');  
  
        if (isExecuting) {  
            executeBtn.disabled = true;  
            stopBtn.disabled = false;  
            executeText.textContent = '⏳ 执行中...';  
        } else {  
            executeBtn.disabled = false;  
            stopBtn.disabled = true;  
            executeText.textContent = '🚀 执行指令';  
        }  
    }  
  
    addProgressMessage(message, type = 'info') {  
        const progressContainer = document.getElementById('progressContainer');  
        const messageDiv = document.createElement('div');  
        messageDiv.className = `progress-item ${type}`;  
        messageDiv.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;  
          
        progressContainer.appendChild(messageDiv);  
        progressContainer.scrollTop = progressContainer.scrollHeight;  
    }  
  
    clearResults() {  
        document.getElementById('progressContainer').innerHTML = '';  
        document.getElementById('resultContainer').innerHTML = '<div class="text-gray-500 text-center py-8">执行结果将在这里显示...</div>';  
        this.disableResultActions();  
    }  
  
    displayResult(data, container) {  
        // 基于现有的 RuleBasedAdapter 逻辑确定 UI 类型  
        const uiType = this.determineUIType(data, this.currentTaskType);  
        this.uiAdapter.render(data, uiType, container);  
        this.currentResult = data;  
    }
    determineUIType(data, taskType) {  
        // 基于 AIForge 的 UITypeRecommender 逻辑  
        if (taskType === 'data_analysis' && data.metrics) {  
            return 'web_dashboard';  
        } else if (data.rows && Array.isArray(data.rows)) {  
            return 'web_table';  
        } else if (data.steps && Array.isArray(data.steps)) {  
            return 'web_timeline';  
        } else if (data.percentage !== undefined) {  
            return 'web_progress';  
        } else if (taskType === 'content_generation' && data.content) {  
            return 'web_editor';  
        } else {  
            return 'web_card'; // 默认卡片显示  
        }  
    }  
  
    enableResultActions() {  
        document.getElementById('copyResultBtn').disabled = false;  
        document.getElementById('downloadResultBtn').disabled = false;  
    }  
  
    disableResultActions() {  
        document.getElementById('copyResultBtn').disabled = true;  
        document.getElementById('downloadResultBtn').disabled = true;  
    }  
  
    copyResult() {  
        if (this.currentResult) {  
            const text = JSON.stringify(this.currentResult, null, 2);  
            navigator.clipboard.writeText(text).then(() => {  
                this.showToast('结果已复制到剪贴板');  
            });  
        }  
    }  
  
    downloadResult() {  
        if (this.currentResult) {  
            const text = JSON.stringify(this.currentResult, null, 2);  
            const blob = new Blob([text], { type: 'application/json' });  
            const url = URL.createObjectURL(blob);  
            const a = document.createElement('a');  
            a.href = url;  
            a.download = `aiforge-result-${Date.now()}.json`;  
            a.click();  
            URL.revokeObjectURL(url);  
        }  
    }  
  
    showSettings() {  
        document.getElementById('settingsModal').classList.remove('hidden');  
    }  
  
    hideSettings() {  
        document.getElementById('settingsModal').classList.add('hidden');  
    }  
  
    saveSettings() {  
        const maxRounds = document.getElementById('maxRounds').value;  
        const language = document.getElementById('languageSelect').value;  
          
        localStorage.setItem('aiforge-settings', JSON.stringify({  
            maxRounds: parseInt(maxRounds),  
            language: language  
        }));  
          
        this.hideSettings();  
        this.showToast('设置已保存');  
    }  
  
    loadSettings() {  
        const settings = localStorage.getItem('aiforge-settings');  
        if (settings) {  
            const parsed = JSON.parse(settings);  
            document.getElementById('maxRounds').value = parsed.maxRounds || 5;  
            document.getElementById('languageSelect').value = parsed.language || 'zh';  
        }  
    }  
  
    showToast(message) {  
        // 简单的提示消息实现  
        const toast = document.createElement('div');  
        toast.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded shadow-lg z-50';  
        toast.textContent = message;  
        document.body.appendChild(toast);  
          
        setTimeout(() => {  
            toast.remove();  
        }, 3000);  
    }  
}  
  
// 初始化应用  
document.addEventListener('DOMContentLoaded', () => {  
    new AIForgeWebApp();  
});