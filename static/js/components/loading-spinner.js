/**
 * LoadingSpinner Alpine.js Component
 * 
 * Loading indicators with skeleton states and progress tracking
 */

function loadingSpinner() {
    return {
        type: 'spinner', // 'spinner', 'skeleton', 'progress', 'dots'
        size: 'md', // 'sm', 'md', 'lg'
        message: '',
        progress: 0, // 0-100 for progress bars
        isVisible: false,
        color: 'blue', // 'blue', 'gray', 'green', 'red'
        
        init() {
            // Listen for loading state changes from API
            eventSystem.on('knowledgeAPI:loadingChange', (event) => {
                if (this.shouldShowForOperation(event.detail.operation)) {
                    this.isVisible = event.detail.loading;
                    this.message = this.getMessageForOperation(event.detail.operation);
                }
            });
            
            // Listen for progress updates
            eventSystem.on('progressUpdate', (data) => {
                this.progress = data.progress || 0;
                this.message = data.message || this.message;
            });
        },
        
        show(options = {}) {
            this.type = options.type || 'spinner';
            this.size = options.size || 'md';
            this.message = options.message || '';
            this.progress = options.progress || 0;
            this.color = options.color || 'blue';
            this.isVisible = true;
        },
        
        hide() {
            this.isVisible = false;
            this.progress = 0;
            this.message = '';
        },
        
        setProgress(value, message = null) {
            this.progress = Math.max(0, Math.min(100, value));
            if (message !== null) {
                this.message = message;
            }
        },
        
        shouldShowForOperation(operation) {
            // Override in component instances to control which operations trigger loading
            return this.operation === operation || this.operation === 'all';
        },
        
        getMessageForOperation(operation) {
            const messages = {
                search: 'Searching...',
                ask: 'Generating answer...',
                qa_history: 'Loading history...',
                qa_sessions: 'Loading sessions...',
                submit_feedback: 'Submitting feedback...',
                process_video: 'Processing video...',
                entities: 'Loading entities...',
                topics: 'Loading topics...',
                summaries: 'Loading summaries...',
                search_stats: 'Loading statistics...',
                migration_status: 'Checking migration status...',
                run_migration: 'Running migration...',
                validate_api_key: 'Validating API key...'
            };
            
            return messages[operation] || 'Loading...';
        },
        
        getSizeClasses() {
            const sizeMap = {
                sm: 'w-4 h-4',
                md: 'w-6 h-6',
                lg: 'w-8 h-8'
            };
            
            return sizeMap[this.size] || sizeMap.md;
        },
        
        getColorClasses() {
            const colorMap = {
                blue: 'text-blue-600',
                gray: 'text-gray-600',
                green: 'text-green-600',
                red: 'text-red-600'
            };
            
            return colorMap[this.color] || colorMap.blue;
        },
        
        getProgressBarClasses() {
            const colorMap = {
                blue: 'bg-blue-600',
                gray: 'bg-gray-600',
                green: 'bg-green-600',
                red: 'bg-red-600'
            };
            
            return colorMap[this.color] || colorMap.blue;
        },
        
        renderSpinner() {
            return `
                <svg class="${this.getSizeClasses()} ${this.getColorClasses()} animate-spin" 
                     fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" 
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
            `;
        },
        
        renderSkeleton() {
            // Different skeleton patterns based on context
            return `
                <div class="animate-pulse space-y-3">
                    <div class="h-4 bg-gray-200 rounded w-3/4"></div>
                    <div class="h-4 bg-gray-200 rounded w-1/2"></div>
                    <div class="h-4 bg-gray-200 rounded w-2/3"></div>
                </div>
            `;
        },
        
        renderProgress() {
            return `
                <div class="w-full">
                    <div class="flex justify-between text-sm text-gray-600 mb-1">
                        <span>${this.message}</span>
                        <span>${Math.round(this.progress)}%</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2">
                        <div class="${this.getProgressBarClasses()} h-2 rounded-full transition-all duration-300" 
                             style="width: ${this.progress}%"></div>
                    </div>
                </div>
            `;
        },
        
        renderDots() {
            return `
                <div class="flex space-x-1">
                    <div class="w-2 h-2 ${this.getColorClasses()} rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                    <div class="w-2 h-2 ${this.getColorClasses()} rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                    <div class="w-2 h-2 ${this.getColorClasses()} rounded-full animate-bounce" style="animation-delay: 300ms"></div>
                </div>
            `;
        },
        
        getContent() {
            switch (this.type) {
                case 'spinner':
                    return this.renderSpinner();
                case 'skeleton':
                    return this.renderSkeleton();
                case 'progress':
                    return this.renderProgress();
                case 'dots':
                    return this.renderDots();
                default:
                    return this.renderSpinner();
            }
        }
    };
}

// Skeleton loading component for specific UI elements
function skeletonLoader() {
    return {
        type: 'card', // 'card', 'list', 'text', 'image'
        count: 1,
        
        renderCard() {
            return `
                <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                    <div class="animate-pulse">
                        <div class="flex space-x-4">
                            <div class="rounded bg-gray-200 h-12 w-12"></div>
                            <div class="flex-1 space-y-2">
                                <div class="h-4 bg-gray-200 rounded w-3/4"></div>
                                <div class="h-4 bg-gray-200 rounded w-1/2"></div>
                            </div>
                        </div>
                        <div class="mt-4 space-y-2">
                            <div class="h-3 bg-gray-200 rounded"></div>
                            <div class="h-3 bg-gray-200 rounded w-5/6"></div>
                        </div>
                    </div>
                </div>
            `;
        },
        
        renderList() {
            return `
                <div class="space-y-3">
                    ${Array.from({ length: this.count }, () => `
                        <div class="animate-pulse flex space-x-3">
                            <div class="rounded-full bg-gray-200 h-8 w-8"></div>
                            <div class="flex-1 space-y-2">
                                <div class="h-3 bg-gray-200 rounded w-1/4"></div>
                                <div class="h-3 bg-gray-200 rounded w-1/2"></div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        },
        
        renderText() {
            return `
                <div class="animate-pulse space-y-2">
                    ${Array.from({ length: this.count }, () => `
                        <div class="h-4 bg-gray-200 rounded w-full"></div>
                    `).join('')}
                </div>
            `;
        },
        
        renderImage() {
            return `
                <div class="animate-pulse">
                    <div class="bg-gray-200 rounded h-48 w-full"></div>
                </div>
            `;
        },
        
        getContent() {
            switch (this.type) {
                case 'card':
                    return Array.from({ length: this.count }, () => this.renderCard()).join('');
                case 'list':
                    return this.renderList();
                case 'text':
                    return this.renderText();
                case 'image':
                    return this.renderImage();
                default:
                    return this.renderCard();
            }
        }
    };
}