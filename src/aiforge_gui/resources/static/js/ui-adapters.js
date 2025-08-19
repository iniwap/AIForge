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
            return `<button class="text-sm px-3 py-1 border rounded hover:bg-gray-50"   
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

    // 统一的摘要渲染  
    renderSummary(summaryText, adaptationInfo = {}) {
        return '';
        /*
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
        */
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
                    <div class="result-card mb-4">  
                        <div class="flex items-start justify-between mb-3">  
                            <h3 class="text-lg font-semibold text-gray-900">${item.title || '执行结果'}</h3>  
                            <div class="flex items-center space-x-2">  
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
                    <div class="flex justify-between items-center mb-4">  
                        <h3 class="text-lg font-semibold">${tableItem.title || '数据表格'}</h3>  
                        <div class="flex space-x-2">${actions}</div>  
                    </div>  
                    <div class="overflow-x-auto">  
                        <table class="result-table w-full border-collapse">  
                            <thead>  
                                <tr class="bg-gray-50">  
                                    ${actualColumns.map(header =>
                `<th class="border p-2 text-left font-medium">${header}</th>`
            ).join('')}  
                                </tr>  
                            </thead>  
                            <tbody>  
                                ${rows.map(row => `  
                                    <tr class="hover:bg-gray-50">  
                                        ${actualColumns.map(header =>
                `<td class="border p-2">${this.formatCellContent(row[header])}</td>`
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

    renderDashboard(data, container) {
        try {
            const dashboardItem = data.display_items[0];
            const content = dashboardItem.content || {};
            const { stats = {}, charts = [], summary = '' } = content;
            const actions = this.renderActionButtons(data.actions);

            const dashboardHtml = `  
                <div class="result-card">  
                    <div class="flex justify-between items-center mb-4">  
                        <h3 class="text-lg font-semibold">${dashboardItem.title || '数据仪表板'}</h3>  
                        <div class="flex space-x-2">${actions}</div>  
                    </div>  
                    <div class="dashboard-grid grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">  
                        ${Object.entries(stats).map(([key, value]) => `  
                            <div class="metric-card p-4 bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg">  
                                <div class="text-sm text-blue-600 font-medium">${key}</div>  
                                <div class="text-2xl font-bold text-blue-900">${this.formatMetricValue(value)}</div>  
                            </div>  
                        `).join('')}  
                    </div>  
                    ${charts.length > 0 ? this.renderCharts(charts) : ''}  
                    ${summary ? `<div class="mt-4 p-3 bg-gray-50 rounded">${summary}</div>` : ''}  
                    ${this.renderSummary(data.summary_text, data)}  
                </div>  
            `;
            container.innerHTML = dashboardHtml;
        } catch (error) {
            this.renderError(container, error, data);
        }
    }

    renderTimeline(data, container) {
        try {
            const timelineItem = data.display_items[0];
            const content = timelineItem.content || {};
            const { items = [] } = content;
            const actions = this.renderActionButtons(data.actions);

            const timelineHtml = `  
                <div class="result-card">  
                    <div class="flex justify-between items-center mb-4">  
                        <h3 class="text-lg font-semibold">${timelineItem.title || '执行时间线'}</h3>  
                        <div class="flex space-x-2">${actions}</div>  
                    </div>  
                    <div class="space-y-4">  
                        ${items.map((step, index) => `  
                            <div class="flex items-start space-x-4">  
                                <div class="flex-shrink-0 w-10 h-10 ${this.getTimelineStepColor(step.status)} rounded-full flex items-center justify-center text-sm font-medium text-white">  
                                    ${step.step || index + 1}  
                                </div>  
                                <div class="flex-1 min-w-0">  
                                    <div class="font-medium text-gray-900">${step.title}</div>  
                                    ${step.description ? `<p class="text-sm text-gray-600 mt-1">${step.description}</p>` : ''}  
                                    ${step.timestamp ? `<div class="text-xs text-gray-500 mt-1">${step.timestamp}</div>` : ''}  
                                    ${step.status ? `<div class="text-xs mt-1 px-2 py-1 rounded ${this.getStatusClass(step.status)}">${step.status}</div>` : ''}  
                                </div>  
                            </div>  
                        `).join('')}  
                    </div>  
                    ${this.renderSummary(data.summary_text, data)}  
                </div>  
            `;
            container.innerHTML = timelineHtml;
        } catch (error) {
            this.renderError(container, error, data);
        }
    }

    renderProgress(data, container) {
        try {
            const progressItem = data.display_items[0];
            const content = progressItem.content || {};
            const { current = 0, total = 100, percentage = 0, status = '' } = content;
            const actions = this.renderActionButtons(data.actions);

            const progressHtml = `  
                <div class="result-card">  
                    <div class="flex justify-between items-center mb-4">  
                        <h3 class="text-lg font-semibold">${progressItem.title || '处理进度'}</h3>  
                        <div class="flex space-x-2">${actions}</div>  
                    </div>  
                    <div class="mb-4">  
                        <div class="flex justify-between text-sm text-gray-600 mb-2">  
                            <span>${current} / ${total}</span>  
                            <span>${percentage.toFixed(1)}%</span>  
                        </div>  
                        <div class="w-full bg-gray-200 rounded-full h-3">  
                            <div class="bg-gradient-to-r from-blue-500 to-blue-600 h-3 rounded-full transition-all duration-500"   
                                 style="width: ${Math.min(percentage, 100)}%"></div>  
                        </div>  
                    </div>  
                    ${status ? `<div class="text-sm text-gray-600 mb-2">${status}</div>` : ''}  
                    ${content.eta ? `<div class="text-xs text-gray-500">预计完成时间: ${content.eta}</div>` : ''}  
                    ${this.renderSummary(data.summary_text, data)}  
                </div>  
            `;
            container.innerHTML = progressHtml;
        } catch (error) {
            this.renderError(container, error, data);
        }
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
                <div class="flex justify-between items-center mb-4">  
                    <h3 class="text-lg font-semibold">${editorItem.title || '生成的内容'}</h3>  
                    <div class="flex space-x-2">  
                        ${actions}  
                        ${!hasCopyAction ?
                    '<button class="text-sm px-3 py-1 border rounded hover:bg-gray-50" onclick="window.aiforgeApp.copyResult()">📋 复制</button>' : ''}  
                        ${!hasDownloadAction ?
                    '<button class="text-sm px-3 py-1 border rounded hover:bg-gray-50" onclick="window.aiforgeApp.downloadResult()">💾 下载</button>' : ''}  
                    </div>  
                </div>  
                  
                <div class="border rounded-lg">  
                    <div class="markdown-content p-4 max-h-96 overflow-y-auto" ${editable ? 'contenteditable="true"' : ''}>  
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
        // 移除代码块标记
        text = text.replace(/```markdown\s*\n/gi, '');
        text = text.replace(/```\s*$/gm, '');

        // 处理表格
        text = text.replace(/^\|(.*)\|\s*\n\|([-:| ]+)\|\s*\n(\|.*\|\s*\n)+/gm, (match) => {
            const rows = match.trim().split('\n');
            const headerRow = rows[0];
            const dataRows = rows.slice(2);

            const header = headerRow
                .split('|')
                .filter(cell => cell.trim() !== '')
                .map(cell => `<th class="border px-4 py-2 bg-gray-100">${cell.trim()}</th>`)
                .join('');

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

        // 处理分隔线
        text = text.replace(/^---+$/gm, '<hr class="my-4 border-gray-300">');

        // 处理引用块
        text = text.replace(/(?:^> (.+)(?:\n|$))+/gm, (match) => {
            const content = match.split('\n')
                .filter(line => line.startsWith('> '))
                .map(line => line.substring(2))
                .join('<br>');
            return `<blockquote class="border-l-4 border-gray-300 pl-4 py-2 my-4 bg-gray-50">${content}</blockquote>`;
        });

        // 处理无序列表
        text = text.replace(/(?:^- (.+)(?:\n|$))+/gm, (match) => {
            const items = match.split('\n')
                .filter(line => line.startsWith('- '))
                .map(line => `<li class="ml-4">${line.substring(2)}</li>`)
                .join('');
            return `<ul class="list-disc my-2">${items}</ul>`;
        });

        // 处理有序列表
        text = text.replace(/(?:^\d+\. (.+)(?:\n|$))+/gm, (match) => {
            const items = match.split('\n')
                .filter(line => /^\d+\. /.test(line))
                .map(line => `<li class="ml-4">${line.replace(/^\d+\. /, '')}</li>`)
                .join('');
            return `<ol class="list-decimal my-2">${items}</ol>`;
        });

        // 确保处理完所有块级元素后，再处理剩余的段落文本
        // 这个正则确保只匹配未被其他规则转换的文本行
        const lines = text.split('\n');
        const processedLines = lines.map(line => {
            const trimmedLine = line.trim();
            // 排除已处理过的标签或空行
            if (trimmedLine === '' || trimmedLine.startsWith('<') && trimmedLine.endsWith('>')) {
                return line;
            }
            // 匹配并处理段落
            return `<p class="my-2">${line}</p>`;
        });
        text = processedLines.join('\n');

        // 清理多余的换行
        text = text.replace(/\n+/g, '\n');
        text = text.replace(/(<p class="my-2">)(\s*<[^>]+>\s*)(<\/p>)/g, '$2'); // 移除包裹着块级元素的段落标签

        return text;
    }

    renderCharts(charts) {
        if (!charts || charts.length === 0) {
            return `  
            <div class="mt-4">  
                <h4 class="text-md font-medium mb-2">数据图表</h4>  
                <div class="bg-gray-100 rounded p-4 text-center text-gray-500">  
                    暂无图表数据  
                </div>  
            </div>  
        `;
        }

        return `  
        <div class="mt-4">  
            <h4 class="text-md font-medium mb-2">数据图表</h4>  
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">  
                ${charts.map((chart, index) => `  
                    <div class="bg-gray-100 rounded p-4 text-center text-gray-500">  
                        <div class="text-2xl mb-2">📊</div>  
                        <p>图表 ${index + 1}: ${chart.type || 'Unknown'}</p>  
                        <p class="text-sm mt-2">需要集成图表库 (Chart.js/D3.js)</p>  
                    </div>  
                `).join('')}  
            </div>  
        </div>  
    `;
    }
    renderList(data, container) {
        try {
            const listItem = data.display_items[0];
            const content = listItem.content || {};
            const { items = [] } = content;
            const actions = this.renderActionButtons(data.actions);

            const itemsHtml = items.map((item, index) => `  
            <div class="list-item p-3 border-b border-gray-200 last:border-b-0 hover:bg-gray-50">  
                <div class="flex items-center space-x-3">  
                    <div class="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">  
                        <span class="text-sm font-medium text-blue-600">${item.id || index + 1}</span>  
                    </div>  
                    <div class="flex-1 min-w-0">  
                        <h4 class="text-sm font-medium text-gray-900 truncate">${item.title || `项目 ${index + 1}`}</h4>  
                        ${item.subtitle ? `<p class="text-xs text-gray-500 truncate">${item.subtitle}</p>` : ''}  
                        ${item.description ? `<p class="text-xs text-gray-600 mt-1">${item.description}</p>` : ''}  
                    </div>  
                    <div class="flex-shrink-0">  
                        <span class="text-xs text-gray-400">→</span>  
                    </div>  
                </div>  
            </div>  
        `).join('');

            const listHtml = `  
            <div class="result-card">  
                <div class="flex justify-between items-center mb-4">  
                    <h3 class="text-lg font-semibold">${listItem.title || '列表数据'}</h3>  
                    <div class="flex space-x-2">${actions}</div>  
                </div>  
                <div class="bg-white rounded-lg border overflow-hidden">  
                    ${itemsHtml || '<div class="text-center text-gray-500 py-8">暂无数据</div>'}  
                </div>  
                ${this.renderSummary(data.summary_text, data)}  
            </div>  
        `;
            container.innerHTML = listHtml;
        } catch (error) {
            this.renderError(container, error, data);
        }
    }
    renderText(data, container) {
        try {
            const textItem = data.display_items[0];
            const content = textItem.content || {};
            const { text = '', format = 'plain', monospace = true } = content;
            const actions = this.renderActionButtons(data.actions);

            const textHtml = `  
            <div class="result-card">  
                <div class="flex justify-between items-center mb-4">  
                    <h3 class="text-lg font-semibold">${textItem.title || '文本输出'}</h3>  
                    <div class="flex space-x-2">${actions}</div>  
                </div>  
                <div class="bg-gray-900 text-green-400 p-4 rounded-lg ${monospace ? 'font-mono' : ''} text-sm">  
                    <div class="flex items-center mb-2">  
                        <div class="flex space-x-2">  
                            <div class="w-3 h-3 bg-red-500 rounded-full"></div>  
                            <div class="w-3 h-3 bg-yellow-500 rounded-full"></div>  
                            <div class="w-3 h-3 bg-green-500 rounded-full"></div>  
                        </div>  
                        <span class="ml-4 text-gray-400">Terminal Output</span>  
                    </div>  
                    <pre class="whitespace-pre-wrap">${text || '暂无输出'}</pre>  
                </div>  
                ${this.renderSummary(data.summary_text, data)}  
            </div>  
        `;
            container.innerHTML = textHtml;
        } catch (error) {
            this.renderError(container, error, data);
        }
    }
    renderMap(data, container) {
        try {
            const mapItems = data.display_items;
            const actions = this.renderActionButtons(data.actions);

            const mapHtml = `  
            <div class="result-card">  
                <div class="flex justify-between items-center mb-4">  
                    <h3 class="text-lg font-semibold">地图视图</h3>  
                    <div class="flex space-x-2">${actions}</div>  
                </div>  
                <div id="map-${Date.now()}" class="w-full h-96 bg-gray-100 rounded-lg">  
                    <div class="flex items-center justify-center h-full text-gray-500">  
                        <div class="text-center">  
                            <div class="text-2xl mb-2">🗺️</div>  
                            <p>地图视图 (${mapItems.length} 个位置)</p>  
                            <p class="text-sm mt-2">需要集成地图服务</p>  
                        </div>  
                    </div>  
                </div>  
                ${this.renderSummary(data.summary_text, data)}  
            </div>  
        `;
            container.innerHTML = mapHtml;
        } catch (error) {
            this.renderError(container, error, data);
        }
    }

    renderChart(data, container) {
        try {
            const chartItem = data.display_items[0];
            const content = chartItem.content || {};
            const { chart_type = 'bar', data: chartData = [], config = {} } = content;
            const actions = this.renderActionButtons(data.actions);

            const chartHtml = `  
            <div class="result-card">  
                <div class="flex justify-between items-center mb-4">  
                    <h3 class="text-lg font-semibold">${chartItem.title || '数据图表'}</h3>  
                    <div class="flex items-center space-x-2">  
                        <select class="chart-type-selector border rounded px-2 py-1 text-sm">  
                            <option value="bar" ${chart_type === 'bar' ? 'selected' : ''}>柱状图</option>  
                            <option value="line" ${chart_type === 'line' ? 'selected' : ''}>折线图</option>  
                            <option value="pie" ${chart_type === 'pie' ? 'selected' : ''}>饼图</option>  
                        </select>  
                        ${actions}  
                    </div>  
                </div>  
                <div class="chart-canvas w-full h-64 bg-gray-50 rounded flex items-center justify-center">  
                    <div class="text-center text-gray-500">  
                        <div class="text-2xl mb-2">📊</div>  
                        <p>图表渲染区域</p>  
                        <p class="text-sm mt-2">需要集成图表库 (Chart.js/D3.js)</p>  
                    </div>  
                </div>  
                ${this.renderSummary(data.summary_text, data)}  
            </div>  
        `;
            container.innerHTML = chartHtml;
        } catch (error) {
            this.renderError(container, error, data);
        }
    }

    renderGallery(data, container) {
        try {
            const galleryItems = data.display_items;
            const actions = this.renderActionButtons(data.actions);

            const itemsHtml = galleryItems.map((item, index) => `  
            <div class="gallery-item group cursor-pointer">  
                <div class="aspect-square bg-gray-100 rounded-lg overflow-hidden">  
                    ${item.image_url ?
                    `<img src="${item.image_url}" alt="Image ${index + 1}" class="w-full h-full object-cover group-hover:scale-105 transition-transform">` :
                    `<div class="w-full h-full flex items-center justify-center text-gray-400">  
                            <div class="text-center">  
                                <div class="text-2xl mb-1">🖼️</div>  
                                <p class="text-xs">图片 ${index + 1}</p>  
                            </div>  
                        </div>`
                }  
                </div>  
                ${item.metadata ? `  
                    <div class="mt-2 text-xs text-gray-600">  
                        ${Object.entries(item.metadata).map(([key, value]) =>
                    `<div>${key}: ${value}</div>`
                ).join('')}  
                    </div>  
                ` : ''}  
            </div>  
        `).join('');

            const galleryHtml = `  
            <div class="result-card">  
                <div class="flex justify-between items-center mb-4">  
                    <h3 class="text-lg font-semibold">图片画廊</h3>  
                    <div class="flex space-x-2">${actions}</div>  
                </div>  
                <div class="grid grid-cols-3 gap-4">  
                    ${itemsHtml}  
                </div>  
                ${this.renderSummary(data.summary_text, data)}  
            </div>  
        `;
            container.innerHTML = galleryHtml;
        } catch (error) {
            this.renderError(container, error, data);
        }
    }

    renderCalendar(data, container) {
        try {
            const events = data.display_items;
            const actions = this.renderActionButtons(data.actions);

            const eventsHtml = events.map((event, index) => `  
            <div class="calendar-event p-3 mb-2 bg-blue-50 rounded-lg border-l-4 border-blue-400">  
                <div class="flex justify-between items-start">  
                    <div class="flex-1">  
                        <h4 class="font-medium text-gray-900">${event.title || '事件'}</h4>  
                        ${event.description ? `<p class="text-sm text-gray-600 mt-1">${event.description}</p>` : ''}  
                    </div>  
                    <div class="text-right text-sm text-gray-500">  
                        ${event.date ? `<div>${event.date}</div>` : ''}  
                        ${event.time ? `<div>${event.time}</div>` : ''}  
                    </div>  
                </div>  
            </div>  
        `).join('');

            const calendarHtml = `  
            <div class="result-card">  
                <div class="flex justify-between items-center mb-4">  
                    <h3 class="text-lg font-semibold">日历视图</h3>  
                    <div class="flex items-center space-x-2">  
                        <button class="text-sm px-3 py-1 border rounded hover:bg-gray-50">月视图</button>  
                        <button class="text-sm px-3 py-1 border rounded hover:bg-gray-50">周视图</button>  
                        ${actions}  
                    </div>  
                </div>  
                <div class="calendar-events space-y-2">  
                    ${eventsHtml || '<div class="text-center text-gray-500 py-8">暂无事件</div>'}  
                </div>  
                ${this.renderSummary(data.summary_text, data)}  
            </div>  
        `;
            container.innerHTML = calendarHtml;
        } catch (error) {
            this.renderError(container, error, data);
        }
    }
    // 辅助方法  
    formatContent(content) {
        if (typeof content === 'string') {
            return content
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/\n/g, '<br>')
                .replace(/---/g, '<hr class="my-4 border-gray-300">');
        }
        if (typeof content === 'object' && content !== null) {
            return `<pre class="bg-gray-100 p-2 rounded text-sm overflow-auto">${JSON.stringify(content, null, 2)}</pre>`;
        }
        return String(content);
    }
    renderCardContent(content) {
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
                    if (content.secondary.metadata) {
                        html += `<div class="text-xs text-gray-400 mt-2">`;
                        Object.entries(content.secondary.metadata).forEach(([key, value]) => {
                            html += `<span class="mr-3">${key}: ${value}</span>`;
                        });
                        html += `</div>`;
                    }
                    html += `</div>`;
                } else {
                    html += `<div class="text-gray-600 text-sm">${content.secondary}</div>`;
                }
            }

            // 处理额外的内容字段  
            if (content.details) {
                html += `<div class="mt-2 text-sm text-gray-700">${content.details}</div>`;
            }

            if (content.tags && Array.isArray(content.tags)) {
                html += `<div class="mt-2 flex flex-wrap gap-1">`;
                content.tags.forEach(tag => {
                    html += `<span class="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">${tag}</span>`;
                });
                html += `</div>`;
            }

            return html;
        }
        return this.formatContent(content);
    }
    renderMetadata(metadata) {
        return '';
        /*
        const importantFields = ['summary', 'word_count', 'output_format', 'search_results_count', 'timestamp'];
        const otherFields = Object.keys(metadata).filter(key => !importantFields.includes(key));

        return `  
        <div class="mt-3 pt-3 border-t border-gray-200">  
            <div class="text-xs text-gray-500 space-y-1">  
                ${importantFields.map(key =>
            metadata[key] ? `<div><span class="font-medium">${this.formatFieldName(key)}:</span> ${this.formatFieldValue(key, metadata[key])}</div>` : ''
        ).join('')}  
                ${otherFields.length > 0 ? `  
                    <details class="mt-2">  
                        <summary class="cursor-pointer text-gray-400 hover:text-gray-600">更多信息 (${otherFields.length})</summary>  
                        <div class="mt-1 space-y-1 pl-2">  
                            ${otherFields.map(key =>
            `<div><span class="font-medium">${this.formatFieldName(key)}:</span> ${this.formatFieldValue(key, metadata[key])}</div>`
        ).join('')}  
                        </div>  
                    </details>  
                ` : ''}  
            </div>  
        </div>  
    `;
    */
    }

    formatFieldName(key) {
        const nameMap = {
            'word_count': '字数',
            'output_format': '输出格式',
            'search_results_count': '搜索结果数',
            'timestamp': '时间戳',
            'task_type': '任务类型',
            'execution_type': '执行类型',
            'content_type': '内容类型'
        };
        return nameMap[key] || key;
    }

    formatFieldValue(key, value) {
        if (key === 'timestamp' && typeof value === 'number') {
            return new Date(value * 1000).toLocaleString();
        }
        if (typeof value === 'object') {
            return JSON.stringify(value);
        }
        return String(value);
    }
    // 格式化表格单元格内容  
    formatCellContent(content) {
        if (content === null || content === undefined) {
            return '<span class="text-gray-400">-</span>';
        }
        if (typeof content === 'boolean') {
            return content ? '<span class="text-green-600">✓</span>' : '<span class="text-red-600">✗</span>';
        }
        if (typeof content === 'number') {
            return content.toLocaleString();
        }
        if (typeof content === 'string' && content.length > 50) {
            return `<span title="${content}">${content.substring(0, 47)}...</span>`;
        }
        return String(content);
    }

    // 格式化指标值  
    formatMetricValue(value) {
        if (typeof value === 'number') {
            if (value >= 1000000) {
                return (value / 1000000).toFixed(1) + 'M';
            }
            if (value >= 1000) {
                return (value / 1000).toFixed(1) + 'K';
            }
            return value.toLocaleString();
        }
        return String(value);
    }

    // 获取时间线步骤颜色  
    getTimelineStepColor(status) {
        const colorMap = {
            'completed': 'bg-green-500',
            'running': 'bg-blue-500',
            'failed': 'bg-red-500',
            'pending': 'bg-yellow-500',
            'skipped': 'bg-gray-400'
        };
        return colorMap[status] || 'bg-blue-500';
    }

    // 渲染分页控件  
    renderPagination(pagination) {
        const { current_page = 1, total_pages = 1, total_items = 0 } = pagination;

        if (total_pages <= 1) return '';

        return `  
        <div class="mt-4 flex items-center justify-between">  
            <div class="text-sm text-gray-500">  
                共 ${total_items} 条记录，第 ${current_page} / ${total_pages} 页  
            </div>  
            <div class="flex space-x-2">  
                <button class="px-3 py-1 border rounded text-sm hover:bg-gray-50"   
                        ${current_page <= 1 ? 'disabled' : ''}>上一页</button>  
                <button class="px-3 py-1 border rounded text-sm hover:bg-gray-50"  
                        ${current_page >= total_pages ? 'disabled' : ''}>下一页</button>  
            </div>  
        </div>  
    `;
    }

    // 设置可编辑内容  
    setupEditableContent(container, originalText) {
        const editableDiv = container.querySelector('[contenteditable="true"]');
        if (editableDiv) {
            let saveTimeout;
            editableDiv.addEventListener('input', () => {
                clearTimeout(saveTimeout);
                saveTimeout = setTimeout(() => {
                    const newText = editableDiv.innerText;
                    if (newText !== originalText) {
                        this.autoSaveContent(newText);
                    }
                }, 2000);
            });

            // 添加编辑提示  
            editableDiv.addEventListener('focus', () => {
                editableDiv.classList.add('ring-2', 'ring-blue-300');
            });

            editableDiv.addEventListener('blur', () => {
                editableDiv.classList.remove('ring-2', 'ring-blue-300');
            });
        }
    }

    // 自动保存内容  
    autoSaveContent(content) {
        localStorage.setItem('aiforge-draft-content', content);
        localStorage.setItem('aiforge-draft-timestamp', Date.now().toString());

        // 显示保存提示  
        const saveIndicator = document.createElement('div');
        saveIndicator.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-3 py-1 rounded text-sm z-50';
        saveIndicator.textContent = '草稿已保存';
        document.body.appendChild(saveIndicator);

        setTimeout(() => saveIndicator.remove(), 2000);
    }

    // 渲染默认视图  
    renderDefault(data, container) {
        const actions = this.renderActionButtons(data.actions);

        const defaultHtml = `  
        <div class="result-card">  
            <div class="flex justify-between items-center mb-4">  
                <h3 class="text-lg font-semibold">执行结果</h3>  
                <div class="flex space-x-2">${actions}</div>  
            </div>  
            <div class="bg-gray-50 rounded p-4">  
                <pre class="text-sm text-gray-800 whitespace-pre-wrap overflow-auto max-h-96">${JSON.stringify(data, null, 2)}</pre>  
            </div>  
            ${this.renderSummary(data.summary_text, data)}  
        </div>  
    `;
        container.innerHTML = defaultHtml;
    }

    // 渲染错误信息  
    renderError(container, error, data) {
        const errorHtml = `  
        <div class="error-container">  
            <div class="bg-red-50 border border-red-200 rounded-lg p-4">  
                <div class="flex items-center">  
                    <div class="text-red-400 text-xl mr-3">⚠️</div>  
                    <div>  
                        <h3 class="text-red-800 font-medium">渲染错误</h3>  
                        <p class="text-red-600 text-sm mt-1">${error.message}</p>  
                    </div>  
                </div>  
                <details class="mt-3">  
                    <summary class="text-red-700 text-sm cursor-pointer">查看原始数据</summary>  
                    <pre class="text-xs text-red-600 mt-2 bg-red-100 p-2 rounded overflow-auto max-h-40">${JSON.stringify(data, null, 2)}</pre>  
                </details>  
                <div class="mt-3">  
                    <button class="text-sm px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200"   
                            onclick="window.aiforgeApp.retryRender()">  
                        🔄 重试渲染  
                    </button>  
                </div>  
            </div>  
        </div>  
    `;
        container.innerHTML = errorHtml;
    }

    // 获取状态样式类  
    getStatusClass(status) {
        const statusClasses = {
            'completed': 'bg-green-100 text-green-800',
            'running': 'bg-blue-100 text-blue-800',
            'failed': 'bg-red-100 text-red-800',
            'pending': 'bg-yellow-100 text-yellow-800',
            'cancelled': 'bg-gray-100 text-gray-800',
            'skipped': 'bg-purple-100 text-purple-800'
        };
        return statusClasses[status] || 'bg-gray-100 text-gray-800';
    }

}