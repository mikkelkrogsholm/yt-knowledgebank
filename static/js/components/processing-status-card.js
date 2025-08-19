/**
 * Processing Status Card
 * 
 * Displays current video processing status with:
 * - Real-time progress updates
 * - Queue length and ETA
 * - Progress bars and visual indicators
 * - Click-through to detailed progress view
 */

function processingStatusCard() {
    return {
        // Processing state
        processingData: {
            queue_length: 0,
            in_progress: 0,
            current_job: null
        },
        isLoading: false,
        error: null,
        api: null,
        
        // Update intervals
        updateInterval: null,
        refreshInterval: 3000, // 3 seconds for active processing, 30 seconds for idle
        
        // Component state
        isExpanded: false,
        hasRecentActivity: false,
        
        init() {
            this.api = new KnowledgeAPI();
            this.startStatusUpdates();
            this.checkRecentActivity();
        },
        
        async checkRecentActivity() {
            // Check if there was recent processing activity (last 30 minutes)
            try {
                const videos = await this.api.getRecentVideos({ limit: 5 });
                const now = new Date();
                const thirtyMinutesAgo = new Date(now - 30 * 60 * 1000);
                
                this.hasRecentActivity = videos.videos?.some(video => {
                    const created = new Date(video.created_at || video.processed_date || 0);
                    return created > thirtyMinutesAgo;
                }) || false;
            } catch (error) {
                console.warn('Failed to check recent activity:', error);
            }
        },
        
        startStatusUpdates() {
            this.updateProcessingStatus();
            
            // Set up periodic updates
            this.updateInterval = setInterval(() => {
                this.updateProcessingStatus();
            }, this.refreshInterval);
        },
        
        async updateProcessingStatus() {
            if (this.isLoading) return;
            
            try {
                this.isLoading = true;
                this.error = null;
                
                const response = await this.api.makeRequest('/api/dashboard/processing');
                this.processingData = {
                    queue_length: response.queue_length || 0,
                    in_progress: response.in_progress || 0,
                    current_job: response.current_job || null
                };
                
                // Adjust refresh interval based on activity
                const newInterval = this.processingData.in_progress > 0 ? 3000 : 15000;
                if (newInterval !== this.refreshInterval) {
                    this.refreshInterval = newInterval;
                    clearInterval(this.updateInterval);
                    this.startStatusUpdates();
                }
                
            } catch (error) {
                console.error('Failed to update processing status:', error);
                this.error = 'Failed to load processing status';
            } finally {
                this.isLoading = false;
            }
        },
        
        getStatusDisplay() {
            if (this.processingData.in_progress > 0) {
                return 'Processing';
            } else if (this.processingData.queue_length > 0) {
                return 'Queued';
            } else if (this.hasRecentActivity) {
                return 'Ready';
            } else {
                return 'Idle';
            }
        },
        
        getStatusColor() {
            const status = this.getStatusDisplay();
            switch (status) {
                case 'Processing': return 'blue';
                case 'Queued': return 'yellow';
                case 'Ready': return 'green';
                default: return 'gray';
            }
        },
        
        getProgressPercent() {
            return this.processingData.current_job?.percent || 0;
        },
        
        getCurrentJobTitle() {
            return this.processingData.current_job?.title || 'No active processing';
        },
        
        getCurrentJobPhase() {
            if (!this.processingData.current_job) return '';
            
            const phase = this.processingData.current_job.phase || '';
            switch (phase) {
                case 'downloading': return 'Downloading video...';
                case 'transcribing': return 'Transcribing audio...';
                case 'completed': return 'Processing complete';
                case 'error': return 'Processing error';
                default: return this.processingData.current_job.status || 'Processing...';
            }
        },
        
        getEstimatedTimeRemaining() {
            if (!this.processingData.current_job) return '';
            
            const percent = this.getProgressPercent();
            if (percent <= 0 || percent >= 100) return '';
            
            // Rough estimate based on phase and progress
            const phase = this.processingData.current_job.phase;
            let estimatedTotalMinutes = 5; // Default estimate
            
            if (phase === 'downloading') {
                estimatedTotalMinutes = 2; // Downloading is usually faster
            } else if (phase === 'transcribing') {
                estimatedTotalMinutes = 8; // Transcribing takes longer
            }
            
            const remainingPercent = 100 - percent;
            const remainingMinutes = Math.round((remainingPercent / 100) * estimatedTotalMinutes);
            
            if (remainingMinutes <= 1) return '< 1 min';
            if (remainingMinutes <= 60) return `~${remainingMinutes} min`;
            
            const hours = Math.floor(remainingMinutes / 60);
            const mins = remainingMinutes % 60;
            return mins > 0 ? `~${hours}h ${mins}m` : `~${hours}h`;
        },
        
        toggleExpanded() {
            this.isExpanded = !this.isExpanded;
        },
        
        navigateToProcess() {
            if (this.processingData.current_job) {
                window.location.href = this.processingData.current_job.url || '/process';
            } else {
                window.location.href = '/process';
            }
        },
        
        formatLastActivity() {
            // Show when the last processing activity occurred
            if (this.processingData.in_progress > 0) {
                return 'Active now';
            }
            
            if (this.hasRecentActivity) {
                return 'Recent activity';
            }
            
            return 'No recent activity';
        },
        
        destroy() {
            if (this.updateInterval) {
                clearInterval(this.updateInterval);
            }
        }
    };
}

// Register component globally
if (typeof window !== 'undefined') {
    window.processingStatusCard = processingStatusCard;
}