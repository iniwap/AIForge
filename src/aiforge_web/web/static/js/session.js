class SessionManager {  
    constructor() {  
        this.sessionId = this.getOrCreateSessionId();  
    }  
      
    getOrCreateSessionId() {  
        let sessionId = localStorage.getItem('aiforge_session_id');  
        if (!sessionId) {  
            sessionId = this.generateSessionId();  
            localStorage.setItem('aiforge_session_id', sessionId);  
        }  
        return sessionId;  
    }  
      
    generateSessionId() {  
        return 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();  
    }  
      
    getHeaders() {  
        return {  
            'X-Session-ID': this.sessionId,  
            'Content-Type': 'application/json'  
        };  
    }  
      
    // 页面卸载时清理会话  
    setupCleanup() {  
        window.addEventListener('beforeunload', () => {  
            navigator.sendBeacon('/api/v1/core/session/cleanup/' + this.sessionId);  
        });  
    }
    
    async stopExecution() {  
        try {  
            const response = await fetch('/api/v1/core/stop', {  
                method: 'POST',  
                headers: this.getHeaders()  
            });  
            return await response.json();  
        } catch (error) {  
            console.error('停止执行失败:', error);  
            return { success: false, error: error.message };  
        }  
    }  
      
    setupCleanup() {  
        window.addEventListener('beforeunload', () => {  
            // 页面卸载时停止执行并清理会话  
            this.stopExecution();  
            navigator.sendBeacon('/api/v1/core/session/cleanup/' + this.sessionId);  
        });  
    } 
}  
  
// 全局会话管理器  
const sessionManager = new SessionManager();  
sessionManager.setupCleanup();