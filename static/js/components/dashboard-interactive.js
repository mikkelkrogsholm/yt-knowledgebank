/**
 * Dashboard Interactive Elements
 * 
 * Provides interactive functionality for the Knowledge Dashboard:
 * - Auto-refresh system
 * - Drag-and-drop URL processing  
 * - Keyboard shortcuts
 * - Export functionality
 */

// Dashboard Auto-Refresh System
function dashboardAutoRefresh() {
    return {
        interval: 30000, // 30 seconds default
        timerId: null,
        isActive: false,
        onRefresh: null,
        
        start() {
            if (this.isActive) return;
            
            this.isActive = true;
            this.timerId = setInterval(() => {
                if (this.onRefresh && typeof this.onRefresh === 'function') {
                    this.onRefresh();
                }
            }, this.interval);
            
            console.log('Dashboard auto-refresh started');
        },
        
        stop() {
            if (!this.isActive) return;
            
            this.isActive = false;
            if (this.timerId) {
                clearInterval(this.timerId);
                this.timerId = null;
            }
            
            console.log('Dashboard auto-refresh stopped');
        },
        
        setInterval(ms) {
            this.interval = ms;
            if (this.isActive) {
                this.stop();
                this.start();
            }
        },
        
        // Manual refresh trigger
        refresh() {
            if (this.onRefresh && typeof this.onRefresh === 'function') {
                this.onRefresh();
            }
        }
    };
}

// Drag-and-Drop URL Processor
function dragDropProcessor() {
    return {
        dropZone: null,
        overlay: null,
        onProcess: null,
        
        init() {
            this.createDropZone();
            this.setupEventListeners();
        },
        
        createDropZone() {
            // Create overlay for visual feedback
            this.overlay = document.createElement('div');
            this.overlay.id = 'drop-overlay';
            this.overlay.className = 'fixed inset-0 bg-primary-500 bg-opacity-20 backdrop-blur-sm z-50 hidden items-center justify-center';
            this.overlay.innerHTML = `
                <div class="bg-white dark:bg-gray-800 rounded-xl p-8 shadow-xl border-2 border-dashed border-primary-400 max-w-md mx-4">
                    <div class="text-center">
                        <div class="text-4xl mb-4">📎</div>
                        <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">Drop YouTube URL Here</h3>
                        <p class="text-gray-600 dark:text-gray-400">Release to start processing the video</p>
                    </div>
                </div>
            `;
            document.body.appendChild(this.overlay);
            
            // Use document body as drop zone
            this.dropZone = document.body;
        },
        
        setupEventListeners() {
            let dragCounter = 0;
            
            // Prevent default drag behaviors
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                this.dropZone.addEventListener(eventName, this.preventDefaults, false);
                document.body.addEventListener(eventName, this.preventDefaults, false);
            });
            
            // Highlight drop zone when item is dragged over it
            ['dragenter', 'dragover'].forEach(eventName => {
                this.dropZone.addEventListener(eventName, () => {
                    if (eventName === 'dragenter') dragCounter++;
                    this.highlight();
                }, false);
            });
            
            ['dragleave', 'drop'].forEach(eventName => {
                this.dropZone.addEventListener(eventName, () => {
                    if (eventName === 'dragleave') dragCounter--;
                    if (dragCounter === 0) {
                        this.unhighlight();
                    }
                }, false);
            });
            
            // Handle dropped files
            this.dropZone.addEventListener('drop', (e) => {
                dragCounter = 0;
                this.handleDrop(e);
            }, false);
        },
        
        preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        },
        
        highlight() {
            this.overlay.classList.remove('hidden');
            this.overlay.classList.add('flex');
        },
        
        unhighlight() {
            this.overlay.classList.add('hidden');
            this.overlay.classList.remove('flex');
        },
        
        async handleDrop(e) {
            this.unhighlight();
            
            const dt = e.dataTransfer;
            const url = dt.getData('text/plain') || dt.getData('text/uri-list');
            
            if (this.isYouTubeURL(url)) {
                if (this.onProcess && typeof this.onProcess === 'function') {
                    this.onProcess(url);
                } else {
                    // Default: navigate to process page with URL
                    window.location.href = `/process?url=${encodeURIComponent(url)}`;
                }
            } else {
                // Show error notification
                eventSystem.emit('notification', {
                    type: 'error',
                    title: 'Invalid URL',
                    message: 'Please drop a valid YouTube URL'
                });
            }
        },
        
        isYouTubeURL(url) {
            if (!url) return false;
            
            const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/;
            return youtubeRegex.test(url);
        },
        
        destroy() {
            if (this.overlay && this.overlay.parentNode) {
                this.overlay.parentNode.removeChild(this.overlay);
            }
        }
    };
}

// Dashboard Keyboard Shortcuts
function dashboardShortcuts() {
    return {
        shortcuts: new Map(),
        isActive: false,
        onAction: null,
        
        init() {
            this.registerDefaultShortcuts();
            this.setupEventListeners();
            this.isActive = true;
        },
        
        registerDefaultShortcuts() {
            // Register dashboard-specific shortcuts
            this.shortcuts.set('ctrl+n', 'new-question');
            this.shortcuts.set('ctrl+k', 'focus-search');
            this.shortcuts.set('ctrl+r', 'refresh-dashboard');
            this.shortcuts.set('ctrl+e', 'export-dashboard');
            this.shortcuts.set('ctrl+h', 'show-help');
            this.shortcuts.set('1', 'switch-to-question');
            this.shortcuts.set('2', 'switch-to-search');
            this.shortcuts.set('3', 'switch-to-browse');
        },
        
        setupEventListeners() {
            document.addEventListener('keydown', this.handleKeydown.bind(this));
        },
        
        handleKeydown(e) {
            if (!this.isActive) return;
            
            // Don't interfere with input elements
            if (eventSystem.isInputElement(e.target)) return;
            
            const key = this.getKeyCombo(e);
            const action = this.shortcuts.get(key);
            
            if (action) {
                e.preventDefault();
                this.executeAction(action, e);
            }
        },
        
        getKeyCombo(e) {
            const parts = [];
            
            if (e.ctrlKey) parts.push('ctrl');
            if (e.altKey) parts.push('alt');
            if (e.shiftKey) parts.push('shift');
            if (e.metaKey) parts.push('meta');
            
            parts.push(e.key.toLowerCase());
            
            return parts.join('+');
        },
        
        executeAction(action, e) {
            if (this.onAction && typeof this.onAction === 'function') {
                this.onAction(action);
                return;
            }
            
            // Default action handlers
            switch (action) {
                case 'new-question':
                    this.focusSearchBar();
                    break;
                case 'focus-search':
                    this.focusSearchBar();
                    break;
                case 'refresh-dashboard':
                    eventSystem.emit('dashboard:refresh');
                    break;
                case 'export-dashboard':
                    this.exportDashboard();
                    break;
                case 'show-help':
                    this.showHelpModal();
                    break;
                case 'switch-to-question':
                    this.switchSearchType('question');
                    break;
                case 'switch-to-search':
                    this.switchSearchType('search');
                    break;
                case 'switch-to-browse':
                    this.switchSearchType('browse');
                    break;
            }
        },
        
        focusSearchBar() {
            const searchInput = document.querySelector('[x-data*="askAnythingBar"] input[type="text"]');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        },
        
        switchSearchType(type) {
            // Emit event to switch search type
            eventSystem.emit('dashboard:switchSearchType', type);
        },
        
        exportDashboard() {
            const exporter = dashboardExporter();
            exporter.exportDashboard();
        },
        
        showHelpModal() {
            eventSystem.emit('showModal', {
                type: 'help',
                data: {
                    title: 'Keyboard Shortcuts',
                    shortcuts: [
                        { key: 'Ctrl+N', action: 'New question' },
                        { key: 'Ctrl+K', action: 'Focus search' },
                        { key: 'Ctrl+R', action: 'Refresh dashboard' },
                        { key: 'Ctrl+E', action: 'Export dashboard' },
                        { key: '1, 2, 3', action: 'Switch search type' },
                        { key: '/', action: 'Focus search (global)' },
                        { key: 'Esc', action: 'Close modals' }
                    ]
                }
            });
        },
        
        addShortcut(key, action) {
            this.shortcuts.set(key, action);
        },
        
        removeShortcut(key) {
            this.shortcuts.delete(key);
        },
        
        destroy() {
            this.isActive = false;
            document.removeEventListener('keydown', this.handleKeydown.bind(this));
        }
    };
}

// Dashboard Export Functionality
function dashboardExporter() {
    return {
        async exportDashboard() {
            try {
                const data = await this.collectDashboardData();
                const options = await this.showExportOptions();
                
                switch (options.format) {
                    case 'json':
                        this.exportToJSON(data, options.filename);
                        break;
                    case 'csv':
                        this.exportToCSV(data, options.filename);
                        break;
                    case 'pdf':
                        this.exportToPDF(data, options.filename);
                        break;
                }
                
                eventSystem.emit('notification', {
                    type: 'success',
                    title: 'Export Complete',
                    message: `Dashboard data exported as ${options.format.toUpperCase()}`
                });
                
            } catch (error) {
                console.error('Export failed:', error);
                eventSystem.emit('notification', {
                    type: 'error',
                    title: 'Export Failed',
                    message: 'Failed to export dashboard data'
                });
            }
        },
        
        async collectDashboardData() {
            // Collect data from all dashboard components
            const api = new KnowledgeAPI();
            
            const [stats, summaries, topics, entities, activity] = await Promise.all([
                api.getKnowledgeStats().catch(() => ({})),
                api.getSummaries({ limit: 10 }).catch(() => ({ summaries: [] })),
                api.getTopicTrends({ limit: 10 }).catch(() => ({ topics: [] })),
                api.getEntityHighlights({ limit: 10 }).catch(() => ({ entities: [] })),
                api.getRecentActivity({ limit: 20 }).catch(() => ({ activities: [] }))
            ]);
            
            return {
                exported_at: new Date().toISOString(),
                stats,
                summaries: summaries.summaries,
                topics: topics.topics,
                entities: entities.entities,
                activity: activity.activities
            };
        },
        
        async showExportOptions() {
            // Return default options for now
            // In a full implementation, this would show a modal
            return {
                format: 'json',
                filename: `knowledge-dashboard-${new Date().toISOString().slice(0, 10)}`
            };
        },
        
        exportToJSON(data, filename) {
            const jsonString = JSON.stringify(data, null, 2);
            this.downloadFile(jsonString, `${filename}.json`, 'application/json');
            return jsonString;
        },
        
        exportToCSV(data, filename) {
            // Convert key metrics to CSV format
            const csvLines = [
                'Category,Metric,Value',
                `Stats,Total Videos,${data.stats.total_videos || 0}`,
                `Stats,Total Hours,${data.stats.total_hours || 0}`,
                `Stats,Entities Discovered,${data.stats.entities_discovered || 0}`,
                `Stats,Topics Identified,${data.stats.topics_identified || 0}`,
                '',
                'Recent Summaries,Title,Created At'
            ];
            
            // Add summaries
            if (data.summaries) {
                data.summaries.forEach(summary => {
                    csvLines.push(`Summary,"${summary.title}",${summary.created_at}`);
                });
            }
            
            const csvString = csvLines.join('\n');
            this.downloadFile(csvString, `${filename}.csv`, 'text/csv');
            return csvString;
        },
        
        async exportToPDF(data, filename) {
            // For now, create a simple HTML report and print
            const htmlReport = this.generateHTMLReport(data);
            
            const printWindow = window.open('', '_blank');
            printWindow.document.write(htmlReport);
            printWindow.document.close();
            printWindow.print();
            
            return htmlReport;
        },
        
        generateHTMLReport(data) {
            return `
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Knowledge Dashboard Report</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; }
                        .header { border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
                        .section { margin-bottom: 30px; }
                        .stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
                        .stat-box { border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
                        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
                        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                        th { background-color: #f2f2f2; }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>Knowledge Dashboard Report</h1>
                        <p>Generated: ${new Date().toLocaleString()}</p>
                    </div>
                    
                    <div class="section">
                        <h2>Knowledge Statistics</h2>
                        <div class="stats-grid">
                            <div class="stat-box">
                                <h3>Videos</h3>
                                <p>${data.stats.total_videos || 0}</p>
                            </div>
                            <div class="stat-box">
                                <h3>Total Hours</h3>
                                <p>${data.stats.total_hours || 0}</p>
                            </div>
                            <div class="stat-box">
                                <h3>Entities</h3>
                                <p>${data.stats.entities_discovered || 0}</p>
                            </div>
                            <div class="stat-box">
                                <h3>Topics</h3>
                                <p>${data.stats.topics_identified || 0}</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>Recent Summaries</h2>
                        <table>
                            <tr><th>Title</th><th>Created</th></tr>
                            ${(data.summaries || []).map(s => `<tr><td>${s.title}</td><td>${new Date(s.created_at).toLocaleDateString()}</td></tr>`).join('')}
                        </table>
                    </div>
                    
                    <div class="section">
                        <h2>Top Topics</h2>
                        <table>
                            <tr><th>Topic</th><th>Frequency</th><th>Trend</th></tr>
                            ${(data.topics || []).map(t => `<tr><td>${t.name}</td><td>${t.frequency}</td><td>${t.trend}</td></tr>`).join('')}
                        </table>
                    </div>
                </body>
                </html>
            `;
        },
        
        downloadFile(content, filename, mimeType) {
            const blob = new Blob([content], { type: mimeType });
            const url = URL.createObjectURL(blob);
            
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            URL.revokeObjectURL(url);
        }
    };
}

// Register all interactive components globally
if (typeof window !== 'undefined') {
    window.dashboardAutoRefresh = dashboardAutoRefresh;
    window.dragDropProcessor = dragDropProcessor;
    window.dashboardShortcuts = dashboardShortcuts;
    window.dashboardExporter = dashboardExporter;
}