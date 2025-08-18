class WebUIAdapter {  
    constructor() {  
        this.adapters = {  
            'web_card': this.renderCard.bind(this),  
            'web_table': this.renderTable.bind(this),  
            'web_dashboard': this.renderDashboard.bind(this),  
            'web_timeline': this.renderTimeline.bind(this),  
            'web_progress': this.renderProgress.bind(this),  
            'web_editor': this.renderEditor.bind(this),  
            'web_map': this.renderMap.bind(this),  
            'web_chart': this.renderChart.bind(this),  
            'web_gallery': this.renderGallery.bind(this),  
            'web_calendar': this.renderCalendar.bind(this),  
            'web_list': this.renderList.bind(this),  
            'web_text': this.renderText.bind(this),  
            'default': this.renderDefault.bind(this)  
        };  
    }  
  
    render(data, uiType = 'default', container) {  
        // 数据验证和预处理      
        if (!this.validateData(data)) {  
            this.renderError(container, new Error('Invalid data structure'), data);  
            return;  
        }  
  
        // 统一处理 "None" 值问题    
        const cleanedData = this.sanitizeNoneValues(data);  
  
        const adapter = this.adapters[uiType] || this.adapters['default'];  
        return adapter(cleanedData, container);  
    }  
  
    // 统一清理 "None" 值的方法    
    sanitizeNoneValues(data) {  
        const cleanedData = JSON.parse(JSON.stringify(data)); // 深拷贝    
  
        // 递归处理所有 display_items    
        if (cleanedData.display_items) {  
            cleanedData.display_items.forEach(item => {  
                if (item.content) {  
                    // 处理文本内容    
                    if (item.content.text === 'None' || item.content.text === 'null') {  
                        item.content.text = '⚠️ 内容生成失败，请点击"重新生成"按钮重试';  
                    }  
  
                    // 处理主要内容    
                    if (item.content.primary === 'None' || item.content.primary === 'null') {  
                        item.content.primary = '⚠️ 内容生成失败，请重试';  
                    }  
  
                    // 处理其他可能的 None 值    
                    this.cleanObjectNoneValues(item.content);  
                }  
            });  
        }  
  
        // 处理 actions 中的 None 值    
        if (cleanedData.actions) {  
            cleanedData.actions.forEach(action => {  
                if (action.data) {  
                    this.cleanObjectNoneValues(action.data);  
                }  
            });  
        }  
  
        return cleanedData;  
    }  
  
    // 递归清理对象中的 None 值    
    cleanObjectNoneValues(obj) {  
        for (const key in obj) {  
            if (obj[key] === 'None' || obj[key] === 'null') {  
                obj[key] = ''; // 或其他合适的默认值    
            } else if (typeof obj[key] === 'object' && obj[key] !== null) {  
                this.cleanObjectNoneValues(obj[key]);  
            }  
        }  
    }  
  
    // 统一的数据验证方法    
    validateData(data) {  
        return data &&  
            typeof data === 'object' &&  
            Array.isArray(data.display_items) &&  
            data.display_items.length > 0;  
    }  
  
    // 统一的动作按钮渲染    
    renderActionButtons(actions = []) {  
        return actions.map(action => {  
            const actionData = this.escapeJsonForHtml(action.data || {});  
            return `<button class="action-btn"     
                           onclick="window.aiforgeApp.handleAction('${action.action}', ${actionData})">    
                        ${this.getActionIcon(action.action)} ${action.label}    
                    </button>`;  
        }).join('');  
    }  
  
    // 安全的JSON转义    
    escapeJsonForHtml(obj) {  
        return JSON.stringify(obj).replace(/"/g, '&quot;');  
    }  
  
    // 动作图标映射    
    getActionIcon(action) {  
        const icons = {  
            'save': '💾', 'export': '📤', 'regenerate': '🔄', 'copy': '📋',  
            'edit': '✏️', 'download': '⬇️', 'share': '🔗', 'print': '🖨️',  
            'refresh': '🔄', 'delete': '🗑️', 'view': '👁️', 'filter': '🔍'  
        };  
        return icons[action] || '🔧';  
    }  
  
    renderCard(data, container) {  
        try {  
            const actions = this.renderActionButtons(data.actions);  
  
            const cardsHtml = data.display_items.map((item, index) => {  
                const content = item.content || {};  
                let contentHtml = '';  
  
                if (typeof content === 'object' && content.primary) {  
                    contentHtml = this.renderCardContent(content);  
                } else {  
                    contentHtml = this.formatContent(content);  
                }  
  
                return `    
                    <div class="result-card">    
                        <div class="card-header">    
                            <h3>${item.title || '执行结果'}</h3>    
                            <div class="card-actions">    
                                ${actions}    
                                <span class="text-xs text-gray-500">${new Date().toLocaleString()}</span>    
                            </div>    
                        </div>    
                        ${contentHtml}    
                        ${item.capabilities ? `    
                            <div class="mt-2 flex flex-wrap gap-1">    
                                ${item.capabilities.map(cap =>  
                    `<span class="text-xs px-2 py-1 bg-gray-100 rounded">${cap}</span>`  
                ).join('')}    
                            </div>    
                        ` : ''}    
                    </div>    
                `;  
            }).join('');  
  
            container.innerHTML = cardsHtml + this.renderSummary(data.summary_text, data);  
        } catch (error) {  
            this.renderError(container, error, data);  
        }  
    }  
  
    renderTable(data, container) {  
        try {  
            const tableItem = data.display_items[0];  
            const content = tableItem.content || {};  
            const { columns = [], rows = [] } = content;  
            const actions = this.renderActionButtons(data.actions);  
  
            // 处理动态列检测    
            const actualColumns = columns.length > 0 ? columns :  
                (rows.length > 0 ? Object.keys(rows[0]) : []);  
  
            const tableHtml = `    
                <div class="result-card">    
                    <div class="card-header">    
                        <h3>${tableItem.title || '数据表格'}</h3>    
                        <div class="card-actions">${actions}</div>    
                    </div>    
                    <div class="table-container">    
                        <table class="result-table">    
                            <thead>    
                                <tr>    
                                    ${actualColumns.map(header =>  
                `<th>${header}</th>`  
            ).join('')}    
                                </tr>    
                            </thead>    
                            <tbody>    
                                ${rows.map(row => `    
                                    <tr>    
                                        ${actualColumns.map(header =>  
                `<td>${this.formatCellContent(row[header])}</td>`  
            ).join('')}    
                                    </tr>    
                                `).join('')}    
                            </tbody>    
                        </table>    
                    </div>    
                    ${content.pagination ? this.renderPagination(content.pagination) : ''}    
                    ${this.renderSummary(data.summary_text, data)}    
                </div>    
            `;  
            container.innerHTML = tableHtml;  
        } catch (error) {  
            this.renderError(container, error, data);  
        }  
    }  
  
    renderEditor(data, container) {  
        try {  
            const editorItem = data.display_items[0];  
            const content = editorItem.content || {};  
            const { text = '', format = 'plain', metadata = {}, editable = false } = content;  
            const actions = this.renderActionButtons(data.actions);  
  
            // 检查是否已有复制和下载按钮    
            const hasCopyAction = data.actions && data.actions.some(action => action.action === 'copy');  
            const hasDownloadAction = data.actions && data.actions.some(action => action.action === 'download');  
            let contentHtml;  
            if (format === 'markdown') {  
                contentHtml = this.renderMarkdown(text);  
            } else if (this.isCodeFormat(format)) {  
                contentHtml = this.renderCode(text, format);  
            } else {  
                contentHtml = this.formatContent(text);  
            }  
  
            const editorHtml = `    
            <div class="result-card">    
                <div class="card-header">    
                    <h3>${editorItem.title || '生成的内容'}</h3>    
                    <div class="card-actions">    
                        ${actions}    
                        ${!hasCopyAction ?  
                    '<button class="action-btn" onclick="window.aiforgeApp.copyResult()">📋 复制</button>' : ''}    
                        ${!hasDownloadAction ?  
                    '<button class="action-btn" onclick="window.aiforgeApp.downloadResult()">💾 下载</button>' : ''}    
                    </div>    
                </div>    
                    
                <div class="editor-content">    
                    <div class="markdown-content" ${editable ? 'contenteditable="true"' : ''}>    
                        ${contentHtml}    
                    </div>    
                    <textarea class="hidden" id="markdownSource">${text}</textarea>    
                </div>    
                    
                ${Object.keys(metadata).length > 0 ? this.renderMetadata(metadata) : ''}    
                ${this.renderSummary(data.summary_text, data)}    
            </div>    
        `;  
  
            container.innerHTML = editorHtml;  
  
            if (editable) {  
                this.setupEditableContent(container, text);  
            }  
  
        } catch (error) {  
            this.renderError(container, error, data);  
        }  
    }  
  
    renderMarkdown(text) {  
        // 首先移除代码块标记，但更精确地匹配    
        text = text.replace(/```markdown\s*\n/gi, '');  
        text = text.replace(/```\s*$/gm, '');  
  
        // 处理表格  
        text = text.replace(/^\|(.*)\|\s*\n\|([-:| ]+)\|\s*\n(\|.*\|\s*\n)+/gm, (match) => {  
            const rows = match.trim().split('\n');  
            const headerRow = rows[0];  
            const dataRows = rows.slice(2);  
  
            // 处理表头  
            const header = headerRow  
                .split('|')  
                .filter(cell => cell.trim() !== '')  
                .map(cell => `<th class="border px-4 py-2 bg-gray-100">${cell.trim()}</th>`)  
                .join('');  
  
            // 处理数据行  
            const body = dataRows  
                .map(row => {  
                    return '<tr>' +  
                        row.split('|')  
                            .filter(cell => cell.trim() !== '')  
                            .map(cell => `<td class="border px-4 py-2">${cell.trim()}</td>`)  
                            .join('') +  
                        '</tr>';  
                })  
                .join('');  
  
            return `<table class="border-collapse table-auto w-full my-4">  
                  <thead><tr>${header}</tr></thead>  
                  <tbody>${body}</tbody>  
                </table>`;  
        });  
  
        // 处理标题    
        text = text.replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold mb-4">$1</h1>');  
        text = text.replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold mb-3">$1</h2>');  
        text = text.replace(/^### (.*$)/gim, '<h3 class="text-lg font-medium mb-2">$1</h3>');  
  
        // 处理链接  
        text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2" class="text-blue-600 hover:underline">$1</a>');  
  
        // 处理粗体和斜体  
        text = text.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');  
        text = text.replace(/\*(.*?)\*/gim, '<em>$1</em>');  
  
        // 处理行内代码  
        text = text.replace(/`([^`]+)`/gim, '<code class="bg-gray-100 px-1 rounded">$1</code>');  
  
        // 处理无序列表  
        text = text.replace(/(?:^- (.+)(?:\n|$))+/gm, (match) => {  
            const items = match.split('\n')  
                .filter(line => line.startsWith('- '))  
                .map(line => `<li class="ml-4">${line.substring(2)}</li>`)  
                .join('');  
            return `<ul class="list-disc my-2">${items}</ul>`;  
        });  
  
        // 处理段落  
        text = text.replace(/^([^<].*?)$/gm, (match, p1) => {  
            if (p1.trim() === '') return '';  
            return `<p class="my-2">${p1}</p>`;  
        });  
  
        return text;  
    }  
  
    isCodeFormat(format) {  
        const codeFormats = ['python', 'javascript', 'java', 'cpp', 'html', 'css'];  
        return codeFormats.includes(format);  
    }

    renderCode(code, language) {  
        const escapedCode = code  
            .replace(/&/g, '&amp;')  
            .replace(/</g, '&lt;')  
            .replace(/>/g, '&gt;')  
            .replace(/"/g, '&quot;')  
            .replace(/'/g, '&#39;');  
    
        return `<pre class="language-${language}"><code>${escapedCode}</code></pre>`;  
    }

    renderDefault(data, container) {  
        try {  
            const defaultItem = data.display_items[0];  
            const actions = this.renderActionButtons(data.actions);  
            
            const defaultHtml = `  
                <div class="result-card">  
                    <div class="card-header">  
                        <h3>${defaultItem.title || '执行结果'}</h3>  
                        <div class="card-actions">${actions}</div>  
                    </div>  
                    <div class="default-content">  
                        <pre>${JSON.stringify(defaultItem.content, null, 2)}</pre>  
                    </div>  
                    ${this.renderSummary(data.summary_text, data)}  
                </div>  
            `;  
            container.innerHTML = defaultHtml;  
        } catch (error) {  
            this.renderError(container, error, data);  
        }  
    }  
  
    renderCardContent(content) {  
        if (typeof content === 'object' && content.primary) {  
            let html = `<div class="primary-content">${content.primary}</div>`;  
            
            if (content.secondary) {  
                if (typeof content.secondary === 'object') {  
                    html += '<div class="secondary-content">';  
                    if (content.secondary.content) {  
                        html += `<p>${content.secondary.content}</p>`;  
                    }  
                    if (content.secondary.source) {  
                        html += `<p class="source">来源: ${content.secondary.source}</p>`;  
                    }  
                    html += '</div>';  
                } else {  
                    html += `<div class="secondary-content">${content.secondary}</div>`;  
                }  
            }  
            
            return html;  
        }  
        return this.formatContent(content);  
    }  
    
    formatCellContent(content) {  
        if (content === null || content === undefined) {  
            return '<span class="text-gray">-</span>';  
        }  
        if (typeof content === 'boolean') {  
            return content ? '<span class="text-green">✓</span>' : '<span class="text-red">✗</span>';  
        }  
        if (typeof content === 'number') {  
            return content.toLocaleString();  
        }  
        if (typeof content === 'string' && content.length > 50) {  
            return `<span title="${content}">${content.substring(0, 47)}...</span>`;  
        }  
        return String(content);  
    }  
    
    formatContent(content) {  
        if (typeof content === 'string') {  
            return content  
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  
                .replace(/\*(.*?)\*/g, '<em>$1</em>')  
                .replace(/\n/g, '<br>');  
        }  
        if (typeof content === 'object' && content !== null) {  
            return `<pre>${JSON.stringify(content, null, 2)}</pre>`;  
        }  
        return String(content);  
    }  
    
    renderSummary(summaryText, adaptationInfo = {}) {  
        if (!summaryText && !adaptationInfo.adaptation_method) return '';  
    
        return `  
            <div class="mt-4 space-y-2">  
                ${summaryText ? `  
                    <div class="p-3 bg-blue-50 rounded-lg">  
                        <p class="text-sm text-blue-800">${summaryText}</p>  
                    </div>  
                ` : ''}  
                ${adaptationInfo.adaptation_method ? `  
                    <div class="text-xs text-gray-400 flex justify-between">  
                        <span>适配方法: ${adaptationInfo.adaptation_method}</span>  
                        <span>任务类型: ${adaptationInfo.task_type || 'unknown'}</span>  
                    </div>  
                ` : ''}  
            </div>  
        `;  
    }  
    
    renderError(container, error, data) {  
        const errorHtml = `  
            <div class="result-card">  
                <div class="card-header">  
                    <h3>渲染错误</h3>  
                </div>  
                <div class="error-content">  
                    <p class="text-red">错误: ${error.message}</p>  
                    <details>  
                        <summary>原始数据</summary>  
                        <pre>${JSON.stringify(data, null, 2)}</pre>  
                    </details>  
                </div>  
            </div>  
        `;  
        container.innerHTML = errorHtml;  
    }  
    
    renderPagination(pagination) {  
        const { current_page = 1, total_pages = 1, total_items = 0 } = pagination;  
        
        if (total_pages <= 1) return '';  
        
        return `  
            <div class="pagination">  
                <span>第 ${current_page} / ${total_pages} 页，共 ${total_items} 条</span>  
            </div>  
        `;  
    }  
    
    setupEditableContent(container, originalText) {  
        const editableDiv = container.querySelector('[contenteditable="true"]');  
        if (editableDiv) {  
            editableDiv.addEventListener('input', () => {  
                // 处理编辑事件  
                console.log('Content edited');  
            });  
        }  
    }  
}