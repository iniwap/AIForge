class ConfigManager {    
    constructor() {    
        this.storageKey = 'aiforge-gui-settings';    
        this.defaultSettings = {    
            theme: 'dark',    
            language: 'zh',    
            progressLevel: 'detailed',    
            remoteUrl: ''    
        };  
        this.currentConfig = null; // 添加当前配置存储  
    }    
      
    // 添加缺失的方法  
    setCurrentConfig(config) {  
        this.currentConfig = config;  
    }  
      
    getCurrentConfig() {  
        return this.currentConfig;  
    }  
        
    getSettings() {    
        try {    
            const stored = localStorage.getItem(this.storageKey);    
            if (stored) {    
                return { ...this.defaultSettings, ...JSON.parse(stored) };    
            }    
        } catch (error) {    
            console.error('加载设置失败:', error);    
        }    
            
        return { ...this.defaultSettings };    
    }    
        
    saveSettings(settings) {    
        try {    
            const currentSettings = this.getSettings();    
            const newSettings = { ...currentSettings, ...settings };    
            localStorage.setItem(this.storageKey, JSON.stringify(newSettings));    
            return true;    
        } catch (error) {    
            console.error('保存设置失败:', error);    
            return false;    
        }    
    }    
        
    resetSettings() {    
        try {    
            localStorage.removeItem(this.storageKey);    
            return true;    
        } catch (error) {    
            console.error('重置设置失败:', error);    
            return false;    
        }    
    }    
        
    exportSettings() {    
        const settings = this.getSettings();    
        const blob = new Blob([JSON.stringify(settings, null, 2)], {    
            type: 'application/json'    
        });    
        const url = URL.createObjectURL(blob);    
        const a = document.createElement('a');    
        a.href = url;    
        a.download = 'aiforge-gui-settings.json';    
        a.click();    
        URL.revokeObjectURL(url);    
    }    
        
    async importSettings(file) {    
        try {    
            const text = await file.text();    
            const settings = JSON.parse(text);    
            this.saveSettings(settings);    
            return true;    
        } catch (error) {    
            console.error('导入设置失败:', error);    
            return false;    
        }    
    }    
}