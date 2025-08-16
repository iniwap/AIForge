class TaskTypeManager {
    constructor() {
        this.builtinTypes = new Map();
        this.customTypes = new Map();
        this.loadBuiltinTypes();
    }

    async loadBuiltinTypes() {
        try {
            const response = await fetch('/api/v1/metadata/task-types');
            const data = await response.json();

            data.builtin_types.forEach(type => {
                this.builtinTypes.set(type.id, type);
            });

            // 渲染任务类型按钮  
            this.renderTaskTypeButtons();
        } catch (error) {
            console.error('加载任务类型失败:', error);
        }
    }

    renderTaskTypeButtons() {
        const container = document.getElementById('taskTypeButtons');
        const buttons = Array.from(this.builtinTypes.values()).map(type => `  
            <button class="task-type-btn" data-type="${type.id}" title="${type.description}">  
                ${type.icon} ${type.name}  
            </button>  
        `).join('');

        container.innerHTML = buttons;
    }

    registerCustomType(typeConfig) {
        // 为未来的自定义任务类型预留接口  
        this.customTypes.set(typeConfig.id, typeConfig);
        this.renderTaskTypeButtons();
    }

    getTypeConfig(typeId) {
        return this.builtinTypes.get(typeId) || this.customTypes.get(typeId);
    }
}