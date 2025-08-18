class AIForgeGUIApp {  
    constructor() {  
        this.isLocal = false;  
        this.streamingClient = null;  
        this.configManager = new ConfigManager();  
        this.uiAdapter = new WebUIAdapter();  
        this.currentTaskType = 'auto';  
        this.isExecuting = false;  
        this.executionCompleted = false;  
        this.currentResult = null;  
          
        this.init();  
          
        // 设置全局引用以便在 onclick 中使用  
        window.aiforgeApp = this;  
    }  
      
    async init() {  
        await this.checkConnectionMode();  
        this.initializeUI();  
        this.initializeStreamingClient();  
        this.loadSettings();  
    }  
      
    async checkConnectionMode() {  
        const statusIndicator = document.getElementById('statusIndicator');  
        const statusText = document.getElementById('statusText');  
        
        statusIndicator.className = 'status-indicator connecting';  
        statusText.textContent = '连接中...';  
        
        try {  
            // 等待PyWebView就绪  
            await this.waitForPyWebView();  
            
            if (typeof pywebview !== 'undefined' && typeof pywebview.api !== 'undefined') {  
                const info = await pywebview.api.get_connection_info();  
                const connectionInfo = JSON.parse(info);  
                this.isLocal = connectionInfo.mode === 'local';  
                this.updateConnectionStatus(connectionInfo);  
            } else {  
                this.isLocal = false;  
                this.updateConnectionStatus({mode: 'remote'});  
            }  
        } catch (error) {  
            console.error('检查连接模式失败:', error);  
            this.isLocal = false;  
            statusIndicator.className = 'status-indicator error';  
            statusText.textContent = '连接失败';  
        }  
    }  
    
    waitForPyWebView(timeout = 5000) {  
        return new Promise((resolve, reject) => {  
            const startTime = Date.now();  
            
            const checkPyWebView = () => {  
                if (typeof pywebview !== 'undefined' && typeof pywebview.api !== 'undefined') {  
                    resolve();  
                } else if (Date.now() - startTime > timeout) {  
                    reject(new Error('PyWebView initialization timeout'));  
                } else {  
                    setTimeout(checkPyWebView, 100);  
                }  
            };  
            
            checkPyWebView();  
        });  
    }
    updateConnectionStatus(info) {  
        const statusIndicator = document.getElementById('statusIndicator');  
        const statusText = document.getElementById('statusText');  
        
        if (info.mode === 'local') {  
            statusIndicator.className = 'status-indicator local';  
            statusText.textContent = '本地模式';  
        } else {  
            statusIndicator.className = 'status-indicator remote';  
            statusText.textContent = '远程模式';  
        }  
    }
      
    initializeUI() {  
        document.getElementById('executeBtn').addEventListener('click', () => {  
            this.executeInstruction();  
        });  
          
        document.getElementById('taskType').addEventListener('change', (e) => {  
            this.currentTaskType = e.target.value;  
        });  
          
        document.getElementById('settingsBtn').addEventListener('click', () => {  
            this.showSettings();  
        });  
          
        this.initializeSettingsModal();  
        this.initializeKeyboardShortcuts();  
    }  
      
    initializeKeyboardShortcuts() {  
        document.addEventListener('keydown', (e) => {  
            // Ctrl/Cmd + Enter 执行指令  
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {  
                e.preventDefault();  
                this.executeInstruction();  
            }  
              
            // Escape 停止执行  
            if (e.key === 'Escape' && this.isExecuting) {  
                e.preventDefault();  
                this.stopExecution();  
            }  
        });  
    }  
      
    initializeStreamingClient() {  
        this.streamingClient = new StreamingClient('/api');  
    }  
      
    async executeInstruction() {  
        const instructionInput = document.getElementById('instructionInput');  
        const instruction = instructionInput.value.trim();  
        
        if (!instruction) {  
            alert('请输入指令');  
            return;  
        }  
        
        if (this.isExecuting) {  
            return;  
        }  
    
        this.setExecuting(true);  
        this.executionCompleted = false;  
        
        try {  
            if (this.isLocal && typeof pywebview !== 'undefined') {  
                // 本地模式：使用专门的本地执行方法  
                await this.executeLocalInstruction(instruction);  
            } else {  
                // 远程模式：使用远程执行方法  
                await this.executeRemoteInstruction(instruction);  
            }  
        } catch (error) {  
            console.error('执行错误:', error);  
            this.addProgressMessage(`❌ 执行失败: ${error.message}`, 'error');  
        } finally {  
            this.setExecuting(false);  
        }  
    }
        
    setExecuting(isExecuting) {  
        this.isExecuting = isExecuting;  
        const executeBtn = document.getElementById('executeBtn');  
        const instructionInput = document.getElementById('instructionInput');  
        
        if (executeBtn) {  
            executeBtn.disabled = isExecuting;  
            executeBtn.textContent = isExecuting ? '执行中...' : '执行指令';  
        }  
        
        if (instructionInput) {  
            instructionInput.disabled = isExecuting;  
        }  
    }
        
    displayError(error) {  
        const resultContainer = document.getElementById('resultContainer');  
        resultContainer.innerHTML = `  
            <div class="error-container bg-red-50 border border-red-200 rounded-lg p-4">  
                <div class="flex items-center">  
                    <div class="text-red-400 text-xl mr-3">⚠️</div>  
                    <div>  
                        <h3 class="text-red-800 font-medium">执行错误</h3>  
                        <p class="text-red-600 text-sm mt-1">${error.message}</p>  
                    </div>  
                </div>  
                <div class="mt-3">  
                    <button class="text-sm px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200"  
                            onclick="window.aiforgeApp.retryExecution()">  
                        🔄 重试执行  
                    </button>  
                </div>  
            </div>  
        `;  
    }
      
    async executeLocalInstruction(instruction) {  
        try {  
            this.addProgressMessage('🚀 开始本地执行...', 'info');  
            
            // 验证WebView API可用性  
            if (typeof pywebview === 'undefined') {  
                throw new Error('pywebview对象不可用');  
            }  
            
            if (typeof pywebview.api === 'undefined') {  
                throw new Error('pywebview.api对象不可用');  
            }  
            
            if (typeof pywebview.api.execute_instruction !== 'function') {  
                throw new Error('execute_instruction方法不可用');  
            }  
            
            console.log('开始调用WebView API执行指令:', instruction);  
            const result = await pywebview.api.execute_instruction(instruction, '{}');  
            console.log('WebView API返回结果:', result);  
            
            const resultData = JSON.parse(result);  
            
            if (resultData.success) {  
                const resultContainer = document.getElementById('resultContent');  
                this.displayResult(resultData.data, resultContainer);  
                this.addProgressMessage('✅ 执行完成', 'complete');  
            } else {  
                this.addProgressMessage(`❌ 错误: ${resultData.error}`, 'error');  
            }  
        } catch (error) {  
            console.error('本地执行错误详情:', error);  
            this.addProgressMessage(`❌ 本地执行错误: ${error.message}`, 'error');  
        } finally {  
            this.setExecuting(false);  
        }  
    }
        
    async executeRemoteInstruction(instruction) {  
        await this.streamingClient.executeInstruction(instruction, {  
            taskType: this.currentTaskType,  
            sessionId: Date.now().toString()  
        }, {  
            onProgress: (message, type) => {  
                this.addProgressMessage(message, type);  
            },  
            onResult: (data) => {  
                this.displayResult(data, document.getElementById('resultContainer'));  
            },  
            onError: (error) => {  
                this.addProgressMessage(`❌ 错误: ${error.message}`, 'error');  
            },  
            onComplete: () => {  
                if (!this.executionCompleted) {  
                    this.addProgressMessage('✅ 执行完成', 'complete');  
                    this.executionCompleted = true;  
                }  
                this.setExecution(false);  
            }  
        });  
    }  
      
    stopExecution() {  
        this.streamingClient.disconnect();  
        this.addProgressMessage('⏹️ 正在停止执行...', 'info');  
        this.setExecution(false);  
    }  
      
    setExecution(isExecuting) {  
        this.isExecuting = isExecuting;  
        const executeBtn = document.getElementById('executeBtn');  
        const instructionInput = document.getElementById('instructionInput');  
          
        executeBtn.disabled = isExecuting;  
        executeBtn.textContent = isExecuting ? '执行中...' : '执行';  
        instructionInput.disabled = isExecuting;  
    }  
      
    addProgressMessage(message, type = 'info') {  
        const progressMessages = document.getElementById('progressMessages');  
        const messageElement = document.createElement('div');  
        messageElement.className = `progress-message ${type}`;  
        messageElement.textContent = `${new Date().toLocaleTimeString()} - ${message}`;  
        progressMessages.appendChild(messageElement);  
        progressMessages.scrollTop = progressMessages.scrollHeight;  
    }  
      
    clearResults() {  
        document.getElementById('progressMessages').innerHTML = '';  
        document.getElementById('resultContent').innerHTML = '';  
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
              
            // 渲染结果  
            this.uiAdapter.render(resultData, uiType, container);  
            this.currentResult = data;  
              
        } catch (error) {  
            console.error('Failed to display result:', error);  
            this.renderError(container, error, data);  
        }  
    }  
      
    determineUIType(data, frontendTaskType) {  
        if (!data || !data.display_items) {  
            console.error('Invalid data structure: missing display_items field', data);  
            return 'web_card';  
        }  
          
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
      
    initializeSettingsModal() {  
        const modal = document.getElementById('settingsModal');  
        const closeBtn = modal.querySelector('.close');  
        const saveBtn = document.getElementById('saveSettings');  
          
        closeBtn.addEventListener('click', () => {  
            modal.style.display = 'none';  
        });  
          
        saveBtn.addEventListener('click', () => {  
            this.saveSettings();  
            modal.style.display = 'none';  
        });  
          
        window.addEventListener('click', (e) => {  
            if (e.target === modal) {  
                modal.style.display = 'none';  
            }  
        });  
    }  
      
    showSettings() {  
        const modal = document.getElementById('settingsModal');  
        modal.style.display = 'block';  
          
        const settings = this.configManager.getSettings();  
        document.getElementById('themeSelect').value = settings.theme || 'dark';  
        document.getElementById('progressLevel').value = settings.progressLevel || 'detailed';  
        document.getElementById('remoteUrl').value = settings.remoteUrl || '';  
    }  
      
    async saveSettings() {  
        const settings = {  
            theme: document.getElementById('themeSelect').value,  
            progressLevel: document.getElementById('progressLevel').value,  
            remoteUrl: document.getElementById('remoteUrl').value  
        };  
          
        this.configManager.saveSettings(settings);  
          
        if (this.isLocal && typeof pywebview !== 'undefined') {  
            try {  
                await pywebview.api.save_settings(JSON.stringify(settings));  
            } catch (error) {  
                console.error('保存设置到 Python 端失败:', error);  
            }  
        }  
          
        this.applyTheme(settings.theme);  
        this.showToast('设置已保存');  
    }  
      
    loadSettings() {  
        const settings = this.configManager.getSettings();  
        this.applyTheme(settings.theme || 'dark');  
    }  
      
    applyTheme(theme) {  
        document.body.className = theme;  
    }  
      
    showToast(message, type = 'success') {  
        const toast = document.createElement('div');  
        const bgColor = type === 'error' ? 'bg-red-500' : 'bg-green-500';  
        toast.className = `fixed top-4 right-4 ${bgColor} text-white px-4 py-2 rounded shadow-lg z-50 transition-opacity`;  
        toast.textContent = message;  
        document.body.appendChild(toast);  
          
        setTimeout(() => toast.style.opacity = '1', 10);  
          
        setTimeout(() => {  
            toast.style.opacity = '0';  
            setTimeout(() => toast.remove(), 300);  
        }, 3000);  
    }  
      
    // 动作处理方法  
    handleAction(actionType, actionData) {  
        console.log('Handling action:', actionType, actionData);  
          
        switch (actionType) {  
            case 'copy':  
                this.copyResult();  
                break;  
            case 'download':  
                this.downloadResult();  
                break;  
            case 'regenerate':  
                this.regenerateContent();  
                break;  
            case 'save':  
                this.saveContent(actionData.content);  
                break;  
            case 'export':  
                this.exportContent(actionData.format || 'txt');  
                break;  
            default:  
                console.warn('Unknown action type:', actionType);  
        }  
    }  
      
    copyResult() {  
        if (this.currentResult) {  
            const result = this.currentResult.result || this.currentResult;  
            const editorItem = result.display_items?.find(item => item.type === 'web_editor');  
              
            if (editorItem && editorItem.content && editorItem.content.text) {  
                const markdownContent = editorItem.content.text;  
                navigator.clipboard.writeText(markdownContent).then(() => {  
                    this.showToast('内容已复制到剪贴板');  
                });  
            } else {  
                const text = JSON.stringify(this.currentResult, null, 2);  
                navigator.clipboard.writeText(text).then(() => {  
                    this.showToast('结果已复制到剪贴板');  
                });  
            }  
        }  
    }
    downloadResult() {  
        if (this.currentResult) {  
            const text = this.extractTextFromResult(this.currentResult);  
            const blob = new Blob([text], { type: 'text/plain' });  
            const url = URL.createObjectURL(blob);  
            const a = document.createElement('a');  
            a.href = url;  
            a.download = `aiforge-result-${Date.now()}.txt`;  
            a.click();  
            URL.revokeObjectURL(url);  
            this.showToast('结果已下载');  
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
    
    extractTextFromResult(result) {  
        if (result && result.display_items) {  
            return result.display_items.map(item => {  
                if (item.content && item.content.text) {  
                    return item.content.text;  
                } else if (item.content && item.content.primary) {  
                    return item.content.primary;  
                }  
                return JSON.stringify(item.content);  
            }).join('\n\n');  
        }  
        return JSON.stringify(result, null, 2);  
    }  
    
    retryRender() {  
        if (this.currentResult) {  
            const resultContainer = document.getElementById('resultContainer');  
            this.displayResult(this.currentResult, resultContainer);  
            this.showToast('正在重试渲染...');  
        }  
    }  
}
    
// 初始化应用  
document.addEventListener('DOMContentLoaded', () => {  
    new AIForgeGUIApp();  
});