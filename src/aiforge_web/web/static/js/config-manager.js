// 前端配置管理 
class ConfigManager {
    async checkConfigStatus() {
        try {
            const response = await fetch('/api/v1/config/status');
            return await response.json();
        } catch (error) {
            console.error('检查配置状态失败:', error);
            return { configured: false };
        }
    }

    async updateUserConfig(config) {
        const response = await fetch('/api/v1/config/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        return await response.json();
    }

    showConfigModal() {
        // 显示配置模态框，让用户选择：  
        // 1. 使用自己的 API 密钥  
        // 2. 购买 AIForge 服务计划  
        // 3. 使用免费额度  

        // 简化实现  
        console.log('显示配置模态框');
    }
}