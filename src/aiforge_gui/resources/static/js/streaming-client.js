// 流式客户端
class StreamingClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
        this.isConnected = false;
        this.abortController = null;
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

            const response = await fetch(`${this.baseUrl}/api/v1/core/execute/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    instruction: instruction,
                    task_type: contextData.taskType,
                    user_id: contextData.user_id,
                    session_id: contextData.session_id
                }),
                signal: this.abortController.signal,
                timeout: 300000, // 5分钟超时
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

            let buffer = '';

            while (this.isConnected && !this.abortController.signal.aborted) {
                const { done, value } = await reader.read();

                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;

                const messages = buffer.split('\n\n');
                buffer = messages.pop() || '';

                for (const message of messages) {
                    if (message.trim()) {
                        const lines = message.split('\n');
                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                try {
                                    const jsonStr = line.slice(6).trim();
                                    if (jsonStr) {
                                        const data = JSON.parse(jsonStr);
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
            if (error.name === 'AbortError') {
                console.log('流式执行已被用户停止');
            } else {
                console.error('流式执行错误:', error);
                onError(error);
            }
        } finally {
            onComplete();
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
                if (callbacks.onHeartbeat) {
                    callbacks.onHeartbeat();
                }
                break;

            default:
                console.warn('Unknown message type:', data.type);
        }
    }
}