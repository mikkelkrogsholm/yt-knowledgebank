/**
 * SearchBar Alpine.js Component
 * 
 * Real-time search with suggestions and keyboard navigation
 */

function searchBar() {
    return {
        query: '',
        suggestions: [],
        isOpen: false,
        loading: false,
        selectedIndex: -1,
        api: null,
        searchType: 'semantic', // 'semantic', 'keyword', 'hybrid'
        
        init() {
            this.api = new KnowledgeAPI();
            
            // Listen for global search events
            eventSystem.on('quickSearch', () => {
                this.$refs.input.focus();
            });
            
            eventSystem.on('escape', () => {
                this.closeSuggestions();
            });
            
            // Debounced search function
            this.debouncedSearch = eventSystem.debounce(this.performSearch.bind(this), 300);
        },
        
        async handleInput() {
            this.selectedIndex = -1;
            
            if (this.query.trim().length < 2) {
                this.closeSuggestions();
                return;
            }
            
            this.debouncedSearch();
        },
        
        async performSearch() {
            if (this.query.trim().length < 2) return;
            
            this.loading = true;
            
            try {
                const result = await this.api.search(this.query, {
                    limit: 5,
                    offset: 0
                });
                
                this.suggestions = result.results.map(r => ({
                    id: r.id,
                    text: r.highlighted_text || r.text,
                    video_id: r.video_id,
                    start_ms: r.start_ms,
                    end_ms: r.end_ms,
                    rank: r.rank
                }));
                
                this.isOpen = this.suggestions.length > 0;
                
                // Emit search results event
                eventSystem.emit('searchResults', {
                    query: this.query,
                    results: result.results,
                    total_found: result.total_found
                });
                
            } catch (error) {
                eventSystem.handleError(error, 'SearchBar component');
                this.suggestions = [];
                this.isOpen = false;
            } finally {
                this.loading = false;
            }
        },
        
        async handleSubmit() {
            if (this.query.trim().length === 0) return;
            
            this.closeSuggestions();
            
            // Emit search submit event
            eventSystem.emit('searchSubmit', {
                query: this.query,
                searchType: this.searchType
            });
            
            // Navigate to search results page or update current page
            if (window.location.pathname !== '/search') {
                window.location.href = `/search?q=${encodeURIComponent(this.query)}&type=${this.searchType}`;
            }
        },
        
        handleKeydown(event) {
            if (!this.isOpen) return;
            
            switch (event.key) {
                case 'ArrowDown':
                    event.preventDefault();
                    this.selectedIndex = Math.min(this.selectedIndex + 1, this.suggestions.length - 1);
                    break;
                    
                case 'ArrowUp':
                    event.preventDefault();
                    this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                    break;
                    
                case 'Enter':
                    event.preventDefault();
                    if (this.selectedIndex >= 0) {
                        this.selectSuggestion(this.suggestions[this.selectedIndex]);
                    } else {
                        this.handleSubmit();
                    }
                    break;
                    
                case 'Escape':
                    this.closeSuggestions();
                    break;
            }
        },
        
        selectSuggestion(suggestion) {
            // Navigate to video at specific timestamp
            const url = `/video/${suggestion.video_id}?t=${Math.floor(suggestion.start_ms / 1000)}`;
            window.location.href = url;
            
            this.closeSuggestions();
            
            // Emit suggestion selected event
            eventSystem.emit('suggestionSelected', suggestion);
        },
        
        closeSuggestions() {
            this.isOpen = false;
            this.selectedIndex = -1;
        },
        
        handleFocus() {
            if (this.suggestions.length > 0) {
                this.isOpen = true;
            }
        },
        
        handleBlur() {
            // Delay closing to allow click on suggestions
            setTimeout(() => {
                this.closeSuggestions();
            }, 200);
        },
        
        setSearchType(type) {
            this.searchType = type;
            if (this.query.trim().length >= 2) {
                this.debouncedSearch();
            }
        },
        
        getPlaceholderText() {
            const placeholders = {
                semantic: 'Ask a question or search for concepts...',
                keyword: 'Search for specific words or phrases...',
                hybrid: 'Search using both keywords and concepts...'
            };
            
            return placeholders[this.searchType] || 'Search...';
        },
        
        formatSuggestionText(text) {
            // Remove HTML tags for display but preserve highlighting
            return text.replace(/<(?!\/?(mark|strong|em)\b)[^>]*>/gi, '');
        },
        
        truncateText(text, maxLength = 120) {
            if (text.length <= maxLength) return text;
            return text.substring(0, maxLength).replace(/\s+\S*$/, '') + '...';
        },
        
        formatTime(milliseconds) {
            if (!milliseconds || milliseconds < 0) return '0:00';
            
            const totalSeconds = Math.floor(milliseconds / 1000);
            const hours = Math.floor(totalSeconds / 3600);
            const minutes = Math.floor((totalSeconds % 3600) / 60);
            const seconds = totalSeconds % 60;
            
            if (hours > 0) {
                return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }
            
            return `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }
    };
}