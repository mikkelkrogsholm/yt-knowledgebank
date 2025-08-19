/**
 * Simple Search Bar Component
 * 
 * Basic search interface for the Knowledge Dashboard
 * Handles only content search - no modes, no suggestions
 */

function simpleSearchBar() {
    return {
        // State
        query: '',
        isLoading: false,
        lastResponse: null,
        
        // API client
        api: null,
        
        init() {
            // Initialize KnowledgeAPI client
            this.api = new KnowledgeAPI();
        },
        
        async handleSubmit() {
            if (!this.query.trim() || this.isLoading) return;
            
            this.isLoading = true;
            this.lastResponse = null;
            
            try {
                const response = await this.api.search(this.query, {
                    limit: 20
                });
                
                // Transform search results into a response format
                this.lastResponse = {
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
                
            } catch (error) {
                console.error('Search failed:', error);
                this.lastResponse = {
                    error: true,
                    message: 'Sorry, I encountered an error while searching. Please try again.'
                };
            } finally {
                this.isLoading = false;
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
                    <div class="text-xs text-gray-500">Score: ${Math.round(result.rank * 100)}%</div>
                </li>`;
            });
            
            html += '</ul>';
            
            if (response.has_more) {
                html += `<p class="mt-3 text-sm text-gray-600">And ${response.total_found - topResults.length} more results available.</p>`;
            }
            
            return html;
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
        
        jumpToVideo(videoId, startMs) {
            // Navigate to video page with timestamp
            const url = `/video/${videoId}?t=${Math.floor(startMs / 1000)}`;
            window.open(url, '_blank');
        }
    };
}

// Register component globally
if (typeof window !== 'undefined') {
    window.simpleSearchBar = simpleSearchBar;
}