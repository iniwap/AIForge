class AIForgeGUIApp {  
    constructor() {  
        this.isLocal = false;  
        this.streamingClient = null;  
        this.configManager = new GUIConfigManager();  
        this.uiAdapter = new WebUIAdapter();  
        this.currentTaskType = 'auto';  
        this.isExecuting = false;  
        this.currentResult = null;  
        this.connectionInfo = null;  
  
        this.init();  
        window.aiforgeApp = this;  
    }  
  
    async init() {  
        await this.checkConnectionMode();  
        await this.loadCurrentConfig();  
        this.initializeUI();  
        this.initializeConfigUI();  
        this.initializeStreamingClient();  
        this.updateConfigUI();  
    }  
  
    async loadCurrentConfig() {  
        try {  
            if (typeof pywebview !== 'undefined' && pywebview.api) {  
                const response = await pywebview.api.get_config_info();  
                const configInfo = JSON.parse(response);  
                this.configManager.setCurrentConfig(configInfo.current_config);  
                this.connectionInfo = configInfo;  
            }  
        } catch (error) {  
            console.error('Failed to load current config:', error);  
        }  
    }  
  
    initializeConfigUI() {  
        // 配置按钮事件  
        const configBtn = document.getElementById('configBtn');  
        const configModal = document.getElementById('configModal');  
        const closeConfigBtn = document.getElementById('closeConfigBtn');  
        const saveConfigBtn = document.getElementById('saveConfigBtn');  
        const cancelConfigBtn = document.getElementById('cancelConfigBtn');  
  
        configBtn?.addEventListener('click', () => this.showConfigModal());  
        closeConfigBtn?.addEventListener('click', () => this.hideConfigModal());  
        cancelConfigBtn?.addEventListener('click', () => this.hideConfigModal());  
        saveConfigBtn?.addEventListener('click', () => this.saveConfig());  
  
        // 快速配置选择器  
        const providerSelect = document.getElementById('providerSelect');  
        const localeSelect = document.getElementById('localeSelect');  
  
        providerSelect?.addEventListener('change', (e) => {  
            this.updateQuickConfig('provider', e.target.value);  
        });  
  
        localeSelect?.addEventListener('change', (e) => {  
            this.updateQuickConfig('locale', e.target.value);  
        });  
  
        // 模态框外点击关闭  
        configModal?.addEventListener('click', (e) => {  
            if (e.target === configModal) {  
                this.hideConfigModal();  
            }  
        });  
  
        // API密钥状态检查按钮  
        const checkApiKeyBtn = document.getElementById('checkApiKeyBtn');  
        checkApiKeyBtn?.addEventListener('click', () => this.checkApiKeyStatus());  
    }  
  
    updateConfigUI() {  
        const config = this.configManager.getCurrentConfig();  
        if (!config) return;  
  
        // 更新快速配置选择器  
        const providerSelect = document.getElementById('providerSelect');  
        const localeSelect = document.getElementById('localeSelect');  
  
        if (providerSelect) {  
            providerSelect.value = config.provider || 'openrouter';  
        }  
  
        if (localeSelect) {  
            localeSelect.value = config.locale || 'zh';  
        }  
  
        // 更新配置状态指示器  
        this.updateConfigStatus();  
    }  
  
    updateConfigStatus() {  
        const config = this.configManager.getCurrentConfig();  
        const statusIndicator = document.getElementById('configStatus');  
        const modeIndicator = document.getElementById('modeIndicator');  
    
        if (statusIndicator) {  
            const hasApiKey = config?.has_api_key;  
            statusIndicator.className = hasApiKey ? 'status-ok' : 'status-warning';  
            statusIndicator.textContent = hasApiKey ? '已配置' : '需要配置';  
        }  
    
        if (modeIndicator && this.connectionInfo) {  
            const mode = this.connectionInfo.mode;  
            modeIndicator.textContent = mode === 'local' ? '本地模式' : '远程模式';  
            modeIndicator.className = `mode-${mode}`;  
        }  
    }  
    
    showConfigModal() {  
        const modal = document.getElementById('configModal');  
        if (modal) {  
            // 加载当前配置到表单  
            this.loadConfigToForm();  
            modal.classList.remove('hidden');  
        }  
    }  
    
    hideConfigModal() {  
        const modal = document.getElementById('configModal');  
        if (modal) {  
            modal.classList.add('hidden');  
        }  
    }  
    
    loadConfigToForm() {  
        if (!this.currentConfig) return;  
    
        const apiKeyInput = document.getElementById('apiKeyInput');  
        const providerInput = document.getElementById('providerInput');  
        const localeInput = document.getElementById('localeInput');  
        const maxRoundsInput = document.getElementById('maxRoundsInput');  
        const maxTokensInput = document.getElementById('maxTokensInput');  
    
        // 不显示API密钥值，只显示是否已设置  
        if (apiKeyInput) {  
            apiKeyInput.placeholder = this.currentConfig.has_api_key ? '已设置API密钥' : '请输入API密钥';  
        }  
    
        if (providerInput) {  
            providerInput.value = this.currentConfig.provider || 'openrouter';  
        }  
    
        if (localeInput) {  
            localeInput.value = this.currentConfig.locale || 'zh';  
        }  
    
        if (maxRoundsInput) {  
            maxRoundsInput.value = this.currentConfig.max_rounds || 2;  
        }  
    
        if (maxTokensInput) {  
            maxTokensInput.value = this.currentConfig.max_tokens || 4096;  
        }  
    }  
    
    async updateQuickConfig(key, value) {  
        try {  
            const config = { [key]: value };  
            const response = await pywebview.api.update_config(JSON.stringify(config));  
            const result = JSON.parse(response);  
            
            if (result.success) {  
                // 更新本地配置状态  
                await this.loadCurrentConfig();  
                this.updateConfigUI();  
                this.showToast(`${key === 'provider' ? '提供商' : '语言'}已更新为 ${value}`);  
            } else {  
                this.showToast(`配置更新失败: ${result.error}`, 'error');  
            }  
        } catch (error) {  
            console.error('Failed to update quick config:', error);  
            this.showToast('配置更新失败', 'error');  
        }  
    }  
    
    async saveConfig() {  
        try {  
            const apiKey = document.getElementById('apiKeyInput')?.value;  
            const provider = document.getElementById('providerInput')?.value;  
            const locale = document.getElementById('localeInput')?.value;  
            const maxRounds = document.getElementById('maxRoundsInput')?.value;  
            const maxTokens = document.getElementById('maxTokensInput')?.value;  
    
            const config = {  
                provider: provider || 'openrouter',  
                locale: locale || 'zh'  
            };  
    
            if (apiKey) {  
                config.api_key = apiKey;  
            }  
    
            if (maxRounds) {  
                config.max_rounds = parseInt(maxRounds);  
            }  
    
            if (maxTokens) {  
                config.max_tokens = parseInt(maxTokens);  
            }  
    
            const response = await pywebview.api.update_config(JSON.stringify(config));  
            const result = JSON.parse(response);  
    
            if (result.success) {  
                await this.loadCurrentConfig();  
                this.updateConfigUI();  
                this.hideConfigModal();  
                this.showToast('配置已保存');  
                
                if (result.requires_restart) {  
                    this.showToast('配置已更新，引擎将重新初始化', 'info');  
                }  
            } else {  
                this.showToast(`配置保存失败: ${result.error}`, 'error');  
            }  
        } catch (error) {  
            console.error('Failed to save config:', error);  
            this.showToast('配置保存失败', 'error');  
        }  
    }  
    
    async checkApiKeyStatus() {  
        try {  
            const response = await pywebview.api.check_api_key_status();  
            const result = JSON.parse(response);  
            
            const statusText = result.has_api_key ? '✅ API密钥已配置' : '❌ 未配置API密钥';  
            this.showToast(statusText, result.has_api_key ? 'success' : 'warning');  
        } catch (error) {  
            console.error('Failed to check API key status:', error);  
            this.showToast('检查API密钥状态失败', 'error');  
        }  
    }  

    async checkConnectionMode() {
        const statusIndicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');

        statusIndicator.className = 'status-indicator connecting';
        statusText.textContent = '连接中...';

        try {
            // 等待PyWebView就绪  
            await this.waitForPyWebViewReady();

            if (typeof pywebview !== 'undefined' && typeof pywebview.api !== 'undefined') {
                const info = await pywebview.api.get_connection_info();
                const connectionInfo = JSON.parse(info);
                this.isLocal = connectionInfo.mode === 'local';
                this.updateConnectionStatus(connectionInfo);
            } else {
                this.isLocal = false;
                this.updateConnectionStatus({ mode: 'remote' });
            }
        } catch (error) {
            console.error('检查连接模式失败:', error);
            this.isLocal = false;
            statusIndicator.className = 'status-indicator error';
            statusText.textContent = '连接失败';
        }
    }

    waitForPyWebViewReady() {
        return new Promise((resolve, reject) => {
            // 如果已经就绪，直接返回  
            if (typeof pywebview !== 'undefined' &&
                typeof pywebview.api !== 'undefined' &&
                typeof pywebview.api.get_connection_info === 'function') {
                resolve();
                return;
            }

            // 监听 PyWebView 就绪事件  
            const onReady = () => {
                if (typeof pywebview !== 'undefined' &&
                    typeof pywebview.api !== 'undefined' &&
                    typeof pywebview.api.get_connection_info === 'function') {
                    document.removeEventListener('pywebviewready', onReady);
                    resolve();
                }
            };

            document.addEventListener('pywebviewready', onReady);

            // 超时保护  
            setTimeout(() => {
                document.removeEventListener('pywebviewready', onReady);
                reject(new Error('PyWebView initialization timeout'));
            }, 10000);
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
        // 在执行前检查 API 密钥状态（如果有配置管理器）  
        if (this.configManager) {  
            try {  
                const hasApiKey = await this.configManager.checkApiKeyStatus();  
                if (!hasApiKey) {  
                    this.showToast('请先配置 API 密钥', 'error');  
                    // GUI 版本可能需要调用 pywebview API 来显示配置界面  
                    if (typeof pywebview !== 'undefined' && pywebview.api.showConfigDialog) {  
                        pywebview.api.showConfigDialog();  
                    }  
                    return;  
                }  
            } catch (error) {  
                console.error('检查 API 密钥状态失败:', error);  
                this.showToast('无法验证 API 密钥状态，请检查配置', 'error');  
                return;  
            }  
        }  

        if (this.isExecuting) {
            return;
        }

        this.setExecuting(true);

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

            const localAPIUrl = await this.getLocalAPIServerURL();

            if (localAPIUrl) {
                // 先测试连接  
                const isConnected = await this.testConnection(localAPIUrl);
                if (!isConnected) {
                    throw new Error('无法连接到本地 API 服务器');
                }

                // 使用本地 API 服务器的流式接口  
                const localStreamingClient = new StreamingClient(localAPIUrl);
                await localStreamingClient.executeInstruction(instruction, {
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
                    onComplete:(isSuccess = true) => {    
                        if (isSuccess) {    
                            this.addProgressMessage('✅ 执行完成', 'complete');    
                        }else{
                            this.addProgressMessage('❌ 执行失败', 'error');    
                        }
                        this.setExecutionState(false);    
                    },
                    onConfigRequired: (message) => {  
                        this.showToast(message, 'error');  
                        this.showConfigModal();
                        this.setExecutionState(false);  
                    }  
                });
            } else {
                await this.executeFallbackLocalInstruction(instruction);
            }
        } catch (error) {
            console.error('本地执行错误详情:', error);
            this.addProgressMessage(`❌ 本地执行错误: ${error.message}`, 'error');
            // 如果流式执行失败，回退到 WebView 桥接  
            await this.executeFallbackLocalInstruction(instruction);
        } finally {
            this.setExecuting(false);
        }
    }
    async testConnection(apiUrl) {
        try {
            const response = await fetch(`${apiUrl}/api/health`, {
                method: 'GET',
                timeout: 5000
            });
            return response.ok;
        } catch (error) {
            console.error('连接测试失败:', error);
            return false;
        }
    }

    async getLocalAPIServerURL() {
        try {
            // 通过 WebView 桥接获取本地 API 服务器 URL  
            if (typeof pywebview !== 'undefined' && typeof pywebview.api !== 'undefined') {
                const info = await pywebview.api.get_connection_info();
                const connectionInfo = JSON.parse(info);
                return connectionInfo.api_server_url;
            }
            return null;
        } catch (error) {
            console.error('获取本地 API 服务器 URL 失败:', error);
            return null;
        }
    }

    async checkLocalAPIServer() {
        try {
            // 获取正确的 API 服务器 URL  
            const localAPIUrl = await this.getLocalAPIServerURL();
            if (!localAPIUrl) {
                return false;
            }

            // 检查本地 API 服务器健康状态  
            const response = await fetch(`${localAPIUrl}/api/health`, {
                method: 'GET',
                timeout: 2000
            });
            return response.ok;
        } catch (error) {
            console.log('本地 API 服务器不可用:', error.message);
            return false;
        }
    }

    async executeFallbackLocalInstruction(instruction) {
        try {
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
            console.error('回退执行错误详情:', error);
            this.addProgressMessage(`❌ 回退执行错误: ${error.message}`, 'error');
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
            onComplete:(isSuccess = true) => {    
                if (progressLevel !== 'none') {    
                    if (isSuccess) {    
                        this.addProgressMessage('✅ 执行完成', 'complete');    
                    }else{
                        this.addProgressMessage('❌ 执行失败', 'error');    
                    }
                }    
                this.setExecutionState(false);    
            }
        });
    }

    stopExecution() {
        this.streamingClient.disconnect();
        this.addProgressMessage('⏹️ 正在停止执行...', 'info');
        this.setExecutionState(false);
    }

    setExecutionState(isExecuting) {
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