class ConfigManager {  
    constructor() {  
        this.config = this.loadConfig();  
        this.apiEndpoint = '/api/v1/config';  
    }  
  
    loadConfig() {  
        // 从localStorage加载配置  
        const saved = localStorage.getItem('aiforge-config');  
        const defaultConfig = {  
            api_key: '',  
            provider: 'openrouter',  
            locale: 'zh',  
            max_rounds: 2,  
            max_tokens: 4096  
        };  
          
        if (saved) {  
            try {  
                return { ...defaultConfig, ...JSON.parse(saved) };  
            } catch (e) {  
                console.warn('Failed to parse saved config:', e);  
            }  
        }  
        return defaultConfig;  
    }  
  
    saveConfig(config) {  
        // 保存到localStorage（不包含API密钥）  
        const configToSave = { ...config };  
        delete configToSave.api_key; // 不保存API密钥  
        localStorage.setItem('aiforge-config', JSON.stringify(configToSave));  
          
        // 更新内存中的配置  
        this.config = { ...this.config, ...config };  
    }  
  
    async updateSessionConfig(config) {  
        try {  
            const response = await fetch(`${this.apiEndpoint}/session`, {  
                method: 'POST',  
                headers: {  
                    'Content-Type': 'application/json',  
                    'X-Session-ID': this.getSessionId()  
                },  
                body: JSON.stringify(config)  
            });  
              
            if (!response.ok) {  
                throw new Error(`HTTP ${response.status}`);  
            }  
              
            return await response.json();  
        } catch (error) {  
            console.error('Failed to update session config:', error);  
            throw error;  
        }  
    }
     async getSessionConfig() {  
        try {  
            const response = await fetch(`${this.apiEndpoint}/session`, {  
                headers: {  
                    'X-Session-ID': this.getSessionId()  
                }  
            });  
              
            if (!response.ok) {  
                throw new Error(`HTTP ${response.status}`);  
            }  
              
            return await response.json();  
        } catch (error) {  
            console.error('Failed to get session config:', error);  
            return this.config; // 返回本地配置作为回退  
        }  
    }  
  
    getSessionId() {  
        // 获取或生成会话ID  
        let sessionId = sessionStorage.getItem('aiforge-session-id');  
        if (!sessionId) {  
            sessionId = 'session-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);  
            sessionStorage.setItem('aiforge-session-id', sessionId);  
        }  
        return sessionId;  
    }  
  
    async checkApiKeyStatus() {  
        // 检查API密钥状态  
        const config = await this.getSessionConfig();  
        return config.has_api_key || !!this.config.api_key;  
    }  
  
    getProviderDisplayName(provider) {  
        const providerNames = {  
            'openrouter': 'OpenRouter',  
            'deepseek': 'DeepSeek',  
            'ollama': 'Ollama (本地)',  
            'grok': 'Grok (X.AI)',  
            'qwen': '通义千问',  
            'gemini': 'Google Gemini',  
            'claude': 'Anthropic Claude',  
            'cohere': 'Cohere',  
            'mistral': 'Mistral AI'  
        };  
        return providerNames[provider] || provider;  
    }  
  
    getLocaleDisplayName(locale) {  
        const localeNames = {  
            'zh': '中文 (简体)',  
            'en': 'English',  
            'ja': '日本語',  
            'ko': '한국어',  
            'fr': 'Français',  
            'de': 'Deutsch',  
            'es': 'Español',  
            'pt': 'Português',  
            'ru': 'Русский',  
            'ar': 'العربية',  
            'hi': 'हिन्दी',  
            'vi': 'Tiếng Việt'  
        };  
        return localeNames[locale] || locale;  
    }  
}