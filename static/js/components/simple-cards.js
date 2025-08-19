/**
 * Simple Cards System
 * 
 * Collection of simplified dashboard cards:
 * - Basic Stats Card (videos count, hours)
 * - Recent Videos Card (last processed videos)
 */

// Basic Stats Card
function basicStatsCard() {
    return {
        stats: {
            total_videos: 0,
            total_hours: 0
        },
        isLoading: true,
        error: null,
        api: null,
        
        init() {
            this.api = new KnowledgeAPI();
            this.loadData();
        },
        
        async loadData() {
            try {
                this.isLoading = true;
                this.error = null;
                
                // Try to get real stats from backend
                const response = await this.api.getKnowledgeStats();
                this.stats = {
                    total_videos: response.total_videos || 0,
                    total_hours: response.total_hours || 0
                };
            } catch (error) {
                console.error('Failed to load stats:', error);
                this.error = 'Failed to load stats';
                // Keep default stats of 0
                this.stats = {
                    total_videos: 0,
                    total_hours: 0
                };
            } finally {
                this.isLoading = false;
            }
        },
        
        formatHours(hours) {
            if (!hours || hours === 0) return '0h';
            
            if (hours < 1) {
                return `${Math.round(hours * 60)}m`;
            } else if (hours < 10) {
                return `${hours.toFixed(1)}h`;
            } else {
                return `${Math.round(hours)}h`;
            }
        }
    };
}

// Recent Videos Card
function recentVideosCard() {
    return {
        videos: [],
        isLoading: true,
        error: null,
        api: null,
        
        init() {
            this.api = new KnowledgeAPI();
            this.loadData();
        },
        
        async loadData() {
            try {
                this.isLoading = true;
                this.error = null;
                
                // Try to get real recent videos from backend
                const response = await this.api.getRecentVideos({
                    limit: 5
                });
                
                this.videos = (response.videos || []).map(video => ({
                    id: video.id || video.task_id || 'unknown',
                    title: video.title || 'Untitled Video',
                    created_at: video.created_at || video.processed_date || new Date().toISOString(),
                    ...video
                }));
            } catch (error) {
                console.error('Failed to load recent videos:', error);
                this.error = 'Failed to load videos';
                this.videos = [];
            } finally {
                this.isLoading = false;
            }
        },
        
        formatDate(dateString) {
            if (!dateString) return 'Unknown';
            
            const date = new Date(dateString);
            const now = new Date();
            const diffMs = now - date;
            const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
            
            if (diffDays === 0) return 'Today';
            if (diffDays === 1) return 'Yesterday';
            if (diffDays < 7) return `${diffDays} days ago`;
            
            return date.toLocaleDateString();
        }
    };
}

// Register all components globally
if (typeof window !== 'undefined') {
    window.basicStatsCard = basicStatsCard;
    window.recentVideosCard = recentVideosCard;
}