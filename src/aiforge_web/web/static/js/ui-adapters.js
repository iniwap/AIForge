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
        const adapter = this.adapters[uiType] || this.adapters['default'];
        return adapter(data, container);
    }

    renderCard(data, container) {
        try {
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

            container.innerHTML = cardsHtml + summaryHtml;
        } catch (error) {
            this.renderError(container, error, data);
        }
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
                    html += `</div>`;
                } else {
                    html += `<div class="text-gray-600 text-sm">${content.secondary}</div>`;
                }
            }
            return html;
        }
        return this.formatContent(content);
    }

    renderTable(data, container) {
        try {
            const tableItem = data.display_items[0];
            const { columns, rows } = tableItem.content;

            const tableHtml = `  
                <div class="result-card">  
                    <h3 class="text-lg font-semibold mb-4">${tableItem.title || '数据表格'}</h3>  
                    <div class="overflow-x-auto">  
                        <table class="result-table">  
                            <thead>  
                                <tr>  
                                    ${columns.map(header => `<th>${header}</th>`).join('')}  
                                </tr>  
                            </thead>  
                            <tbody>  
                                ${rows.map(row => `  
                                    <tr>  
                                        ${columns.map(header => `<td>${row[header] || '-'}</td>`).join('')}  
                                    </tr>  
                                `).join('')}  
                            </tbody>  
                        </table>  
                    </div>  
                    ${data.summary_text ? `<p class="mt-2 text-sm text-gray-600">${data.summary_text}</p>` : ''}  
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
            const { stats, charts, summary } = dashboardItem.content;

            const dashboardHtml = `  
                <div class="result-card">  
                    <h3 class="text-lg font-semibold mb-4">${dashboardItem.title || '数据仪表板'}</h3>  
                    <div class="dashboard-grid">  
                        ${Object.entries(stats || {}).map(([key, value]) => `  
                            <div class="metric-card">  
                                <div class="text-sm opacity-90">${key}</div>  
                                <div class="text-2xl font-bold">${value}</div>  
                            </div>  
                        `).join('')}  
                    </div>  
                    ${charts ? this.renderCharts(charts) : ''}  
                    ${summary ? `<div class="mt-4 p-3 bg-gray-50 rounded">${summary}</div>` : ''}  
                    ${data.summary_text ? `<p class="mt-2 text-sm text-gray-600">${data.summary_text}</p>` : ''}  
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
            const { items } = timelineItem.content;

            const timelineHtml = `  
                <div class="result-card">  
                    <h3 class="text-lg font-semibold mb-4">${timelineItem.title || '执行时间线'}</h3>  
                    <div class="space-y-3">  
                        ${items.map((step, index) => `  
                            <div class="flex items-start space-x-3">  
                                <div class="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-sm font-medium text-blue-600">  
                                    ${step.step || index + 1}  
                                </div>  
                                <div class="flex-1">  
                                    <div class="font-medium text-gray-900">${step.title}</div>  
                                    ${step.timestamp ? `<div class="text-sm text-gray-500 mt-1">${step.timestamp}</div>` : ''}  
                                    ${step.status ? `<div class="text-xs mt-1 px-2 py-1 rounded ${this.getStatusClass(step.status)}">${step.status}</div>` : ''}  
                                </div>  
                            </div>  
                        `).join('')}  
                    </div>  
                    ${data.summary_text ? `<p class="mt-2 text-sm text-gray-600">${data.summary_text}</p>` : ''}  
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
            const { current, total, percentage, status } = progressItem.content;

            const progressHtml = `  
                <div class="result-card">  
                    <h3 class="text-lg font-semibold mb-4">${progressItem.title || '处理进度'}</h3>  
                    <div class="mb-4">  
                        <div class="flex justify-between text-sm text-gray-600 mb-2">  
                            <span>${current || 0} / ${total || 0}</span>  
                            <span>${(percentage || 0).toFixed(1)}%</span>  
                        </div>  
                        <div class="w-full bg-gray-200 rounded-full h-2">  
                            <div class="bg-blue-600 h-2 rounded-full transition-all duration-300" style="width: ${percentage || 0}%"></div>  
                        </div>  
                    </div>  
                    ${status ? `<div class="text-sm text-gray-600">${status}</div>` : ''}  
                    ${data.summary_text ? `<p class="mt-2 text-sm text-gray-600">${data.summary_text}</p>` : ''}  
                </div>  
            `;
            container.innerHTML = progressHtml;
        } catch (error) {
            this.renderError(container, error, data);
        }
    }

    renderEditor(data, container) {
        try {
            const editorItem = data.display_items[0];
            const { text, format, metadata, editable } = editorItem.content;
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
                        <div class="markdown-content p-4 max-h-96 overflow-y-auto">  
                            ${format === 'markdown' ? this.renderMarkdown(text) : this.formatContent(text)}  
                        </div>  
                        <textarea class="hidden" id="markdownSource">${text}</textarea>  
                    </div>  
                    ${metadata ? this.renderMetadata(metadata) : ''}  
                    ${data.summary_text ? `<p class="mt-2 text-sm text-gray-600">${data.summary_text}</p>` : ''}  
                </div>  
            `;
            container.innerHTML = editorHtml;
        } catch (error) {
            this.renderError(container, error, data);
        }
    }

    renderList(data, container) {
        try {
            const listItem = data.display_items[0];
            const { items } = listItem.content;

            const itemsHtml = items.map((item, index) => `  
                <div class="list-item p-3 border-b border-gray-200 last:border-b-0">  
                    <div class="flex items-center space-x-3">  
                        <div class="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">  
                            <span class="text-sm font-medium text-blue-600">${item.id || index + 1}</span>  
                        </div>  
                        <div class="flex-1 min-w-0">  
                            <h4 class="text-sm font-medium text-gray-900 truncate">${item.title}</h4>  
                            ${item.subtitle ? `<p class="text-xs text-gray-500 truncate">${item.subtitle}</p>` : ''}  
                        </div>  
                        <div class="flex-shrink-0">  
                            <span class="text-xs text-gray-400">→</span>  
                        </div>  
                    </div>  
                </div>  
            `).join('');

            const listHtml = `  
                <div class="list-container">  
                    <div class="bg-white rounded-lg border overflow-hidden">  
                        ${itemsHtml || '<div class="text-center text-gray-500 py-8">暂无数据</div>'}  
                    </div>  
                    ${data.summary_text ? `<p class="mt-2 text-sm text-gray-600">${data.summary_text}</p>` : ''}  
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
            const { text, format, monospace } = textItem.content;

            const terminalHtml = `  
                <div class="terminal-container">  
                    <div class="bg-gray-900 text-green-400 p-4 rounded-lg ${monospace ? 'font-mono' : ''} text-sm">  
                        <div class="flex items-center mb-2">  
                            <div class="flex space-x-2">  
                                <div class="w-3 h-3 bg-red-500 rounded-full"></div>  
                                <div class="w-3 h-3 bg-yellow-500 rounded-full"></div>  
                                <div class="w-3 h-3 bg-green-500 rounded-full"></div>  
                            </div>  
                            <span class="ml-4 text-gray-400">${textItem.title || 'Terminal Output'}</span>  
                        </div>  
                        <pre class="whitespace-pre-wrap">${text || '暂无输出'}</pre>  
                    </div>  
                    ${data.summary_text ? `<p class="mt-2 text-sm text-gray-600">${data.summary_text}</p>` : ''}  
                </div>  
            `;
            container.innerHTML = terminalHtml;
        } catch (error) {
            this.renderError(container, error, data);
        }
    }
    renderMap(data, container) {
        try {
            const mapItems = data.display_items;
            const mapHtml = `  
            <div class="map-container">  
                <div id="map-${Date.now()}" class="w-full h-96 bg-gray-100 rounded-lg">  
                    <div class="flex items-center justify-center h-full text-gray-500">  
                        <div class="text-center">  
                            <div class="text-2xl mb-2">🗺️</div>  
                            <p>地图视图 (${mapItems.length} 个位置)</p>  
                            <p class="text-sm mt-2">需要集成地图服务</p>  
                        </div>  
                    </div>  
                </div>  
                ${data.summary_text ? `<p class="mt-2 text-sm text-gray-600">${data.summary_text}</p>` : ''}  
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
            const { chart_type, data: chartData, config } = chartItem;

            const chartHtml = `  
            <div class="chart-container">  
                <div class="bg-white p-4 rounded-lg border">  
                    <div class="flex justify-between items-center mb-4">  
                        <h3 class="text-lg font-semibold">${chart_type.toUpperCase()} 图表</h3>  
                        <div class="text-sm text-gray-500">  
                            <select class="chart-type-selector border rounded px-2 py-1">  
                                <option value="bar" ${chart_type === 'bar' ? 'selected' : ''}>柱状图</option>  
                                <option value="line" ${chart_type === 'line' ? 'selected' : ''}>折线图</option>  
                                <option value="pie" ${chart_type === 'pie' ? 'selected' : ''}>饼图</option>  
                            </select>  
                        </div>  
                    </div>  
                    <div class="chart-canvas w-full h-64 bg-gray-50 rounded flex items-center justify-center">  
                        <div class="text-center text-gray-500">  
                            <div class="text-2xl mb-2">📊</div>  
                            <p>图表渲染区域</p>  
                            <p class="text-sm mt-2">需要集成图表库 (Chart.js/D3.js)</p>  
                        </div>  
                    </div>  
                </div>  
                ${data.summary_text ? `<p class="mt-2 text-sm text-gray-600">${data.summary_text}</p>` : ''}  
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
            <div class="gallery-container">  
                <div class="grid grid-cols-3 gap-4">  
                    ${itemsHtml}  
                </div>  
                ${data.summary_text ? `<p class="mt-4 text-sm text-gray-600">${data.summary_text}</p>` : ''}  
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
            <div class="calendar-container">  
                <div class="bg-white p-4 rounded-lg border">  
                    <div class="flex justify-between items-center mb-4">  
                        <h3 class="text-lg font-semibold">日历视图</h3>  
                        <div class="flex space-x-2">  
                            <button class="text-sm px-3 py-1 border rounded hover:bg-gray-50">月视图</button>  
                            <button class="text-sm px-3 py-1 border rounded hover:bg-gray-50">周视图</button>  
                        </div>  
                    </div>  
                    <div class="calendar-events space-y-2">  
                        ${eventsHtml || '<div class="text-center text-gray-500 py-8">暂无事件</div>'}  
                    </div>  
                </div>  
                ${data.summary_text ? `<p class="mt-2 text-sm text-gray-600">${data.summary_text}</p>` : ''}  
            </div>  
        `;
            container.innerHTML = calendarHtml;
        } catch (error) {
            this.renderError(container, error, data);
        }
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
                    <pre class="text-xs text-red-600 mt-2 bg-red-100 p-2 rounded overflow-auto">${JSON.stringify(data, null, 2)}</pre>  
                </details>  
            </div>  
        </div>  
    `;
        container.innerHTML = errorHtml;
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

    renderMarkdown(text) {
        return text
            .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold mb-4">$1</h1>')
            .replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold mb-3">$1</h2>')
            .replace(/^### (.*$)/gim, '<h3 class="text-lg font-medium mb-2">$1</h3>')
            .replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/gim, '<em>$1</em>')
            .replace(/^- (.*$)/gim, '<li class="ml-4">$1</li>')
            .replace(/\n/gim, '<br>');
    }

    renderCharts(charts) {
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