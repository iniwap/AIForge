class AIForgeWebApp {
    constructor() {
        this.configManager = new ConfigManager();
        this.sessionManager = new SessionManager();
        this.streamingClient = new StreamingClient('',this.sessionManager);
        this.uiAdapter = new WebUIAdapter();
        this.currentTaskType = null;
        this.isExecuting = false;
        this.executionCompleted = false;
        this.currentResult = null; // 添加这个属性  

        this.initializeEventListeners();
        this.initializeKeyboardShortcuts(); // 添加键盘快捷键  
        this.loadSettings();

        // 设置全局引用以便在 onclick 中使用  
        window.aiforgeApp = this;
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
        
        const stopButton = document.getElementById('stopButton');  
        if (stopButton) {  
            stopButton.addEventListener('click', () => this.stopExecution());  
        }  
    }

    async stopExecution() {  
        if (this.isExecuting) {  
            try {  
                await this.streamingClient.stopExecution();  
                this.isExecuting = false;  
                console.warn('执行已停止');  
            } catch (error) {  
                console.error('停止执行失败:', error);  
            }  
        }  
    }  

    selectTaskType(taskType) {
        // 更新按钮状态（仅用于UI展示和示例指令）  
        document.querySelectorAll('.task-type-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-type="${taskType}"]`).classList.add('active');

        // 注意：这个值仅用于前端UI展示，不影响后端处理  
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

    loadUserSettings() {
        // 从 localStorage 或用户配置中加载设置  
        const settings = localStorage.getItem('aiforge-user-settings');
        if (settings) {
            try {
                return JSON.parse(settings);
            } catch (e) {
                console.warn('Failed to parse user settings:', e);
            }
        }
        return {
            progressLevel: 'detailed', // 默认值  
            language: 'zh',
            maxRounds: 5
        };
    }

    saveUserSettings(settings) {
        localStorage.setItem('aiforge-user-settings', JSON.stringify(settings));
    }

    getProgressLevel() {
        // 从用户设置中获取进度级别偏好  
        const settings = this.loadUserSettings();
        return settings.progressLevel || 'detailed'; // 默认详细模式  
    }

    getBrowserInfo() {  
        return {  
            userAgent: navigator.userAgent,  
            language: navigator.language,  
            platform: navigator.platform  
        };  
    }  
  
    getViewportInfo() {  
        return {  
            width: window.innerWidth,  
            height: window.innerHeight  
        };  
    }  

    async executeInstruction() {
        const instruction = document.getElementById('instructionInput').value.trim();
        if (!instruction) {
            alert('请输入指令');
            return;
        }
        this.executionCompleted = false;
        this.setExecutionState(true);
        this.clearResults();

        const progressContainer = document.getElementById('progressContainer');
        const resultContainer = document.getElementById('resultContainer');

        // 获取用户设置的进度级别  
        const progressLevel = this.getProgressLevel();

        // 根据进度级别决定是否显示连接状态  
        if (progressLevel !== 'none') {
            this.addProgressMessage('🔗 正在连接服务器...', 'info');
        }

        try {
            // 准备上下文数据，包含会话信息  
            const contextData = {  
                taskType: this.currentTaskType,  
                user_id: this.sessionManager.sessionId, // 使用会话ID作为用户ID  
                session_id: this.sessionManager.sessionId,  
                browser_info: this.getBrowserInfo(),  
                viewport: this.getViewportInfo(),
                progressLevel: progressLevel
            };  

            await this.streamingClient.executeInstruction(instruction, contextData, {
                onProgress: (message, type) => {
                    // 根据进度级别决定是否显示进度消息  
                    if (progressLevel === 'detailed') {
                        this.addProgressMessage(message, type);
                    } else if (progressLevel === 'minimal' &&
                        ['task_start', 'task_complete', 'error'].includes(type)) {
                        this.addProgressMessage(message, type);
                    }
                    // progressLevel === 'none' 时不显示任何进度消息  
                },
                onResult: (data) => {
                    this.displayResult(data, resultContainer);
                },
                onError: (error) => {
                    this.addProgressMessage(`❌ 错误: ${error.message}`, 'error');
                },
                onComplete: () => {
                    if (progressLevel !== 'none') {
                        if (!this.executionCompleted) {
                            this.addProgressMessage('✅ 执行完成', 'complete');
                            this.executionCompleted = true;
                        }
                    }
                    this.setExecutionState(false);
                },
                onHeartbeat: () => {
                    this.triggerBreathingEffect();
                }
            });
        } catch (error) {
            this.addProgressMessage(`💥 连接失败: ${error.message}`, 'error');
            this.setExecutionState(false);
        }
    }

    triggerBreathingEffect() {
        if (!this.isExecuting) return; // 只在执行时显示效果  

        const executeBtn = document.getElementById('executeBtn');
        const progressContainer = document.getElementById('progressContainer');

        // 添加呼吸效果  
        executeBtn.classList.add('breathing');
        progressContainer.classList.add('breathing');

        // 1秒后移除效果  
        setTimeout(() => {
            executeBtn.classList.remove('breathing');
            progressContainer.classList.remove('breathing');
        }, 1000);
    }

    stopExecution() {
        this.streamingClient.disconnect();
        this.addProgressMessage('⏹️ 正在停止执行...', 'info');
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
        if (!progressContainer) {
            console.error('Progress container not found');
            return;
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `progress-item ${type}`;
        messageDiv.innerHTML = `  
            <span class="timestamp">[${new Date().toLocaleTimeString()}]</span>  
            <span class="message">${message}</span>  
        `;

        progressContainer.appendChild(messageDiv);
        progressContainer.scrollTop = progressContainer.scrollHeight;

        // 确保容器可见  
        progressContainer.style.display = 'block';
    }

    clearResults() {
        document.getElementById('progressContainer').innerHTML = '';
        document.getElementById('resultContainer').innerHTML = '<div class="text-gray-500 text-center py-8">执行结果将在这里显示...</div>';
    }

    displayResult(data, container) {
        if (!container) {
            console.error('Result container not found');
            return;
        }

        try {
            // 验证数据结构  
            if (!data || typeof data !== 'object') {
                throw new Error('Invalid result data structure');
            }

            // 处理嵌套的结果数据  
            let resultData = data;
            if (data.result && typeof data.result === 'object') {
                resultData = data.result;
            }

            // 验证必要的字段  
            if (!resultData.display_items || !Array.isArray(resultData.display_items)) {
                throw new Error('Missing or invalid display_items');
            }

            // 确定UI类型  
            const uiType = this.determineUIType(resultData, this.currentTaskType);

            console.log('渲染信息:', {
                uiType: uiType,
                displayItemsCount: resultData.display_items.length,
                adaptationMethod: resultData.adaptation_method,
                taskType: resultData.task_type
            });

            // 渲染结果  
            this.uiAdapter.render(resultData, uiType, container);
            this.currentResult = data;

            // 显示适配统计信息  
            this.showAdaptationStats(resultData);

        } catch (error) {
            console.error('Failed to display result:', error);
            this.renderError(container, error, data);
        }
    }

    showAdaptationStats(resultData) {
        const statsContainer = document.getElementById('adaptationStats');
        if (statsContainer) {
            const stats = {
                method: resultData.adaptation_method || 'unknown',
                taskType: resultData.task_type || 'unknown',
                itemCount: resultData.display_items?.length || 0,
                hasActions: (resultData.actions?.length || 0) > 0
            };

            statsContainer.innerHTML = `  
            <div class="text-xs text-gray-500 p-2 bg-gray-50 rounded">  
                适配方法: ${stats.method} | 任务类型: ${stats.taskType} |   
                显示项: ${stats.itemCount} | 操作: ${stats.hasActions ? '有' : '无'}  
            </div>  
        `;
        }
    }

    renderError(container, error, data) {
        const errorHtml = `  
        <div class="error-container">  
            <div class="bg-red-50 border border-red-200 rounded-lg p-4">  
                <div class="flex items-center">  
                    <div class="text-red-400 text-xl mr-3">⚠️</div>  
                    <div>  
                        <h3 class="text-red-800 font-medium">结果显示错误</h3>  
                        <p class="text-red-600 text-sm mt-1">${error.message}</p>  
                    </div>  
                </div>  
                <details class="mt-3">  
                    <summary class="text-red-700 text-sm cursor-pointer">查看原始数据</summary>  
                    <pre class="text-xs text-red-600 mt-2 bg-red-100 p-2 rounded overflow-auto max-h-40">${JSON.stringify(data, null, 2)}</pre>  
                </details>  
                <div class="mt-3">  
                    <button class="text-sm px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200"   
                            onclick="window.aiforgeApp.retryRender()">  
                        🔄 重试渲染  
                    </button>  
                </div>  
            </div>  
        </div>  
    `;
        container.innerHTML = errorHtml;
    }
    determineUIType(data, frontendTaskType) {
        if (!data || !data.display_items) {
            console.error('Invalid data structure: missing display_items field', data);
            return 'web_card';
        }

        console.log('UI类型判断:', {
            hasDisplayItems: !!(data.display_items && data.display_items.length > 0),
            firstItemType: data.display_items?.[0]?.type,
            backendTaskType: data.task_type,
            frontendTaskType: frontendTaskType,
            adaptationMethod: data.adaptation_method
        });

        // 优先使用后端已经处理好的 UI 类型  
        if (data.display_items && data.display_items.length > 0) {
            const uiType = data.display_items[0].type;
            // 确保UI类型有web_前缀  
            return uiType.startsWith('web_') ? uiType : `web_${uiType}`;
        }

        // 回退逻辑使用后端的任务类型  
        const actualTaskType = data.task_type || frontendTaskType;
        if (actualTaskType === 'content_generation' || actualTaskType === 'code_generation') {
            return 'web_editor';
        }
        return 'web_card';
    }

    copyResult() {
        if (this.currentResult) {
            const result = this.currentResult.result || this.currentResult;
            const editorItem = result.display_items?.find(item => item.type === 'web_editor');

            if (editorItem && editorItem.content && editorItem.content.text) {
                const markdownContent = editorItem.content.text;
                navigator.clipboard.writeText(markdownContent).then(() => {
                    this.showToast('Markdown 内容已复制到剪贴板');
                });
            } else {
                // 简化的回退逻辑  
                const text = JSON.stringify(this.currentResult, null, 2);
                navigator.clipboard.writeText(text).then(() => {
                    this.showToast('结果已复制到剪贴板');
                });
            }
        }
    }

    downloadResult() {
        if (this.currentResult) {
            const result = this.currentResult.result || this.currentResult;
            const editorItem = result.display_items?.find(item => item.type === 'web_editor');

            if (editorItem && editorItem.content && editorItem.content.text) {
                const markdownContent = editorItem.content.text;
                const blob = new Blob([markdownContent], { type: 'text/markdown' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'generated-content.md';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                this.showToast('Markdown 文件已下载');
            }
        }
    }

    showSettings() {
        const settings = this.loadUserSettings();

        // 更新设置模态框内容，包含进度级别选择  
        document.getElementById('progressLevelSelect').value = settings.progressLevel || 'detailed';
        document.getElementById('maxRounds').value = settings.maxRounds || 5;
        document.getElementById('languageSelect').value = settings.language || 'zh';

        document.getElementById('settingsModal').classList.remove('hidden');
    }

    hideSettings() {
        document.getElementById('settingsModal').classList.add('hidden');
    }

    saveSettings() {
        const progressLevel = document.getElementById('progressLevelSelect').value;
        const maxRounds = document.getElementById('maxRounds').value;
        const language = document.getElementById('languageSelect').value;

        const settings = {
            progressLevel: progressLevel,
            maxRounds: parseInt(maxRounds),
            language: language
        };

        this.saveUserSettings(settings);
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
    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        const bgColor = type === 'error' ? 'bg-red-500' : 'bg-green-500';
        toast.className = `fixed top-4 right-4 ${bgColor} text-white px-4 py-2 rounded shadow-lg z-50 transition-opacity`;
        toast.textContent = message;
        document.body.appendChild(toast);

        // 添加淡入效果  
        setTimeout(() => toast.style.opacity = '1', 10);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    // 处理动作按钮点击  
    handleAction(actionType, actionData) {
        console.log('Handling action:', actionType, actionData);

        switch (actionType) {
            case 'save':
                this.saveContent(actionData.content);
                break;
            case 'export':
                this.exportContent(actionData.format || 'txt');
                break;
            case 'regenerate':
                this.regenerateContent();
                break;
            case 'copy':
                this.copySpecificContent(actionData.content);
                break;
            default:
                console.warn('Unknown action type:', actionType);
        }
    }

    saveContent(content) {
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `aiforge-content-${Date.now()}.txt`;
        a.click();
        URL.revokeObjectURL(url);
        this.showToast('内容已保存');
    }

    exportContent(format) {
        if (this.currentResult) {
            const result = this.currentResult.result || this.currentResult;
            const editorItem = result.display_items?.find(item => item.type === 'web_editor');

            if (editorItem && editorItem.content && editorItem.content.text) {
                const content = editorItem.content.text;
                const mimeType = format === 'md' ? 'text/markdown' : 'text/plain';
                const extension = format === 'md' ? 'md' : 'txt';

                const blob = new Blob([content], { type: mimeType });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `aiforge-export-${Date.now()}.${extension}`;
                a.click();
                URL.revokeObjectURL(url);
                this.showToast(`内容已导出为 ${extension.toUpperCase()} 文件`);
            }
        }
    }

    regenerateContent() {
        const instructionInput = document.getElementById('instructionInput');
        if (instructionInput && instructionInput.value.trim()) {
            this.executeInstruction();
            this.showToast('正在重新生成内容...');
        } else {
            this.showToast('无法重新生成：缺少原始指令', 'error');
        }
    }

    copySpecificContent(content) {
        if (content) {
            navigator.clipboard.writeText(content).then(() => {
                this.showToast('指定内容已复制到剪贴板');
            }).catch(err => {
                console.error('复制失败:', err);
                this.showToast('复制失败', 'error');
            });
        }
    }

    retryRender() {
        if (this.currentResult) {
            const resultContainer = document.getElementById('resultContainer');
            this.displayResult(this.currentResult, resultContainer);
            this.showToast('正在重试渲染...');
        }
    }
    initializeKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + Enter 执行指令  
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                this.executeInstruction();
            }

            // Ctrl/Cmd + C 复制结果（当焦点不在输入框时）  
            if ((e.ctrlKey || e.metaKey) && e.key === 'c' &&
                !['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
                if (this.currentResult) {
                    e.preventDefault();
                    this.copyResult();
                }
            }

            // Escape 停止执行  
            if (e.key === 'Escape' && this.isExecuting) {
                e.preventDefault();
                this.stopExecution();
            }
        });
    }
}

// 初始化应用  
document.addEventListener('DOMContentLoaded', () => {
    new AIForgeWebApp();
});