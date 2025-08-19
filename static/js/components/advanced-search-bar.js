/**
 * Advanced Search Bar Alpine.js Component
 * 
 * Enhanced search with comprehensive filtering and sorting options
 */

function advancedSearchBar() {
    return {
        // Search state
        query: '',
        isLoading: false,
        results: [],
        totalFound: 0,
        hasMore: false,
        lastResponse: null,
        
        // Filter state
        showFilters: false,
        filters: {
            video_id: '',
            speaker_id: '', 
            uploader: '',
            min_duration: '',
            max_duration: '',
            start_date: '',
            end_date: '',
            sort_by: 'relevance',
            sort_order: 'desc'
        },
        
        // Pagination state
        currentPage: 0,
        resultsPerPage: 20,
        
        // UI state
        searchType: 'content', // 'content' or 'videos'
        
        // API client
        api: null,
        
        init() {
            this.api = new KnowledgeAPI();
            
            // Load saved filters from localStorage
            this.loadSavedFilters();
            
            // Listen for global search events
            eventSystem.on('quickSearch', () => {
                this.$refs.searchInput?.focus();
            });
            
            eventSystem.on('escape', () => {
                this.showFilters = false;
            });
            
            // Debounced search function
            this.debouncedSearch = eventSystem.debounce(this.performSearch.bind(this), 300);
        },
        
        async performSearch(resetPagination = true) {
            if (!this.query.trim()) {
                this.clearResults();
                return;
            }
            
            if (resetPagination) {
                this.currentPage = 0;
            }
            
            this.isLoading = true;
            this.lastResponse = null;
            
            try {
                let result;
                const searchParams = {
                    limit: this.resultsPerPage,
                    offset: this.currentPage * this.resultsPerPage,
                    ...this.getActiveFilters()
                };
                
                if (this.searchType === 'content') {
                    result = await this.api.search(this.query, searchParams);
                    this.results = resetPagination ? result.results : [...this.results, ...result.results];
                    this.totalFound = result.total_found;
                    this.hasMore = result.has_more;
                    
                    // Format for display
                    this.lastResponse = {
                        query: this.query,
                        results: this.results,
                        total_found: this.totalFound,
                        response_time_ms: result.query_time_ms || 0
                    };
                } else if (this.searchType === 'videos') {
                    const videoParams = {
                        query: this.query,
                        ...searchParams
                    };
                    result = await this.filterVideos(videoParams);
                    this.results = resetPagination ? result.videos : [...this.results, ...result.videos];
                    this.totalFound = result.total_found;
                    this.hasMore = result.has_more;
                    
                    this.lastResponse = {
                        query: this.query,
                        results: this.results,
                        total_found: this.totalFound,
                        response_time_ms: 0
                    };
                }
                
                // Save filters to localStorage
                this.saveFilters();
                
                // Emit search results event
                eventSystem.emit('advancedSearchResults', {
                    query: this.query,
                    results: this.results,
                    totalFound: this.totalFound,
                    searchType: this.searchType,
                    filters: this.filters
                });
                
            } catch (error) {
                console.error('Advanced search failed:', error);
                this.lastResponse = {
                    error: true,
                    message: 'Search failed. Please try again.'
                };
                eventSystem.handleError(error, 'AdvancedSearchBar component');
            } finally {
                this.isLoading = false;
            }
        },
        
        async filterVideos(params) {
            const queryParams = new URLSearchParams();
            
            Object.entries(params).forEach(([key, value]) => {
                if (value !== null && value !== undefined && value !== '') {
                    queryParams.append(key, value);
                }
            });
            
            const response = await fetch(`/api/videos/filter?${queryParams.toString()}`);
            if (!response.ok) {
                throw new Error(`Video filter failed: ${response.statusText}`);
            }
            
            return await response.json();
        },
        
        async loadMoreResults() {
            if (!this.hasMore || this.isLoading) return;
            
            this.currentPage++;
            await this.performSearch(false);
        },
        
        getActiveFilters() {
            const active = {};
            Object.entries(this.filters).forEach(([key, value]) => {
                if (value !== null && value !== undefined && value !== '') {
                    active[key] = value;
                }
            });
            return active;
        },
        
        clearResults() {
            this.results = [];
            this.totalFound = 0;
            this.hasMore = false;
            this.lastResponse = null;
            this.currentPage = 0;
        },
        
        clearAllFilters() {
            this.filters = {
                video_id: '',
                speaker_id: '', 
                uploader: '',
                min_duration: '',
                max_duration: '',
                start_date: '',
                end_date: '',
                sort_by: 'relevance',
                sort_order: 'desc'
            };
            
            this.saveFilters();
            
            if (this.query.trim()) {
                this.performSearch();
            }
        },
        
        toggleFilters() {
            this.showFilters = !this.showFilters;
        },
        
        setSearchType(type) {
            if (this.searchType !== type) {
                this.searchType = type;
                
                // Adjust default sort for video search
                if (type === 'videos' && this.filters.sort_by === 'relevance') {
                    this.filters.sort_by = 'date';
                } else if (type === 'content' && ['date', 'duration', 'alphabetical'].includes(this.filters.sort_by)) {
                    this.filters.sort_by = 'relevance';
                }
                
                if (this.query.trim()) {
                    this.performSearch();
                }
            }
        },
        
        handleFilterChange() {
            // Debounce filter changes
            if (!this.debouncedSearch) {
                this.debouncedSearch = eventSystem.debounce(this.performSearch.bind(this), 500);
            }
            
            if (this.query.trim()) {
                this.debouncedSearch();
            }
        },
        
        handleSubmit() {
            this.performSearch();
        },
        
        saveFilters() {
            try {
                localStorage.setItem('advancedSearchFilters', JSON.stringify({
                    filters: this.filters,
                    searchType: this.searchType
                }));
            } catch (e) {
                console.warn('Failed to save search filters:', e);
            }
        },
        
        loadSavedFilters() {
            try {
                const saved = localStorage.getItem('advancedSearchFilters');
                if (saved) {
                    const data = JSON.parse(saved);
                    if (data.filters) {
                        this.filters = { ...this.filters, ...data.filters };
                    }
                    if (data.searchType) {
                        this.searchType = data.searchType;
                    }
                }
            } catch (e) {
                console.warn('Failed to load saved search filters:', e);
            }
        },
        
        getActiveFilterCount() {
            return Object.values(this.getActiveFilters()).length;
        },
        
        formatDuration(seconds) {
            if (!seconds || seconds < 0) return '0:00';
            
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = seconds % 60;
            
            if (hours > 0) {
                return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
            }
            
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        },
        
        formatRelevanceScore(rank) {
            if (!rank || rank === 0) return 100;
            
            // Convert FTS5 BM25 rank to percentage
            const normalizedScore = Math.max(0, Math.min(100, Math.exp(rank) * 100));
            return Math.round(normalizedScore);
        },
        
        formatDate(dateString) {
            if (!dateString) return 'Unknown';
            
            try {
                const date = new Date(dateString);
                return date.toLocaleDateString();
            } catch (e) {
                return 'Invalid date';
            }
        },
        
        jumpToVideo(videoId, startMs = null) {
            let url = `/video/${videoId}`;
            if (startMs && startMs > 0) {
                url += `?t=${Math.floor(startMs / 1000)}`;
            }
            window.open(url, '_blank');
        },
        
        getSortOptions() {
            if (this.searchType === 'content') {
                return [
                    { value: 'relevance', label: 'Relevance' },
                    { value: 'date', label: 'Date' },
                    { value: 'duration', label: 'Duration' },
                    { value: 'alphabetical', label: 'Alphabetical' }
                ];
            } else {
                return [
                    { value: 'date', label: 'Date' },
                    { value: 'duration', label: 'Duration' },
                    { value: 'alphabetical', label: 'Alphabetical' }
                ];
            }
        },
        
        getPlaceholderText() {
            return this.searchType === 'content' 
                ? 'Search video transcripts...' 
                : 'Search video library...';
        }
    };
}

// Register component globally
if (typeof window !== 'undefined') {
    window.advancedSearchBar = advancedSearchBar;
}