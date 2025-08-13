class WebUIAdapter {  
    constructor() {  
        this.adapters = {  
            'web_card': this.renderCard.bind(this),  
            'web_table': this.renderTable.bind(this),  
            'web_dashboard': this.renderDashboard.bind(this),  
            'web_timeline': this.renderTimeline.bind(this),  
            'web_progress': this.renderProgress.bind(this),  
            'web_editor': this.renderEditor.bind(this),  
            'default': this.renderDefault.bind(this)  
        };  
    }  
  
    render(data, uiType = 'default', container) {  
        const adapter = this.adapters[uiType] || this.adapters['default'];  
        return adapter(data, container);  
    }  
  
    renderCard(data, container) {  
        const cardHtml = `  
            <div class="result-card">  
                <div class="flex items-start justify-between mb-3">  
                    <h3 class="text-lg font-semibold text-gray-900">${data.title || '执行结果'}</h3>  
                    <span class="text-xs text-gray-500">${new Date().toLocaleString()}</span>  
                </div>  
                ${data.content ? `<div class="text-gray-700 mb-3">${this.formatContent(data.content)}</div>` : ''}  
                ${data.metadata ? this.renderMetadata(data.metadata) : ''}  
            </div>  
        `;  
        container.innerHTML = cardHtml;  
    }  
  
    renderTable(data, container) {  
        if (!data.rows || !Array.isArray(data.rows)) {  
            return this.renderDefault(data, container);  
        }  
  
        const headers = data.headers || Object.keys(data.rows[0] || {});  
        const tableHtml = `  
            <div class="result-card">  
                <h3 class="text-lg font-semibold mb-4">${data.title || '数据表格'}</h3>  
                <div class="overflow-x-auto">  
                    <table class="result-table">  
                        <thead>  
                            <tr>  
                                ${headers.map(header => `<th>${header}</th>`).join('')}  
                            </tr>  
                        </thead>  
                        <tbody>  
                            ${data.rows.map(row => `  
                                <tr>  
                                    ${headers.map(header => `<td>${row[header] || '-'}</td>`).join('')}  
                                </tr>  
                            `).join('')}  
                        </tbody>  
                    </table>  
                </div>  
            </div>  
        `;  
        container.innerHTML = tableHtml;  
    }
    renderDashboard(data, container) {  
        const dashboardHtml = `  
            <div class="result-card">  
                <h3 class="text-lg font-semibold mb-4">${data.title || '数据仪表板'}</h3>  
                <div class="dashboard-grid">  
                    ${data.metrics ? data.metrics.map(metric => `  
                        <div class="metric-card">  
                            <div class="text-sm opacity-90">${metric.label}</div>  
                            <div class="text-2xl font-bold">${metric.value}</div>  
                            ${metric.trend ? `<div class="text-xs mt-1">${metric.trend}</div>` : ''}  
                        </div>  
                    `).join('') : ''}  
                </div>  
                ${data.charts ? this.renderCharts(data.charts) : ''}  
                ${data.summary ? `<div class="mt-4 p-3 bg-gray-50 rounded">${data.summary}</div>` : ''}  
            </div>  
        `;  
        container.innerHTML = dashboardHtml;  
    }  
  
    renderTimeline(data, container) {  
        const timelineHtml = `  
            <div class="result-card">  
                <h3 class="text-lg font-semibold mb-4">${data.title || '执行时间线'}</h3>  
                <div class="space-y-3">  
                    ${data.steps ? data.steps.map((step, index) => `  
                        <div class="flex items-start space-x-3">  
                            <div class="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-sm font-medium text-blue-600">  
                                ${index + 1}  
                            </div>  
                            <div class="flex-1">  
                                <div class="font-medium text-gray-900">${step.title || step}</div>  
                                ${step.description ? `<div class="text-sm text-gray-500 mt-1">${step.description}</div>` : ''}  
                                ${step.status ? `<div class="text-xs mt-1 px-2 py-1 rounded ${this.getStatusClass(step.status)}">${step.status}</div>` : ''}  
                            </div>  
                        </div>  
                    `).join('') : ''}  
                </div>  
            </div>  
        `;  
        container.innerHTML = timelineHtml;  
    }  
  
    renderProgress(data, container) {  
        const percentage = data.percentage || 0;  
        const progressHtml = `  
            <div class="result-card">  
                <h3 class="text-lg font-semibold mb-4">${data.title || '处理进度'}</h3>  
                <div class="mb-4">  
                    <div class="flex justify-between text-sm text-gray-600 mb-2">  
                        <span>${data.current || 0} / ${data.total || 0}</span>  
                        <span>${percentage.toFixed(1)}%</span>  
                    </div>  
                    <div class="w-full bg-gray-200 rounded-full h-2">  
                        <div class="bg-blue-600 h-2 rounded-full transition-all duration-300" style="width: ${percentage}%"></div>  
                    </div>  
                </div>  
                ${data.details ? `<div class="text-sm text-gray-600">${data.details}</div>` : ''}  
            </div>  
        `;  
        container.innerHTML = progressHtml;  
    }  
  
    renderEditor(data, container) {  
        const editorHtml = `  
            <div class="result-card">  
                <div class="flex justify-between items-center mb-4">  
                    <h3 class="text-lg font-semibold">${data.title || '内容编辑器'}</h3>  
                    <div class="flex space-x-2">  
                        <button class="text-sm px-3 py-1 border rounded hover:bg-gray-50" onclick="this.copyContent()">复制</button>  
                        <button class="text-sm px-3 py-1 border rounded hover:bg-gray-50" onclick="this.downloadContent()">下载</button>  
                    </div>  
                </div>  
                <div class="border rounded-lg">  
                    <textarea   
                        class="w-full h-64 p-4 border-0 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"  
                        placeholder="生成的内容将在这里显示..."  
                    >${data.content || ''}</textarea>  
                </div>  
                ${data.metadata ? this.renderMetadata(data.metadata) : ''}  
            </div>  
        `;  
        container.innerHTML = editorHtml;  
    }  
  
    renderDefault(data, container) {  
        const defaultHtml = `  
            <div class="result-card">  
                <h3 class="text-lg font-semibold mb-4">执行结果</h3>  
                <div class="bg-gray-50 rounded p-4">  
                    <pre class="text-sm text-gray-800 whitespace-pre-wrap">${JSON.stringify(data, null, 2)}</pre>  
                </div>  
            </div>  
        `;  
        container.innerHTML = defaultHtml;  
    }  
  
    // 辅助方法  
    formatContent(content) {  
        if (typeof content === 'string') {  
            return content.replace(/\n/g, '<br>');  
        }  
        return JSON.stringify(content, null, 2);  
    }  
  
    renderMetadata(metadata) {  
        return `  
            <div class="mt-3 pt-3 border-t border-gray-200">  
                <div class="text-xs text-gray-500 space-y-1">  
                    ${Object.entries(metadata).map(([key, value]) =>   
                        `<div><span class="font-medium">${key}:</span> ${value}</div>`  
                    ).join('')}  
                </div>  
            </div>  
        `;  
    }  
  
    renderCharts(charts) {  
        // 简化的图表渲染，实际可以集成 Chart.js 等库  
        return `  
            <div class="mt-4">  
                <h4 class="text-md font-medium mb-2">数据图表</h4>  
                <div class="bg-gray-100 rounded p-4 text-center text-gray-500">  
                    图表功能待实现 (可集成 Chart.js)  
                </div>  
            </div>  
        `;  
    }  
  
    getStatusClass(status) {  
        const statusClasses = {  
            'completed': 'bg-green-100 text-green-800',  
            'running': 'bg-blue-100 text-blue-800',  
            'failed': 'bg-red-100 text-red-800',  
            'pending': 'bg-yellow-100 text-yellow-800'  
        };  
        return statusClasses[status] || 'bg-gray-100 text-gray-800';  
    }  
}