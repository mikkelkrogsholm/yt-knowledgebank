/**
 * Ask Anything Bar Component
 * 
 * Main search/question interface for the Knowledge Dashboard
 * Handles question asking, content search, and topic browsing
 */

function askAnythingBar() {
    return {
        // State
        query: '',
        searchType: 'question', // 'question', 'search', 'browse'
        isLoading: false,
        lastResponse: null,
        suggestions: [],
        
        // API client
        api: null,
        
        // Session management
        currentSessionId: null,
        
        init() {
            // Initialize KnowledgeAPI client
            this.api = new KnowledgeAPI();
            
            // Load suggestions based on available content
            this.loadSuggestions();
            
            // Set up event listeners
            eventSystem.on('dashboard:refresh', () => {
                this.loadSuggestions();
            });
            
            // Focus on input when slash is pressed globally
            eventSystem.registerShortcut('/', (e) => {
                e.preventDefault();
                const input = this.$el.querySelector('input[type="text"]');
                if (input) {
                    input.focus();
                }
            });
            
            // Handle ctrl+enter for quick submit
            eventSystem.registerShortcut('ctrl+enter', () => {
                if (this.query.trim()) {
                    this.handleSubmit();
                }
            });
        },
        
        setSearchType(type) {
            this.searchType = type;
            this.query = '';
            this.lastResponse = null;
            this.loadSuggestions();
        },
        
        getPlaceholder() {
            switch (this.searchType) {
                case 'question':
                    return 'Ask anything about your videos... (e.g., "What productivity tips are mentioned?")';
                case 'search':
                    return 'Search across all video content... (e.g., "atomic habits morning routine")';
                case 'browse':
                    return 'Browse topics and entities... (e.g., "productivity", "Tim Ferriss")';
                default:
                    return 'Ask anything...';
            }
        },
        
        getButtonText() {
            switch (this.searchType) {
                case 'question':
                    return 'Ask';
                case 'search':
                    return 'Search';
                case 'browse':
                    return 'Browse';
                default:
                    return 'Submit';
            }
        },
        
        async loadSuggestions() {
            try {
                let suggestions = [];
                
                switch (this.searchType) {
                    case 'question':
                        suggestions = await this.loadQuestionSuggestions();
                        break;
                    case 'search':
                        suggestions = await this.loadSearchSuggestions();
                        break;
                    case 'browse':
                        suggestions = await this.loadBrowseSuggestions();
                        break;
                }
                
                this.suggestions = suggestions;
            } catch (error) {
                console.error('Failed to load suggestions:', error);
                this.suggestions = this.getDefaultSuggestions();
            }
        },
        
        async loadQuestionSuggestions() {
            // Load popular questions and content-based suggestions
            try {
                const response = await this.api.getPopularQuestions();
                const contentSuggestions = await this.api.getContentSuggestions();
                
                return [
                    ...response.questions.slice(0, 3),
                    ...contentSuggestions.suggestions.slice(0, 2)
                ];
            } catch (error) {
                return [
                    'What topics are discussed most in my videos?',
                    'Who are the main speakers or guests?',
                    'What books or resources are mentioned?',
                    'Show me recent insights and summaries'
                ];
            }
        },
        
        async loadSearchSuggestions() {
            // Load recent searches and popular terms
            try {
                const response = await this.api.getSearchSuggestions();
                return response.suggestions.slice(0, 5);
            } catch (error) {
                return [
                    'productivity tips',
                    'learning strategies',
                    'morning routine',
                    'time management',
                    'habit formation'
                ];
            }
        },
        
        async loadBrowseSuggestions() {
            // Load popular topics and entities
            try {
                const [topics, entities] = await Promise.all([
                    this.api.getPopularTopics(),
                    this.api.getPopularEntities()
                ]);
                
                return [
                    ...topics.topics.slice(0, 3).map(t => t.name),
                    ...entities.entities.slice(0, 2).map(e => e.name)
                ];
            } catch (error) {
                return [
                    'Productivity',
                    'Learning',
                    'Health',
                    'Tim Ferriss',
                    'Atomic Habits'
                ];
            }
        },
        
        getDefaultSuggestions() {
            return [
                'What are the main themes in my videos?',
                'Show me productivity tips',
                'Who are the most mentioned people?',
                'Find content about learning'
            ];
        },
        
        selectSuggestion(suggestion) {
            this.query = suggestion;
            this.handleSubmit();
        },
        
        async handleSubmit() {
            if (!this.query.trim() || this.isLoading) return;
            
            this.isLoading = true;
            this.lastResponse = null;
            
            try {
                let response;
                
                switch (this.searchType) {
                    case 'question':
                        response = await this.handleQuestion();
                        break;
                    case 'search':
                        response = await this.handleSearch();
                        break;
                    case 'browse':
                        response = await this.handleBrowse();
                        break;
                }
                
                this.lastResponse = response;
                
                // Emit event for analytics
                eventSystem.emit('dashboard:query', {
                    type: this.searchType,
                    query: this.query,
                    hasResults: response && (response.answer || response.results?.length > 0)
                });
                
            } catch (error) {
                eventSystem.handleError(error, 'Ask Anything Bar');
                this.lastResponse = {
                    error: true,
                    message: 'Sorry, I encountered an error while processing your request. Please try again.'
                };
            } finally {
                this.isLoading = false;
            }
        },
        
        async handleQuestion() {
            const response = await this.api.ask(this.query, this.currentSessionId);
            
            // Store session ID for follow-up questions
            if (response.session_id) {
                this.currentSessionId = response.session_id;
            }
            
            return response;
        },
        
        async handleSearch() {
            const response = await this.api.search(this.query, {
                limit: 20
            });
            
            // Transform search results into a response format
            return {
                query: this.query,
                answer: this.formatSearchResults(response),
                sources: response.results.map(result => ({
                    video_id: result.video_id,
                    title: result.video_title || `Video ${result.video_id}`,
                    start_ms: result.start_ms,
                    text: result.text,
                    highlighted_text: result.highlighted_text,
                    rank: result.rank
                })),
                total_found: response.total_found,
                response_time_ms: response.query_time_ms
            };
        },
        
        async handleBrowse() {
            // Try to match query with topics or entities first
            const [topicMatch, entityMatch] = await Promise.all([
                this.api.findTopic(this.query).catch(() => null),
                this.api.findEntity(this.query).catch(() => null)
            ]);
            
            if (topicMatch) {
                return this.formatTopicBrowse(topicMatch);
            } else if (entityMatch) {
                return this.formatEntityBrowse(entityMatch);
            } else {
                // Fall back to general search
                return this.handleSearch();
            }
        },
        
        formatSearchResults(response) {
            if (response.total_found === 0) {
                return `<p>No results found for "<strong>${this.query}</strong>". Try different keywords or check your spelling.</p>`;
            }
            
            const topResults = response.results.slice(0, 5);
            let html = `<p>Found <strong>${response.total_found}</strong> results for "<strong>${this.query}</strong>":</p><ul class="mt-3 space-y-2">`;
            
            topResults.forEach(result => {
                html += `<li class="border-l-2 border-primary-200 pl-3">
                    <div class="text-sm">${result.highlighted_text || result.text}</div>
                    <div class="text-xs text-gray-500">Score: ${this.formatRelevanceScore(result.rank)}%</div>
                </li>`;
            });
            
            html += '</ul>';
            
            if (response.has_more) {
                html += `<p class="mt-3 text-sm text-gray-600">And ${response.total_found - topResults.length} more results available.</p>`;
            }
            
            return html;
        },
        
        formatTopicBrowse(topic) {
            return {
                answer: `<h3>Topic: ${topic.name}</h3>
                    <p>Found in <strong>${topic.video_count}</strong> videos with <strong>${topic.mention_count}</strong> total mentions.</p>
                    <p>${topic.description || 'No description available.'}</p>`,
                sources: topic.recent_mentions || [],
                confidence_score: 1.0,
                response_time_ms: 50
            };
        },
        
        formatEntityBrowse(entity) {
            return {
                answer: `<h3>${entity.name}</h3>
                    <p><strong>Type:</strong> ${entity.type}</p>
                    <p>Mentioned <strong>${entity.mention_count}</strong> times across <strong>${entity.video_count}</strong> videos.</p>
                    <p>${entity.description || 'No description available.'}</p>`,
                sources: entity.recent_mentions || [],
                confidence_score: 1.0,
                response_time_ms: 50
            };
        },
        
        formatTimestamp(ms) {
            const seconds = Math.floor(ms / 1000);
            const minutes = Math.floor(seconds / 60);
            const hours = Math.floor(minutes / 60);
            
            if (hours > 0) {
                return `${hours}:${String(minutes % 60).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
            } else {
                return `${minutes}:${String(seconds % 60).padStart(2, '0')}`;
            }
        },
        
        formatRelevanceScore(rank) {
            // Convert FTS5 BM25 rank (negative value, closer to 0 = better match) 
            // to positive percentage (higher = better match)
            // FTS5 ranks typically range from 0 to -5 or lower
            
            if (!rank || rank === 0) return 100;
            
            // Since rank is negative, we need to convert it to a positive scale
            // Better matches have ranks closer to 0 (like -0.001)
            // Worse matches have more negative ranks (like -4.5)
            
            // Use exponential decay to convert negative rank to percentage
            // This ensures better matches (closer to 0) get higher percentages
            const normalizedScore = Math.max(0, Math.min(100, Math.exp(rank) * 100));
            
            return Math.round(normalizedScore);
        },
        
        jumpToVideo(videoId, startMs) {
            // Navigate to video page with timestamp
            const url = `/video/${videoId}?t=${Math.floor(startMs / 1000)}`;
            window.open(url, '_blank');
        },
        
        // Helper methods for event handling
        wait(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }
    };
}

// Register component globally
if (typeof window !== 'undefined') {
    window.askAnythingBar = askAnythingBar;
}