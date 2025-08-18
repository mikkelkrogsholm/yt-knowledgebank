/**
 * KnowledgeAPI Client
 * 
 * Comprehensive API client for YouTube Knowledge Bank backend.
 * Handles all endpoints with error handling, retry logic, and loading states.
 */

class KnowledgeAPI {
    constructor(baseURL = '') {
        this.baseURL = baseURL;
        this.loadingStates = new Map();
        this.defaultRetryAttempts = 3;
        this.defaultRetryDelay = 1000; // 1 second
        this.requestTimeout = 30000; // 30 seconds
        
        // Use fetch or injected fetch for testing
        this.fetch = this.fetch || window.fetch;
    }
    
    /**
     * Check if a specific operation is currently loading
     * @param {string} operation - Operation name to check
     * @returns {boolean} Whether the operation is loading
     */
    isLoading(operation) {
        return this.loadingStates.get(operation) || false;
    }
    
    /**
     * Set loading state for an operation
     * @param {string} operation - Operation name
     * @param {boolean} loading - Loading state
     */
    setLoading(operation, loading) {
        this.loadingStates.set(operation, loading);
        
        // Emit loading state change event
        if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('knowledgeAPI:loadingChange', {
                detail: { operation, loading }
            }));
        }
    }
    
    /**
     * Build URL with query parameters
     * @param {string} path - API path
     * @param {Object} params - Query parameters
     * @returns {string} Complete URL with parameters
     */
    buildURL(path, params = {}) {
        const url = new URL(path, this.baseURL || window.location.origin);
        
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
                url.searchParams.append(key, value);
            }
        });
        
        return url.toString();
    }
    
    /**
     * Make HTTP request with retry logic and error handling
     * @param {string} url - Request URL
     * @param {Object} options - Fetch options
     * @param {number} retryAttempts - Number of retry attempts
     * @returns {Promise<Object>} Response data
     */
    async makeRequest(url, options = {}, retryAttempts = this.defaultRetryAttempts) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.requestTimeout);
        
        const requestOptions = {
            ...options,
            signal: controller.signal,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        };
        
        try {
            const response = await this.fetch(url, requestOptions);
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(`HTTP ${response.status}: ${errorData.error || errorData.detail || 'Request failed'}`);
            }
            
            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            
            // Retry on network errors (but not on HTTP errors)
            if (retryAttempts > 0 && (error.name === 'AbortError' || error.message.includes('Network error') || error.message.includes('fetch'))) {
                await new Promise(resolve => setTimeout(resolve, this.defaultRetryDelay));
                return this.makeRequest(url, options, retryAttempts - 1);
            }
            
            throw error;
        }
    }
    
    /**
     * Search transcripts using keyword or semantic search
     * @param {string} query - Search query
     * @param {Object} options - Search options
     * @returns {Promise<Object>} Search results
     */
    async search(query, options = {}) {
        this.setLoading('search', true);
        
        try {
            const params = {
                query,
                limit: 50,
                offset: 0,
                ...options
            };
            
            const url = this.buildURL('/api/search', params);
            const result = await this.makeRequest(url);
            
            return result;
        } finally {
            this.setLoading('search', false);
        }
    }
    
    /**
     * Ask a question using RAG (Retrieval-Augmented Generation)
     * @param {string} question - Question to ask
     * @param {string|null} sessionId - Optional session ID for conversation context
     * @returns {Promise<Object>} AI-generated answer with sources
     */
    async ask(question, sessionId = null) {
        this.setLoading('ask', true);
        
        try {
            const requestBody = {
                question: question.trim()
            };
            
            if (sessionId) {
                requestBody.session_id = sessionId;
            }
            
            const url = this.buildURL('/api/ask');
            const result = await this.makeRequest(url, {
                method: 'POST',
                body: JSON.stringify(requestBody)
            });
            
            return result;
        } finally {
            this.setLoading('ask', false);
        }
    }
    
    /**
     * Get Q&A conversation history for a session
     * @param {string} sessionId - Session ID
     * @param {number} limit - Number of exchanges to return
     * @param {number} offset - Number of exchanges to skip
     * @returns {Promise<Object>} Conversation history
     */
    async getQAHistory(sessionId, limit = 20, offset = 0) {
        this.setLoading('qa_history', true);
        
        try {
            const params = {
                session_id: sessionId,
                limit,
                offset
            };
            
            const url = this.buildURL('/api/qa/history', params);
            const result = await this.makeRequest(url);
            
            return result;
        } finally {
            this.setLoading('qa_history', false);
        }
    }
    
    /**
     * Get list of Q&A sessions
     * @param {string|null} userId - Optional user ID filter
     * @param {number} limit - Number of sessions to return
     * @param {number} offset - Number of sessions to skip
     * @returns {Promise<Object>} Sessions list
     */
    async getQASessions(userId = null, limit = 20, offset = 0) {
        this.setLoading('qa_sessions', true);
        
        try {
            const params = { limit, offset };
            if (userId) {
                params.user_id = userId;
            }
            
            const url = this.buildURL('/api/qa/sessions', params);
            const result = await this.makeRequest(url);
            
            return result;
        } finally {
            this.setLoading('qa_sessions', false);
        }
    }
    
    /**
     * Submit feedback for a Q&A exchange
     * @param {string} exchangeId - Exchange ID to provide feedback for
     * @param {number} rating - Rating (1-5)
     * @param {string|null} feedbackText - Optional feedback text
     * @param {string|null} feedbackType - Optional feedback type
     * @returns {Promise<Object>} Feedback submission result
     */
    async submitFeedback(exchangeId, rating, feedbackText = null, feedbackType = null) {
        this.setLoading('submit_feedback', true);
        
        try {
            const requestBody = {
                exchange_id: exchangeId,
                rating
            };
            
            if (feedbackText) {
                requestBody.feedback_text = feedbackText;
            }
            
            if (feedbackType) {
                requestBody.feedback_type = feedbackType;
            }
            
            const url = this.buildURL('/api/qa/feedback');
            const result = await this.makeRequest(url, {
                method: 'POST',
                body: JSON.stringify(requestBody)
            });
            
            return result;
        } finally {
            this.setLoading('submit_feedback', false);
        }
    }
    
    /**
     * Get search statistics
     * @returns {Promise<Object>} Search performance statistics
     */
    async getSearchStats() {
        this.setLoading('search_stats', true);
        
        try {
            const url = this.buildURL('/api/search/stats');
            const result = await this.makeRequest(url);
            
            return result;
        } finally {
            this.setLoading('search_stats', false);
        }
    }
    
    /**
     * Process a new YouTube video
     * @param {string} youtubeUrl - YouTube video URL
     * @returns {Promise<Object>} Processing task information
     */
    async processVideo(youtubeUrl) {
        this.setLoading('process_video', true);
        
        try {
            const url = this.buildURL('/process');
            const formData = new FormData();
            formData.append('youtube_url', youtubeUrl);
            
            const result = await this.makeRequest(url, {
                method: 'POST',
                body: formData,
                headers: {} // Let browser set Content-Type for FormData
            });
            
            return result;
        } finally {
            this.setLoading('process_video', false);
        }
    }
    
    /**
     * Get processing progress for a task
     * @param {string} taskId - Task ID
     * @returns {Promise<Object>} Processing progress
     */
    async getProgress(taskId) {
        const url = this.buildURL(`/progress/${taskId}`);
        return this.makeRequest(url);
    }
    
    /**
     * Get final result for a completed task
     * @param {string} taskId - Task ID
     * @returns {Promise<Object>} Task result
     */
    async getResult(taskId) {
        const url = this.buildURL(`/result/${taskId}`);
        return this.makeRequest(url);
    }
    
    /**
     * Get migration status
     * @returns {Promise<Object>} Migration status information
     */
    async getMigrationStatus() {
        this.setLoading('migration_status', true);
        
        try {
            const url = this.buildURL('/api/migration/status');
            const result = await this.makeRequest(url);
            
            return result;
        } finally {
            this.setLoading('migration_status', false);
        }
    }
    
    /**
     * Run database migration
     * @returns {Promise<Object>} Migration result
     */
    async runMigration() {
        this.setLoading('run_migration', true);
        
        try {
            const url = this.buildURL('/api/migration/run');
            const result = await this.makeRequest(url, {
                method: 'POST'
            });
            
            return result;
        } finally {
            this.setLoading('run_migration', false);
        }
    }
    
    /**
     * Validate API keys
     * @param {string} keyType - Type of key ('elevenlabs' or 'openai')
     * @param {string} apiKey - API key to validate
     * @returns {Promise<Object>} Validation result
     */
    async validateAPIKey(keyType, apiKey) {
        this.setLoading('validate_api_key', true);
        
        try {
            const url = this.buildURL(`/settings/validate-${keyType}`);
            const formData = new FormData();
            formData.append(keyType === 'elevenlabs' ? 'api_key' : 'openai_api_key', apiKey);
            
            const result = await this.makeRequest(url, {
                method: 'POST',
                body: formData,
                headers: {} // Let browser set Content-Type for FormData
            });
            
            return result;
        } finally {
            this.setLoading('validate_api_key', false);
        }
    }
    
    // Future endpoints for entities, topics, and summaries
    // These will be implemented when the backend endpoints are added
    
    /**
     * Get entities for a video or all videos
     * @param {string|null} videoId - Optional video ID filter
     * @returns {Promise<Object>} Entities list
     */
    async getEntities(videoId = null) {
        this.setLoading('entities', true);
        
        try {
            const params = {};
            if (videoId) {
                params.video_id = videoId;
            }
            
            const url = this.buildURL('/api/entities', params);
            const result = await this.makeRequest(url);
            
            return result;
        } finally {
            this.setLoading('entities', false);
        }
    }
    
    /**
     * Get topics for videos
     * @param {string|null} videoId - Optional video ID filter
     * @returns {Promise<Object>} Topics list
     */
    async getTopics(videoId = null) {
        this.setLoading('topics', true);
        
        try {
            const params = {};
            if (videoId) {
                params.video_id = videoId;
            }
            
            const url = this.buildURL('/api/topics', params);
            const result = await this.makeRequest(url);
            
            return result;
        } finally {
            this.setLoading('topics', false);
        }
    }
    
    /**
     * Get summaries for a video or all videos
     * @param {string|null} videoId - Optional video ID filter
     * @returns {Promise<Object>} Summaries list
     */
    async getSummaries(videoId = null) {
        this.setLoading('summaries', true);
        
        try {
            const params = {};
            if (videoId) {
                params.video_id = videoId;
            }
            
            const url = this.buildURL('/api/summaries', params);
            const result = await this.makeRequest(url);
            
            return result;
        } finally {
            this.setLoading('summaries', false);
        }
    }
}

// Export for both browser and Node.js environments
if (typeof window !== 'undefined') {
    window.KnowledgeAPI = KnowledgeAPI;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = KnowledgeAPI;
}