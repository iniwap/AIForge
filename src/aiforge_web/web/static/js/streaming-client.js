class StreamingClient {
    constructor(baseUrl = '', sessionManager = null) {
        this.baseUrl = baseUrl;
        this.isConnected = false;
        this.abortController = null;
        this.sessionManager = sessionManager;
    }
    disconnect() {
        this.isConnected = false;
        if (this.abortController) {
            this.abortController.abort();
            this.abortController = null;
        }
    }
    async executeInstruction(instruction, contextData = {}, callbacks = {}) {
        const {
            onProgress = () => { },
            onResult = () => { },
            onError = () => { },
            onComplete = () => { }
        } = callbacks;

        try {
            this.disconnect();
            this.abortController = new AbortController();

            const requestBody = {  
                instruction: instruction,  
                task_type: contextData.taskType,  
                user_id: contextData.user_id,  
                session_id: this.sessionManager ? this.sessionManager.sessionId : contextData.session_id,
                progress_level: contextData.progress_level
            };  
    
            const headers = this.sessionManager ?   
                this.sessionManager.getHeaders() :   
                { 'Content-Type': 'application/json' };  
    
            const response = await fetch(`${this.baseUrl}/api/v1/core/execute/stream`, {  
                method: 'POST',  
                headers: headers,  
                body: JSON.stringify(requestBody),  
                signal: this.abortController.signal  
            });
            
            if (!response.ok) {  
                if (response.status === 400) {  
                    // 尝试解析错误详情  
                    try {  
                        const errorData = await response.json();  
                        if (errorData.detail && errorData.detail.includes('API密钥')) {  
                            // 触发配置提示  
                            if (callbacks.onConfigRequired) {  
                                callbacks.onConfigRequired(errorData.detail);  
                                callbacks.onComplete(false);
                                return;  
                            }  
                        }  
                    } catch (e) {  
                        // 解析失败，继续抛出原始错误  
                    }  
                }  
                throw new Error(`HTTP error! status: ${response.status}`);  
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            this.isConnected = true;

            let buffer = ''; // 添加缓冲区处理粘连消息  

            while (this.isConnected && !this.abortController.signal.aborted) {
                const { done, value } = await reader.read();

                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;

                // 按双换行符分割完整的 SSE 消息  
                const messages = buffer.split('\n\n');
                buffer = messages.pop() || ''; // 保留不完整的消息  

                for (const message of messages) {
                    if (message.trim()) {
                        const lines = message.split('\n');
                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                try {
                                    const jsonStr = line.slice(6).trim();
                                    if (jsonStr) {
                                        const data = JSON.parse(jsonStr);
                                        console.log('[DEBUG] 前端收到的数据:', data);
                                        this.handleMessage(data, { onProgress, onResult, onError, onComplete });
                                    }
                                } catch (e) {
                                    console.warn('解析消息失败:', line, e);
                                }
                            }
                        }
                    }
                }
            }
        } catch (error) {
            // 区分用户主动停止和真正的错误  
            if (error.name === 'AbortError') {
                console.log('流式执行已被用户停止');
                // 不调用 onError，避免显示错误消息  
            } else {
                console.error('流式执行错误:', error);
                onError(error);
            }
        } finally {
            //onComplete();
            this.disconnect();
        }
    }


    handleMessage(data, callbacks) {
        switch (data.type) {
            case 'progress':
                if (callbacks.onProgress) {
                    callbacks.onProgress(data.message, data.progress_type || 'info');
                }
                break;

            case 'result':
                if (callbacks.onResult) {
                    callbacks.onResult(data.data);
                }
                break;

            case 'error':
                if (callbacks.onError) {
                    callbacks.onError(new Error(data.message));
                }
                break;

            case 'complete':
                if (callbacks.onComplete) {
                    callbacks.onComplete();
                }
                break;

            case 'heartbeat':
                // 触发呼吸效果回调  
                if (callbacks.onHeartbeat) {
                    callbacks.onHeartbeat();
                }
                break;
            // 检查停止消息  
            case 'stopped':
                console.log('执行已被服务器停止');  
                if (callbacks.onComplete) {  
                    callbacks.onComplete();  
                }  
                this.disconnect();  
                break;  
            default:
                console.warn('Unknown message type:', data.type);
        }
    }
    async stopExecution() {  
        this.disconnect();  
        if (this.sessionManager) {  
            return await this.sessionManager.stopExecution();  
        }  
    }  
}

// 导出供其他模块使用  
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StreamingClient;
}