/**
 * Insight Cards System
 * 
 * Collection of dashboard cards that provide different knowledge insights:
 * - Recent Summaries Card
 * - Topic Trends Card  
 * - Entity Highlights Card
 * - Processing Status Card
 * - Quick Stats Card
 */

// Recent Summaries Card
function recentSummariesCard() {
    return {
        summaries: [],
        isLoading: true,
        error: null,
        api: null,
        
        init() {
            this.api = new KnowledgeAPI();
            this.loadData();
            
            // Auto-refresh every 5 minutes
            setInterval(() => this.loadData(), 5 * 60 * 1000);
            
            // Listen for dashboard refresh events
            eventSystem.on('dashboard:refresh', () => this.loadData());
        },
        
        async loadData() {
            try {
                this.isLoading = true;
                this.error = null;
                
                const response = await this.api.getSummaries({
                    limit: 5,
                    order: 'created_at_desc'
                });
                
                this.summaries = response.summaries || [];
            } catch (error) {
                console.error('Failed to load summaries:', error);
                this.error = 'Failed to load summaries';
                this.summaries = [];
            } finally {
                this.isLoading = false;
            }
        },
        
        async refresh() {
            await this.loadData();
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
        },
        
        showSummaryModal(summary) {
            eventSystem.emit('showModal', {
                type: 'summary',
                data: summary
            });
        }
    };
}

// Topic Trends Card
function topicTrendsCard() {
    return {
        topics: [],
        isLoading: true,
        error: null,
        api: null,
        
        init() {
            this.api = new KnowledgeAPI();
            this.loadData();
            
            // Auto-refresh every 10 minutes
            setInterval(() => this.loadData(), 10 * 60 * 1000);
            
            eventSystem.on('dashboard:refresh', () => this.loadData());
        },
        
        async loadData() {
            try {
                this.isLoading = true;
                this.error = null;
                
                const response = await this.api.getTopicTrends({
                    limit: 10,
                    timeframe: '30days'
                });
                
                this.topics = response.topics || [];
            } catch (error) {
                console.error('Failed to load topic trends:', error);
                this.error = 'Failed to load topics';
                this.topics = [];
            } finally {
                this.isLoading = false;
            }
        },
        
        async refresh() {
            await this.loadData();
        },
        
        getTrendColor(trend) {
            switch (trend) {
                case 'up': return 'text-green-500';
                case 'down': return 'text-red-500';
                case 'stable': return 'text-gray-500';
                default: return 'text-gray-400';
            }
        },
        
        getTrendIcon(trend) {
            switch (trend) {
                case 'up': return '↗️';
                case 'down': return '↘️';
                case 'stable': return '➡️';
                default: return '•';
            }
        },
        
        searchTopic(topicName) {
            // Navigate to search with topic filter
            window.location.href = `/search?q=${encodeURIComponent(topicName)}&type=topic`;
        }
    };
}

// Entity Highlights Card
function entityHighlightsCard() {
    return {
        entities: [],
        isLoading: true,
        error: null,
        api: null,
        
        init() {
            this.api = new KnowledgeAPI();
            this.loadData();
            
            // Auto-refresh every 15 minutes
            setInterval(() => this.loadData(), 15 * 60 * 1000);
            
            eventSystem.on('dashboard:refresh', () => this.loadData());
        },
        
        async loadData() {
            try {
                this.isLoading = true;
                this.error = null;
                
                const response = await this.api.getEntityHighlights({
                    limit: 10,
                    min_mentions: 2
                });
                
                this.entities = response.entities || [];
            } catch (error) {
                console.error('Failed to load entity highlights:', error);
                this.error = 'Failed to load entities';
                this.entities = [];
            } finally {
                this.isLoading = false;
            }
        },
        
        async refresh() {
            await this.loadData();
        },
        
        getEntityIcon(type) {
            switch (type) {
                case 'person': return '👤';
                case 'book': return '📚';
                case 'company': return '🏢';
                case 'concept': return '💡';
                case 'tool': return '🔧';
                case 'place': return '📍';
                default: return '🏷️';
            }
        },
        
        searchEntity(entityName) {
            // Navigate to search with entity filter
            window.location.href = `/search?q=${encodeURIComponent(entityName)}&type=entity`;
        }
    };
}

// Processing Status Card
function processingStatusCard() {
    return {
        status: {
            queue_length: 0,
            in_progress: 0,
            completed_today: 0,
            failed_today: 0,
            current_job: null
        },
        isLoading: true,
        error: null,
        api: null,
        
        init() {
            this.api = new KnowledgeAPI();
            this.loadData();
            
            // Auto-refresh every 30 seconds for processing status
            setInterval(() => this.loadData(), 30 * 1000);
            
            eventSystem.on('dashboard:refresh', () => this.loadData());
        },
        
        async loadData() {
            try {
                this.isLoading = true;
                this.error = null;
                
                const response = await this.api.getProcessingStatus();
                this.status = response || this.status;
            } catch (error) {
                console.error('Failed to load processing status:', error);
                this.error = 'Failed to load status';
            } finally {
                this.isLoading = false;
            }
        },
        
        async refresh() {
            await this.loadData();
        }
    };
}

// Quick Stats Card
function quickStatsCard() {
    return {
        stats: {
            total_videos: 0,
            total_hours: 0,
            entities_discovered: 0,
            topics_identified: 0,
            qa_sessions: 0
        },
        isLoading: true,
        error: null,
        api: null,
        
        init() {
            this.api = new KnowledgeAPI();
            this.loadData();
            
            // Auto-refresh every 5 minutes
            setInterval(() => this.loadData(), 5 * 60 * 1000);
            
            eventSystem.on('dashboard:refresh', () => this.loadData());
        },
        
        async loadData() {
            try {
                this.isLoading = true;
                this.error = null;
                
                const response = await this.api.getKnowledgeStats();
                this.stats = { ...this.stats, ...response };
            } catch (error) {
                console.error('Failed to load knowledge stats:', error);
                this.error = 'Failed to load stats';
            } finally {
                this.isLoading = false;
            }
        },
        
        async refresh() {
            await this.loadData();
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

// Activity Dashboard Component
function activityDashboard() {
    return {
        recentActivity: [],
        recentConversations: [],
        recentVideos: [],
        searchHistory: [],
        bookmarks: [],
        isLoading: true,
        error: null,
        api: null,
        
        init() {
            this.api = new KnowledgeAPI();
            this.loadData();
            
            // Auto-refresh every 2 minutes
            setInterval(() => this.loadData(), 2 * 60 * 1000);
            
            eventSystem.on('dashboard:refresh', () => this.loadData());
        },
        
        async loadData() {
            try {
                this.isLoading = true;
                this.error = null;
                
                // Load all activity data in parallel
                const [activity, conversations, videos] = await Promise.all([
                    this.loadRecentActivity(),
                    this.loadRecentQA(),
                    this.loadRecentVideos()
                ]);
                
                this.recentActivity = activity;
                this.recentConversations = conversations;
                this.recentVideos = videos;
                
            } catch (error) {
                console.error('Failed to load activity data:', error);
                this.error = 'Failed to load activity';
            } finally {
                this.isLoading = false;
            }
        },
        
        async loadRecentActivity() {
            try {
                const response = await this.api.getRecentActivity({
                    limit: 10
                });
                return response.activities || [];
            } catch (error) {
                // Generate mock activity if API not available
                return [
                    {
                        id: 1,
                        type: 'question',
                        description: 'Asked about productivity tips',
                        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
                    },
                    {
                        id: 2,
                        type: 'video_processed',
                        description: 'Processed "Time Management Strategies"',
                        timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString()
                    },
                    {
                        id: 3,
                        type: 'search',
                        description: 'Searched for "morning routine"',
                        timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString()
                    }
                ];
            }
        },
        
        async loadRecentQA() {
            try {
                const response = await this.api.getRecentQA({
                    limit: 5
                });
                return response.conversations || [];
            } catch (error) {
                return [];
            }
        },
        
        async loadRecentVideos() {
            try {
                const response = await this.api.getRecentVideos({
                    limit: 5
                });
                return response.videos || [];
            } catch (error) {
                return [];
            }
        },
        
        async refresh() {
            await this.loadData();
        },
        
        getActivityIcon(type) {
            switch (type) {
                case 'question': return '❓';
                case 'search': return '🔍';
                case 'video_processed': return '🎥';
                case 'entity_discovered': return '🏷️';
                case 'topic_identified': return '📊';
                case 'summary_generated': return '📝';
                default: return '•';
            }
        },
        
        formatTimeAgo(timestamp) {
            if (!timestamp) return 'Unknown';
            
            const date = new Date(timestamp);
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / (1000 * 60));
            const diffHours = Math.floor(diffMins / 60);
            const diffDays = Math.floor(diffHours / 24);
            
            if (diffMins < 1) return 'Just now';
            if (diffMins < 60) return `${diffMins}m ago`;
            if (diffHours < 24) return `${diffHours}h ago`;
            if (diffDays < 7) return `${diffDays}d ago`;
            
            return date.toLocaleDateString();
        },
        
        rerunSearch(query) {
            this.activeQuery = query;
            window.location.href = `/search?q=${encodeURIComponent(query)}`;
        },
        
        addBookmark(item) {
            const bookmark = {
                id: Date.now(),
                ...item,
                bookmarked_at: new Date().toISOString()
            };
            
            this.bookmarks.push(bookmark);
            
            // Persist to localStorage
            try {
                localStorage.setItem('knowledgebank_bookmarks', JSON.stringify(this.bookmarks));
            } catch (error) {
                console.error('Failed to save bookmark:', error);
            }
        },
        
        removeBookmark(itemId) {
            this.bookmarks = this.bookmarks.filter(b => b.id !== itemId);
            
            // Persist to localStorage
            try {
                localStorage.setItem('knowledgebank_bookmarks', JSON.stringify(this.bookmarks));
            } catch (error) {
                console.error('Failed to remove bookmark:', error);
            }
        }
    };
}

// Register all components globally
if (typeof window !== 'undefined') {
    window.recentSummariesCard = recentSummariesCard;
    window.topicTrendsCard = topicTrendsCard;
    window.entityHighlightsCard = entityHighlightsCard;
    window.processingStatusCard = processingStatusCard;
    window.quickStatsCard = quickStatsCard;
    window.activityDashboard = activityDashboard;
}