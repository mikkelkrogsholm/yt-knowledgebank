/**
 * ErrorBoundary Alpine.js Component
 * 
 * Graceful error handling and user-friendly error display
 */

function errorBoundary() {
    return {
        hasError: false,
        error: null,
        errorContext: '',
        retryCount: 0,
        maxRetries: 3,
        isRetrying: false,
        showDetails: false,
        errorId: null,
        
        init() {
            // Listen for global errors but filter out Alpine.js internal errors
            eventSystem.on('error', (errorData) => {
                // Skip errors that are likely from Alpine.js internal handling
                if (errorData.context === 'Global error' && 
                    (!errorData.error || errorData.error.message === 'Unknown error occurred')) {
                    return;
                }
                this.handleError(errorData.error, errorData.context);
            });
        },
        
        handleError(error, context = 'Unknown') {
            // Robust null/undefined error handling to prevent cascade failures
            if (!error) {
                console.warn(`[ErrorBoundary] ${context}: Null or undefined error - ignoring to prevent cascade`);
                return;
            }
            
            // Handle string or primitive errors that might be empty
            if (typeof error === 'string' && !error.trim()) {
                console.warn(`[ErrorBoundary] ${context}: Empty string error - ignoring to prevent cascade`);
                return;
            }
            
            // Ignore "unknown error occurred" errors from Alpine.js internal handling
            const errorMessage = this.getErrorMessage(error);
            if (errorMessage && errorMessage.includes('Unknown error occurred')) {
                console.warn(`[ErrorBoundary] ${context}: Ignoring cascade error:`, error);
                return;
            }
            
            // Additional check for global errors without meaningful content
            if (context === 'Global error' && (!errorMessage || errorMessage === 'Unknown error')) {
                console.warn(`[ErrorBoundary] ${context}: Ignoring meaningless global error:`, error);
                return;
            }
            
            this.hasError = true;
            
            // Safe error object creation with fallbacks
            try {
                if (error instanceof Error) {
                    this.error = error;
                    this.errorMessage = this.getErrorMessage(error) || 'An error occurred';
                } else {
                    // Handle non-Error objects safely
                    const errorString = this.safeStringify(error);
                    this.error = new Error(errorString);
                    this.errorMessage = errorString;
                }
            } catch (conversionError) {
                // Fallback if error object processing fails
                console.error(`[ErrorBoundary] Failed to process error object:`, conversionError);
                this.error = new Error('Error processing failed - unknown error occurred');
                this.errorMessage = 'An unknown error occurred';
            }
            
            this.errorContext = context || 'Unknown';
            this.errorId = this.generateErrorId();
            this.showDetails = false;
            
            // Safe logging
            try {
                console.error(`[ErrorBoundary] ${this.errorContext}:`, this.error);
            } catch (logError) {
                console.error(`[ErrorBoundary] Logging failed:`, logError);
            }
            
            // Safe event emission
            try {
                eventSystem.emit('errorHandled', {
                    error: this.error,
                    context: this.errorContext,
                    errorId: this.errorId,
                    component: this
                });
            } catch (emitError) {
                console.error(`[ErrorBoundary] Event emission failed:`, emitError);
            }
            
            // Safe notification display
            try {
                this.showErrorNotification();
            } catch (notificationError) {
                console.error(`[ErrorBoundary] Notification display failed:`, notificationError);
            }
        },
        
        showErrorNotification() {
            const message = this.getUserFriendlyMessage();
            eventSystem.notify(message, 'error', 8000);
        },
        
        getUserFriendlyMessage() {
            const errorMessage = this.getSafeErrorMessage();
            
            if (!errorMessage) {
                return 'An unknown error occurred';
            }
            
            // Network errors
            if (errorMessage.includes('fetch') || errorMessage.includes('Network')) {
                return 'Network connection error. Please check your internet connection.';
            }
            
            // API errors
            if (errorMessage.includes('404')) {
                return 'The requested resource was not found.';
            }
            
            if (errorMessage.includes('500')) {
                return 'Server error. Please try again in a few moments.';
            }
            
            if (errorMessage.includes('API key')) {
                return 'API key error. Please check your settings.';
            }
            
            if (errorMessage.includes('Unauthorized') || errorMessage.includes('401')) {
                return 'Authentication error. Please check your credentials.';
            }
            
            if (errorMessage.includes('timeout')) {
                return 'Request timed out. Please try again.';
            }
            
            // Permission errors
            if (errorMessage.includes('permission') || errorMessage.includes('403')) {
                return 'Permission denied. You may not have access to this resource.';
            }
            
            // Validation errors
            if (errorMessage.includes('validation') || errorMessage.includes('invalid')) {
                return 'Invalid input. Please check your data and try again.';
            }
            
            // Generic fallback
            return 'Something went wrong. Please try again.';
        },
        
        async retry() {
            if (this.retryCount >= this.maxRetries) {
                eventSystem.notify('Maximum retry attempts reached. Please refresh the page.', 'error');
                return;
            }
            
            this.isRetrying = true;
            this.retryCount++;
            
            try {
                // Wait a bit before retrying
                await new Promise(resolve => setTimeout(resolve, 1000 * this.retryCount));
                
                // Emit retry event so parent components can handle it
                eventSystem.emit('errorRetry', {
                    error: this.error,
                    context: this.errorContext,
                    retryCount: this.retryCount
                });
                
                // Clear error state
                this.clearError();
                
                eventSystem.notify('Retrying...', 'info', 2000);
                
            } catch (retryError) {
                this.handleError(retryError, `Retry attempt ${this.retryCount}`);
            } finally {
                this.isRetrying = false;
            }
        },
        
        clearError() {
            this.hasError = false;
            this.error = null;
            this.errorContext = '';
            this.retryCount = 0;
            this.isRetrying = false;
            this.showDetails = false;
            this.errorId = null;
        },
        
        toggleDetails() {
            this.showDetails = !this.showDetails;
        },
        
        reportError() {
            // Prepare error report
            const errorReport = {
                id: this.errorId,
                message: this.error?.message,
                stack: this.error?.stack,
                context: this.errorContext,
                timestamp: new Date().toISOString(),
                userAgent: navigator.userAgent,
                url: window.location.href,
                retryCount: this.retryCount
            };
            
            // Copy to clipboard
            navigator.clipboard.writeText(JSON.stringify(errorReport, null, 2)).then(() => {
                eventSystem.notify('Error report copied to clipboard', 'success');
            }).catch(() => {
                eventSystem.notify('Failed to copy error report', 'error');
            });
            
            // Emit event for potential logging service
            eventSystem.emit('errorReported', errorReport);
        },
        
        generateErrorId() {
            return `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        },
        
        /**
         * Safely extract error message from error object
         * @param {any} error - Error object or value
         * @returns {string} Safe error message
         */
        getErrorMessage(error) {
            if (!error) return '';
            
            try {
                if (typeof error === 'string') {
                    return error;
                }
                
                if (error instanceof Error) {
                    return error.message || '';
                }
                
                // Handle objects with message property
                if (error && typeof error === 'object' && error.message) {
                    return String(error.message);
                }
                
                // Handle objects with toString method
                if (error && typeof error.toString === 'function') {
                    return error.toString();
                }
                
                return String(error);
            } catch (extractionError) {
                console.warn('Error extracting message from error object:', extractionError);
                return 'Unknown error';
            }
        },
        
        /**
         * Get safe error message for display purposes
         * @returns {string} Safe error message
         */
        getSafeErrorMessage() {
            try {
                return this.errorMessage || this.getErrorMessage(this.error) || '';
            } catch (error) {
                console.warn('Error getting safe error message:', error);
                return '';
            }
        },
        
        /**
         * Safely convert any value to string
         * @param {any} value - Value to convert
         * @returns {string} Safe string representation
         */
        safeStringify(value) {
            if (value === null) return 'null';
            if (value === undefined) return 'undefined';
            
            try {
                if (typeof value === 'string') {
                    return value || 'Empty string';
                }
                
                if (typeof value === 'object') {
                    // Try JSON.stringify first
                    try {
                        return JSON.stringify(value);
                    } catch (jsonError) {
                        // Fallback to toString
                        return value.toString();
                    }
                }
                
                return String(value);
            } catch (stringifyError) {
                console.warn('Error stringifying value:', stringifyError);
                return 'Unstringifiable value';
            }
        },
        
        getErrorTitle() {
            const contextTitles = {
                'Network error': 'Connection Problem',
                'API error': 'Service Error',
                'Component initialization': 'Loading Error',
                'SearchBar component': 'Search Error',
                'Modal component': 'Display Error',
                'Loading component': 'Loading Error'
            };
            
            return contextTitles[this.errorContext] || 'Error';
        },
        
        getErrorIcon() {
            const errorMessage = this.getSafeErrorMessage();
            
            if (!errorMessage) {
                return '❌';
            }
            
            if (errorMessage.includes('Network') || errorMessage.includes('fetch')) {
                return '🌐';
            }
            
            if (errorMessage.includes('API')) {
                return '🔑';
            }
            
            if (errorMessage.includes('404')) {
                return '🔍';
            }
            
            if (errorMessage.includes('500')) {
                return '⚠️';
            }
            
            return '❌';
        },
        
        canRetry() {
            if (!this.error) return false;
            
            const errorMessage = this.getSafeErrorMessage();
            
            if (!errorMessage) return false;
            
            // Don't retry on client errors (4xx)
            if (errorMessage.includes('400') || 
                errorMessage.includes('401') || 
                errorMessage.includes('403') || 
                errorMessage.includes('404')) {
                return false;
            }
            
            // Don't retry on validation errors
            if (errorMessage.includes('validation') || errorMessage.includes('invalid')) {
                return false;
            }
            
            return this.retryCount < this.maxRetries;
        },
        
        getSuggestedActions() {
            const errorMessage = this.getSafeErrorMessage();
            const actions = [];
            
            if (!errorMessage) {
                actions.push('Try refreshing the page');
                actions.push('Contact support if the problem persists');
                return actions;
            }
            
            if (errorMessage.includes('Network') || errorMessage.includes('fetch')) {
                actions.push('Check your internet connection');
                actions.push('Try again in a few moments');
            }
            
            if (errorMessage.includes('API key')) {
                actions.push('Check your API key in Settings');
                actions.push('Verify the API key is valid');
            }
            
            if (errorMessage.includes('404')) {
                actions.push('The resource may have been moved or deleted');
                actions.push('Try refreshing the page');
            }
            
            if (errorMessage.includes('500')) {
                actions.push('This is a server issue');
                actions.push('Try again in a few minutes');
            }
            
            if (actions.length === 0) {
                actions.push('Try refreshing the page');
                actions.push('Contact support if the problem persists');
            }
            
            return actions;
        }
    };
}

// Global error boundary for the entire application
function globalErrorBoundary() {
    return {
        ...errorBoundary(),
        
        init() {
            // Call parent init
            errorBoundary().init.call(this);
            
            // Note: Global error handlers are already set up in event-system.js
            // This avoids duplicate error handling that could cause cascading errors
        }
    };
}