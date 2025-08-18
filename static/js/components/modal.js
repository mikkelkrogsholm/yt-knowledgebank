/**
 * Modal Alpine.js Component
 * 
 * Flexible modal system for detailed views and dialogs
 */

function modal() {
    return {
        isOpen: false,
        type: 'default', // 'default', 'entity', 'topic', 'video', 'confirm', 'form'
        data: {},
        size: 'md', // 'sm', 'md', 'lg', 'xl', 'full'
        closable: true,
        loading: false,
        
        init() {
            // Listen for global modal events
            eventSystem.on('showModal', (modalData) => {
                this.show(modalData);
            });
            
            eventSystem.on('hideModal', () => {
                this.hide();
            });
            
            eventSystem.on('escape', () => {
                if (this.isOpen && this.closable) {
                    this.hide();
                }
            });
        },
        
        show(modalData = {}) {
            this.type = modalData.type || 'default';
            this.data = modalData.data || {};
            this.size = modalData.size || 'md';
            this.closable = modalData.closable !== false;
            this.loading = false;
            
            this.isOpen = true;
            
            // Prevent body scroll
            document.body.style.overflow = 'hidden';
            
            // Focus management
            this.$nextTick(() => {
                const firstFocusable = this.$el.querySelector('[data-modal-focus]') || 
                                      this.$el.querySelector('button, input, textarea, select, a[href]');
                if (firstFocusable) {
                    firstFocusable.focus();
                }
            });
            
            eventSystem.emit('modalOpened', { type: this.type, data: this.data });
        },
        
        hide() {
            if (!this.closable) return;
            
            this.isOpen = false;
            
            // Restore body scroll
            document.body.style.overflow = '';
            
            eventSystem.emit('modalClosed', { type: this.type, data: this.data });
        },
        
        handleBackdropClick(event) {
            if (event.target === event.currentTarget && this.closable) {
                this.hide();
            }
        },
        
        handleKeydown(event) {
            if (!this.isOpen) return;
            
            switch (event.key) {
                case 'Escape':
                    if (this.closable) {
                        event.preventDefault();
                        this.hide();
                    }
                    break;
                    
                case 'Tab':
                    this.trapFocus(event);
                    break;
            }
        },
        
        trapFocus(event) {
            const focusableElements = this.$el.querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            
            const firstElement = focusableElements[0];
            const lastElement = focusableElements[focusableElements.length - 1];
            
            if (event.shiftKey) {
                if (document.activeElement === firstElement) {
                    event.preventDefault();
                    lastElement.focus();
                }
            } else {
                if (document.activeElement === lastElement) {
                    event.preventDefault();
                    firstElement.focus();
                }
            }
        },
        
        getTitle() {
            switch (this.type) {
                case 'entity':
                    return this.data.name || 'Entity Details';
                case 'topic':
                    return this.data.name || 'Topic Details';
                case 'video':
                    return this.data.title || 'Video Details';
                case 'confirm':
                    return this.data.title || 'Confirm Action';
                case 'form':
                    return this.data.title || 'Form';
                default:
                    return this.data.title || 'Details';
            }
        },
        
        getContent() {
            switch (this.type) {
                case 'entity':
                    return this.renderEntityContent();
                case 'topic':
                    return this.renderTopicContent();
                case 'video':
                    return this.renderVideoContent();
                case 'confirm':
                    return this.renderConfirmContent();
                case 'form':
                    return this.renderFormContent();
                default:
                    return this.data.content || '';
            }
        },
        
        renderEntityContent() {
            const entity = this.data;
            return `
                <div class="space-y-4">
                    <div class="flex items-center space-x-3">
                        <span class="text-2xl">${this.getEntityIcon(entity.type)}</span>
                        <div>
                            <h3 class="font-semibold text-lg">${entity.name}</h3>
                            <p class="text-gray-600">${this.capitalizeFirst(entity.type)}</p>
                        </div>
                    </div>
                    
                    ${entity.description ? `
                        <div>
                            <h4 class="font-medium mb-2">Description</h4>
                            <p class="text-gray-700">${entity.description}</p>
                        </div>
                    ` : ''}
                    
                    <div class="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <span class="font-medium">Mentions:</span>
                            <span class="ml-1">${entity.mention_count || 0}</span>
                        </div>
                        <div>
                            <span class="font-medium">Videos:</span>
                            <span class="ml-1">${entity.video_count || 0}</span>
                        </div>
                    </div>
                    
                    ${entity.confidence_score ? `
                        <div class="text-sm">
                            <span class="font-medium">Confidence:</span>
                            <span class="ml-1">${Math.round(entity.confidence_score * 100)}%</span>
                        </div>
                    ` : ''}
                </div>
            `;
        },
        
        renderTopicContent() {
            const topic = this.data;
            return `
                <div class="space-y-4">
                    <div class="flex items-center space-x-3">
                        <span class="text-2xl">🏷️</span>
                        <div>
                            <h3 class="font-semibold text-lg">${topic.name}</h3>
                            <p class="text-gray-600">Topic Weight: ${this.formatWeight(topic.weight)}</p>
                        </div>
                    </div>
                    
                    ${topic.description ? `
                        <div>
                            <h4 class="font-medium mb-2">Description</h4>
                            <p class="text-gray-700">${topic.description}</p>
                        </div>
                    ` : ''}
                    
                    <div class="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <span class="font-medium">Videos:</span>
                            <span class="ml-1">${topic.video_count || 0}</span>
                        </div>
                        <div>
                            <span class="font-medium">Weight:</span>
                            <span class="ml-1">${this.formatWeight(topic.weight)}</span>
                        </div>
                    </div>
                    
                    ${topic.keywords && topic.keywords.length > 0 ? `
                        <div>
                            <h4 class="font-medium mb-2">Keywords</h4>
                            <div class="flex flex-wrap gap-2">
                                ${topic.keywords.map(keyword => 
                                    `<span class="px-2 py-1 bg-gray-100 text-gray-700 rounded text-sm">${keyword}</span>`
                                ).join('')}
                            </div>
                        </div>
                    ` : ''}
                </div>
            `;
        },
        
        renderVideoContent() {
            const video = this.data;
            return `
                <div class="space-y-4">
                    ${video.thumbnail_url ? `
                        <img src="${video.thumbnail_url}" alt="${video.title}" 
                             class="w-full h-48 object-cover rounded">
                    ` : ''}
                    
                    <div>
                        <h3 class="font-semibold text-lg mb-2">${video.title}</h3>
                        ${video.description ? `
                            <p class="text-gray-700">${video.description}</p>
                        ` : ''}
                    </div>
                    
                    <div class="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <span class="font-medium">Duration:</span>
                            <span class="ml-1">${this.formatDuration(video.duration_seconds)}</span>
                        </div>
                        <div>
                            <span class="font-medium">Processed:</span>
                            <span class="ml-1">${this.formatDate(video.processed_at)}</span>
                        </div>
                    </div>
                </div>
            `;
        },
        
        renderConfirmContent() {
            return `
                <div class="text-center">
                    <p class="text-gray-700 mb-6">${this.data.message || 'Are you sure?'}</p>
                    <div class="flex justify-center space-x-3">
                        <button @click="handleConfirm" 
                                class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors">
                            ${this.data.confirmText || 'Confirm'}
                        </button>
                        <button @click="hide" 
                                class="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 transition-colors">
                            ${this.data.cancelText || 'Cancel'}
                        </button>
                    </div>
                </div>
            `;
        },
        
        renderFormContent() {
            // This would be populated with dynamic form content
            return this.data.formHTML || '<p>Form content goes here</p>';
        },
        
        handleConfirm() {
            if (this.data.onConfirm) {
                this.data.onConfirm();
            }
            
            eventSystem.emit('modalConfirmed', { type: this.type, data: this.data });
            this.hide();
        },
        
        getSizeClasses() {
            const sizeMap = {
                sm: 'max-w-md',
                md: 'max-w-lg',
                lg: 'max-w-2xl',
                xl: 'max-w-4xl',
                full: 'max-w-full mx-4'
            };
            
            return sizeMap[this.size] || sizeMap.md;
        },
        
        getEntityIcon(type) {
            const iconMap = {
                person: '👤',
                organization: '🏢',
                book: '📚',
                concept: '💡',
                place: '📍',
                event: '📅'
            };
            
            return iconMap[type] || '🏷️';
        },
        
        formatWeight(weight) {
            if (typeof weight !== 'number') return '0%';
            return `${Math.round(weight * 100)}%`;
        },
        
        formatDuration(seconds) {
            if (!seconds) return '0:00';
            
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = Math.floor(seconds % 60);
            
            if (hours > 0) {
                return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
            }
            
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        },
        
        formatDate(dateString) {
            if (!dateString) return '';
            
            const date = new Date(dateString);
            return date.toLocaleDateString();
        },
        
        capitalizeFirst(str) {
            if (!str) return '';
            return str.charAt(0).toUpperCase() + str.slice(1);
        }
    };
}