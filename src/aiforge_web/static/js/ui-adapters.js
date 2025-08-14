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
        try {  
            // 处理来自 RuleBasedAdapter 的数据结构  
            if (data.display_items && Array.isArray(data.display_items)) {                  
                const cardsHtml = data.display_items.map((item, index) => {  
                    
                    let contentHtml = '';  
                    if (item.content) {  
                        contentHtml = this.renderCardContent(item.content);  
                    }  
                    
                    return `  
                        <div class="result-card mb-4">  
                            <div class="flex items-start justify-between mb-3">  
                                <h3 class="text-lg font-semibold text-gray-900">${item.title || '执行结果'}</h3>  
                                <span class="text-xs text-gray-500">${new Date().toLocaleString()}</span>  
                            </div>  
                            ${contentHtml}  
                        </div>  
                    `;  
                }).join('');  
                
                const summaryHtml = data.summary_text ? `  
                    <div class="mt-4 p-3 bg-blue-50 rounded-lg">  
                        <p class="text-sm text-blue-800">${data.summary_text}</p>  
                    </div>  
                ` : '';  
                
                const finalHtml = cardsHtml + summaryHtml;  
                container.innerHTML = finalHtml;  
                
            } else {  
                // 回退到原始的简单卡片格式  
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
        } catch (error) {  
            console.error('Error in renderCard:', error);  
            container.innerHTML = `  
                <div class="result-card">  
                    <h3 class="text-lg font-semibold text-red-900">渲染错误</h3>  
                    <p class="text-red-700">${error.message}</p>  
                    <pre class="text-xs text-red-600 mt-2">${JSON.stringify(data, null, 2)}</pre>  
                </div>  
            `;  
        }  
    }
    
    renderCardContent(content) {          
        try {  
            if (typeof content === 'object' && content.primary) {  
                let html = `<div class="text-gray-900 font-medium mb-2">${content.primary}</div>`;  
                
                if (content.secondary) {  
                    if (typeof content.secondary === 'object') {  
                        html += `<div class="text-gray-600 text-sm space-y-1">`;  
                        if (content.secondary.content) {  
                            html += `<p>${content.secondary.content}</p>`;  
                        }  
                        if (content.secondary.source) {  
                            html += `<p class="text-xs text-gray-500">来源: ${content.secondary.source}</p>`;  
                        }  
                        if (content.secondary.date) {  
                            html += `<p class="text-xs text-gray-500">时间: ${content.secondary.date}</p>`;  
                        }  
                        html += `</div>`;  
                    } else {  
                        html += `<div class="text-gray-600 text-sm">${content.secondary}</div>`;  
                    }  
                }  
                
                return html;  
            }  
            
            const fallbackHtml = this.formatContent(content);  
            return fallbackHtml;  
        } catch (error) {  
            console.error('Error in renderCardContent:', error);  
            return `<div class="text-red-500">内容渲染错误: ${error.message}</div>`;  
        }  
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
        // 检查是否有编辑器类型的 display_items  
        const editorItem = data.display_items?.find(item => item.type === 'editor');  
        
        if (editorItem && editorItem.content && editorItem.content.text) {  
            const markdownContent = editorItem.content.text;  
            
            const editorHtml = `  
                <div class="result-card">  
                    <div class="flex justify-between items-center mb-4">  
                        <h3 class="text-lg font-semibold">${editorItem.title || '生成的内容'}</h3>  
                        <div class="flex space-x-2">  
                            <button class="text-sm px-3 py-1 border rounded hover:bg-gray-50" onclick="window.aiforgeApp.copyResult()">📋 复制</button>  
                            <button class="text-sm px-3 py-1 border rounded hover:bg-gray-50" onclick="window.aiforgeApp.downloadResult()">💾 下载</button>  
                        </div>  
                    </div>  
                    <div class="border rounded-lg">  
                        <div class="markdown-content p-4 max-h-96 overflow-y-auto">${this.renderMarkdown(markdownContent)}</div>  
                        <textarea class="hidden" id="markdownSource">${markdownContent}</textarea>  
                    </div>  
                    ${data.metadata ? this.renderMetadata(data.metadata) : ''}  
                </div>  
            `;  
            
            container.innerHTML = editorHtml;  
        } else {  
            // 回退到原有逻辑  
            this.renderCard(data, container);  
        }  
    }  
    
    renderMarkdown(text) {  
        // 简单的 Markdown 渲染  
        return text  
            .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold mb-4">$1</h1>')  
            .replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold mb-3">$1</h2>')  
            .replace(/^### (.*$)/gim, '<h3 class="text-lg font-medium mb-2">$1</h3>')  
            .replace(/\\*\\*(.*?)\\*\\*/gim, '<strong>$1</strong>')  
            .replace(/\\*(.*?)\\*/gim, '<em>$1</em>')  
            .replace(/^- (.*$)/gim, '<li class="ml-4">$1</li>')  
            .replace(/\\n/gim, '<br>');  
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