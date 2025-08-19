/**
 * Event System & State Management
 * 
 * Global event dispatcher and state management for component communication.
 * Provides keyboard shortcuts, error boundaries, and shared state.
 */

class EventSystem {
    constructor() {
        this.events = new Map();
        this.globalState = new Map();
        this.keyboardShortcuts = new Map();
        this.errorHandlers = [];
        
        this.initializeKeyboardShortcuts();
        this.initializeErrorHandling();
    }
    
    /**
     * Subscribe to an event
     * @param {string} eventName - Name of the event
     * @param {Function} handler - Event handler function
     * @returns {Function} Unsubscribe function
     */
    on(eventName, handler) {
        if (!this.events.has(eventName)) {
            this.events.set(eventName, new Set());
        }
        
        this.events.get(eventName).add(handler);
        
        // Return unsubscribe function
        return () => {
            this.events.get(eventName)?.delete(handler);
        };
    }
    
    /**
     * Subscribe to an event that will only fire once
     * @param {string} eventName - Name of the event
     * @param {Function} handler - Event handler function
     * @returns {Function} Unsubscribe function
     */
    once(eventName, handler) {
        const wrappedHandler = (...args) => {
            handler(...args);
            this.off(eventName, wrappedHandler);
        };
        
        return this.on(eventName, wrappedHandler);
    }
    
    /**
     * Unsubscribe from an event
     * @param {string} eventName - Name of the event
     * @param {Function} handler - Event handler function to remove
     */
    off(eventName, handler) {
        this.events.get(eventName)?.delete(handler);
    }
    
    /**
     * Emit an event to all subscribers
     * @param {string} eventName - Name of the event
     * @param {...any} args - Arguments to pass to handlers
     */
    emit(eventName, ...args) {
        const handlers = this.events.get(eventName);
        if (handlers) {
            handlers.forEach(handler => {
                try {
                    handler(...args);
                } catch (error) {
                    this.handleError(error, `Event handler for '${eventName}'`);
                }
            });
        }
    }
    
    /**
     * Set global state value
     * @param {string} key - State key
     * @param {any} value - State value
     */
    setState(key, value) {
        const oldValue = this.globalState.get(key);
        this.globalState.set(key, value);
        
        // Emit state change event
        this.emit('stateChange', { key, value, oldValue });
        this.emit(`stateChange:${key}`, value, oldValue);
    }
    
    /**
     * Get global state value
     * @param {string} key - State key
     * @param {any} defaultValue - Default value if key doesn't exist
     * @returns {any} State value
     */
    getState(key, defaultValue = undefined) {
        return this.globalState.has(key) ? this.globalState.get(key) : defaultValue;
    }
    
    /**
     * Remove global state value
     * @param {string} key - State key
     */
    removeState(key) {
        const oldValue = this.globalState.get(key);
        this.globalState.delete(key);
        
        this.emit('stateChange', { key, value: undefined, oldValue });
        this.emit(`stateChange:${key}`, undefined, oldValue);
    }
    
    /**
     * Register a keyboard shortcut
     * @param {string} key - Key combination (e.g., 'ctrl+k', '/', 'escape')
     * @param {Function} handler - Handler function
     * @param {Object} options - Options (preventDefault, target, etc.)
     */
    registerShortcut(key, handler, options = {}) {
        const normalizedKey = this.normalizeKey(key);
        
        if (!this.keyboardShortcuts.has(normalizedKey)) {
            this.keyboardShortcuts.set(normalizedKey, []);
        }
        
        this.keyboardShortcuts.get(normalizedKey).push({
            handler,
            options: {
                preventDefault: true,
                target: document,
                ...options
            }
        });
    }
    
    /**
     * Unregister a keyboard shortcut
     * @param {string} key - Key combination
     * @param {Function} handler - Handler function to remove
     */
    unregisterShortcut(key, handler) {
        const normalizedKey = this.normalizeKey(key);
        const shortcuts = this.keyboardShortcuts.get(normalizedKey);
        
        if (shortcuts) {
            const index = shortcuts.findIndex(s => s.handler === handler);
            if (index >= 0) {
                shortcuts.splice(index, 1);
            }
        }
    }
    
    /**
     * Register error handler
     * @param {Function} handler - Error handler function
     */
    onError(handler) {
        this.errorHandlers.push(handler);
    }
    
    /**
     * Handle errors with graceful fallbacks
     * @param {Error} error - Error object
     * @param {string} context - Context where error occurred
     */
    handleError(error, context = 'Unknown') {
        // Handle null/undefined errors gracefully - but don't emit error events for them
        // as this can cause cascading error dialogs
        if (!error) {
            console.warn(`[${context}]`, 'Null or undefined error - ignoring to prevent cascade');
            return;
        }
        
        console.error(`[${context}]`, error);
        
        // Emit error event with safe error object
        this.emit('error', { 
            error: error instanceof Error ? error : new Error(String(error)), 
            context 
        });
        
        // Call registered error handlers
        this.errorHandlers.forEach(handler => {
            try {
                handler(error, context);
            } catch (handlerError) {
                console.error('Error handler failed:', handlerError);
            }
        });
    }
    
    /**
     * Show user-friendly notification
     * @param {string} message - Notification message
     * @param {string} type - Notification type (success, error, warning, info)
     * @param {number} duration - Duration in milliseconds
     */
    notify(message, type = 'info', duration = 5000) {
        this.emit('notification', { message, type, duration });
    }
    
    /**
     * Initialize keyboard shortcuts system
     */
    initializeKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            const key = this.getKeyFromEvent(event);
            const shortcuts = this.keyboardShortcuts.get(key);
            
            if (shortcuts) {
                shortcuts.forEach(({ handler, options }) => {
                    // Check if target matches (if specified)
                    if (options.target && options.target !== event.target && !options.target.contains(event.target)) {
                        return;
                    }
                    
                    // Check if we should ignore input elements
                    if (options.ignoreInput !== false && this.isInputElement(event.target)) {
                        return;
                    }
                    
                    if (options.preventDefault) {
                        event.preventDefault();
                    }
                    
                    try {
                        handler(event);
                    } catch (error) {
                        this.handleError(error, `Keyboard shortcut '${key}'`);
                    }
                });
            }
        });
    }
    
    /**
     * Initialize error handling system
     */
    initializeErrorHandling() {
        // Global error handler with proper null checks
        window.addEventListener('error', (event) => {
            // Only handle real errors, ignore null/undefined errors from Alpine.js internal handling
            if (event.error && event.error instanceof Error) {
                this.handleError(event.error, 'Global error');
            }
        });
        
        // Unhandled promise rejection handler  
        window.addEventListener('unhandledrejection', (event) => {
            // Only handle real rejections
            if (event.reason) {
                this.handleError(event.reason, 'Unhandled promise rejection');
            }
        });
        
        // Default error handler for notifications
        this.onError((error, context) => {
            // Show user-friendly error notification
            let message = 'An error occurred';
            
            if (error.message.includes('Network')) {
                message = 'Network error. Please check your connection.';
            } else if (error.message.includes('404')) {
                message = 'Resource not found.';
            } else if (error.message.includes('500')) {
                message = 'Server error. Please try again later.';
            } else if (error.message.includes('API key')) {
                message = 'API key error. Please check your settings.';
            }
            
            this.notify(message, 'error');
        });
    }
    
    /**
     * Normalize key string for consistent matching
     * @param {string} key - Key combination string
     * @returns {string} Normalized key string
     */
    normalizeKey(key) {
        return key.toLowerCase().replace(/\s+/g, '');
    }
    
    /**
     * Get key string from keyboard event
     * @param {KeyboardEvent} event - Keyboard event
     * @returns {string} Key string
     */
    getKeyFromEvent(event) {
        const parts = [];
        
        if (event.ctrlKey) parts.push('ctrl');
        if (event.metaKey) parts.push('meta');
        if (event.altKey) parts.push('alt');
        if (event.shiftKey) parts.push('shift');
        
        let key = event.key.toLowerCase();
        
        // Handle special keys
        if (key === ' ') key = 'space';
        if (key === 'arrowup') key = 'up';
        if (key === 'arrowdown') key = 'down';
        if (key === 'arrowleft') key = 'left';
        if (key === 'arrowright') key = 'right';
        
        parts.push(key);
        
        return parts.join('+');
    }
    
    /**
     * Check if element is an input element
     * @param {Element} element - DOM element
     * @returns {boolean} Whether element is an input
     */
    isInputElement(element) {
        const tagName = element.tagName.toLowerCase();
        const inputTypes = ['input', 'textarea', 'select'];
        const contentEditable = element.contentEditable === 'true';
        
        return inputTypes.includes(tagName) || contentEditable;
    }
    
    /**
     * Debounce function calls
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @returns {Function} Debounced function
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    /**
     * Throttle function calls
     * @param {Function} func - Function to throttle
     * @param {number} limit - Time limit in milliseconds
     * @returns {Function} Throttled function
     */
    throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
}

// Global event system instance
const eventSystem = new EventSystem();

// Register common keyboard shortcuts
eventSystem.registerShortcut('/', (event) => {
    // Focus search bar
    const searchInput = document.querySelector('[data-search-input]');
    if (searchInput) {
        searchInput.focus();
        event.preventDefault();
    }
});

eventSystem.registerShortcut('escape', (event) => {
    // Close modals, clear search, etc.
    eventSystem.emit('escape');
});

eventSystem.registerShortcut('ctrl+k', (event) => {
    // Quick search/command palette
    eventSystem.emit('quickSearch');
});

eventSystem.registerShortcut('ctrl+/', (event) => {
    // Show keyboard shortcuts help
    eventSystem.emit('showHelp');
});

// Export for both browser and Node.js environments
if (typeof window !== 'undefined') {
    window.EventSystem = EventSystem;
    window.eventSystem = eventSystem;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { EventSystem, eventSystem };
}