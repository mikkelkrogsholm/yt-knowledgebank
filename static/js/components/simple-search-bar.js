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
                const sources = (response.results || []).map((result, index) => ({
                    id: `result_${index}_${result.video_id || 'unknown'}`,
                    video_id: result.video_id || 'unknown',
                    title: result.video_title || `Video ${result.video_id || 'unknown'}`,
                    start_ms: result.start_ms || 0,
                    text: result.text || '',
                    highlighted_text: result.highlighted_text || result.text || '',
                    rank: result.rank || 0
                })).filter(source => source.video_id !== 'unknown'); // Filter out invalid results
                
                this.lastResponse = {
                    query: this.query,
                    answer: this.formatSearchResults(response),
                    sources: sources,
                    total_found: response.total_found || 0,
                    response_time_ms: response.query_time_ms || 0
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
            
            topResults.forEach((result, index) => {
                html += `<li class="border-l-2 border-primary-200 pl-3" data-result-index="${index}">
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

        renderSourcesList() {
            if (!this.lastResponse?.sources || !Array.isArray(this.lastResponse.sources)) {
                return '';
            }
            
            return this.lastResponse.sources.map((source, index) => {
                const title = source.title || 'Untitled';
                const timestamp = this.formatTimestamp(source.start_ms || 0);
                const videoId = source.video_id || '';
                const startMs = source.start_ms || 0;
                
                return `<div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                    <div class="flex-1">
                        <div class="font-medium text-sm">${title}</div>
                        <div class="text-xs text-gray-600 dark:text-gray-400">${timestamp}</div>
                    </div>
                    <button onclick="window.open('/video/${videoId}?t=${Math.floor(startMs / 1000)}', '_blank')" 
                            class="text-primary-600 hover:text-primary-700 text-sm font-medium">
                        Watch →
                    </button>
                </div>`;
            }).join('');
        }
    };
}

// Register component globally
if (typeof window !== 'undefined') {
    window.simpleSearchBar = simpleSearchBar;
}