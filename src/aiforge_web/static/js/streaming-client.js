class StreamingClient {  
    constructor(baseUrl = '') {  
        this.baseUrl = baseUrl;  
        this.isConnected = false;  
        this.abortController = null;  
    }  
      
    async executeInstruction(instruction, contextData = {}, callbacks = {}) {  
        const {  
            onProgress = () => {},  
            onResult = () => {},  
            onError = () => {},  
            onComplete = () => {}  
        } = callbacks;  
          
        try {  
            // 关闭现有连接  
            this.disconnect();  
              
            // 创建新的 AbortController  
            this.abortController = new AbortController();  
              
            // 发送指令到流式端点  
            const response = await fetch(`${this.baseUrl}/api/process/stream`, {  
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
                signal: this.abortController.signal  
            });  
              
            if (!response.ok) {  
                throw new Error(`HTTP error! status: ${response.status}`);  
            }  
              
            // 处理流式响应  
            const reader = response.body.getReader();  
            const decoder = new TextDecoder();  
            this.isConnected = true;  
              
            while (this.isConnected && !this.abortController.signal.aborted) {  
                const { done, value } = await reader.read();  
                  
                if (done) break;  
                  
                const chunk = decoder.decode(value, { stream: true });  
                const lines = chunk.split('\\n');  
                  
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
              
        } catch (error) {  
            console.error('流式执行错误:', error);  
            onError(error);  
        } finally {  
            onComplete();  
            this.disconnect();  
        }  
    }  
      
    handleMessage(data, callbacks) {  
        const { onProgress, onResult, onError, onComplete } = callbacks;  
          
        switch (data.type) {  
            case 'progress':  
                onProgress(data.message, data.progress_type);  
                break;  
            case 'result':  
                onResult(data.data);  
                break;  
            case 'error':  
                onError(new Error(data.message));  
                break;  
            case 'complete':  
                onComplete();  
                this.disconnect();  
                break;  
            case 'heartbeat':  
                // 心跳消息，保持连接活跃  
                break;  
            default:  
                console.warn('未知消息类型:', data.type);  
        }  
    }  
      
    disconnect() {  
        this.isConnected = false;  
        if (this.abortController) {  
            this.abortController.abort();  
            this.abortController = null;  
        }  
    }  
}  
  
// 导出供其他模块使用  
if (typeof module !== 'undefined' && module.exports) {  
    module.exports = StreamingClient;  
}