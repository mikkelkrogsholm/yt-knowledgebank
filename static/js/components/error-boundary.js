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
            // Ignore null/undefined errors and "unknown error occurred" errors
            // that come from Alpine.js internal handling to prevent cascading error dialogs
            if (!error || 
                (error.message && error.message.includes('Unknown error occurred')) ||
                (context === 'Global error' && !error.message)) {
                console.warn('Ignoring cascade error:', error, context);
                return;
            }
            
            this.hasError = true;
            
            // Handle errors properly
            if (error instanceof Error) {
                this.error = error;
                this.errorMessage = error.message || 'Error occurred';
            } else {
                this.error = new Error(String(error));
                this.errorMessage = String(error);
            }
            
            this.errorContext = context;
            this.errorId = this.generateErrorId();
            this.showDetails = false;
            
            // Log error for debugging
            console.error(`[ErrorBoundary] ${context}:`, this.error);
            
            // Emit error handled event
            eventSystem.emit('errorHandled', {
                error: this.error,
                context,
                errorId: this.errorId,
                component: this
            });
            
            // Show user notification
            this.showErrorNotification();
        },
        
        showErrorNotification() {
            const message = this.getUserFriendlyMessage();
            eventSystem.notify(message, 'error', 8000);
        },
        
        getUserFriendlyMessage() {
            if (!this.error) return 'An unknown error occurred';
            
            const errorMessage = this.errorMessage || this.error?.message || '';
            
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
            const errorMessage = this.error?.message || '';
            
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
            
            const errorMessage = this.errorMessage || this.error?.message || '';
            
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
            if (!this.error) return [];
            
            const errorMessage = this.errorMessage || this.error?.message || '';
            const actions = [];
            
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