/**
 * ResultCard Alpine.js Component
 * 
 * Flexible card component for displaying videos, entities, topics, and search results
 */

function resultCard() {
    return {
        type: 'video', // 'video', 'entity', 'topic', 'search_result'
        data: {},
        expanded: false,
        loading: false,
        
        init() {
            // Validate required data based on type
            this.validateData();
        },
        
        validateData() {
            const requiredFields = {
                video: ['id', 'title'],
                entity: ['name', 'type'],
                topic: ['name', 'weight'],
                search_result: ['text', 'video_id']
            };
            
            const required = requiredFields[this.type] || [];
            for (const field of required) {
                if (!this.data[field]) {
                    console.warn(`ResultCard: Missing required field '${field}' for type '${this.type}'`);
                }
            }
        },
        
        getTitle() {
            switch (this.type) {
                case 'video':
                    return this.data.title || 'Untitled Video';
                case 'entity':
                    return this.data.name || 'Unknown Entity';
                case 'topic':
                    return this.data.name || 'Unknown Topic';
                case 'search_result':
                    return this.getSearchResultTitle();
                default:
                    return 'Unknown Item';
            }
        },
        
        getSearchResultTitle() {
            const text = this.data.text || '';
            const maxLength = 60;
            
            if (text.length <= maxLength) return text;
            
            // Try to break at word boundary
            const truncated = text.substring(0, maxLength);
            const lastSpace = truncated.lastIndexOf(' ');
            
            if (lastSpace > maxLength * 0.7) {
                return truncated.substring(0, lastSpace) + '...';
            }
            
            return truncated + '...';
        },
        
        getSubtitle() {
            switch (this.type) {
                case 'video':
                    return this.formatDuration(this.data.duration_seconds) + 
                           (this.data.processed_at ? ` • Processed ${this.formatDate(this.data.processed_at)}` : '');
                case 'entity':
                    return `${this.capitalizeFirst(this.data.type)} • ${this.data.mention_count || 0} mentions`;
                case 'topic':
                    return `Weight: ${this.formatWeight(this.data.weight)} • ${this.data.video_count || 0} videos`;
                case 'search_result':
                    return `Relevance: ${this.formatScore(this.data.rank)} • ${this.formatTime(this.data.start_ms)}`;
                default:
                    return '';
            }
        },
        
        getDescription() {
            switch (this.type) {
                case 'video':
                    return this.data.description ? 
                           this.truncateText(this.data.description, 120) : 
                           'No description available';
                case 'entity':
                    return this.data.description || `${this.capitalizeFirst(this.data.type)} mentioned in videos`;
                case 'topic':
                    return this.data.description || `Topic found across ${this.data.video_count || 0} videos`;
                case 'search_result':
                    return this.formatHighlightedText(this.data.highlighted_text || this.data.text);
                default:
                    return '';
            }
        },
        
        getThumbnail() {
            switch (this.type) {
                case 'video':
                    return this.data.thumbnail_url || this.getYouTubeThumbnail(this.data.youtube_id);
                case 'entity':
                    return this.getEntityIcon();
                case 'topic':
                    return this.getTopicIcon();
                case 'search_result':
                    return this.getYouTubeThumbnail(this.getVideoIdFromResult());
                default:
                    return null;
            }
        },
        
        getYouTubeThumbnail(youtubeId) {
            if (!youtubeId) return null;
            return `https://img.youtube.com/vi/${youtubeId}/mqdefault.jpg`;
        },
        
        getEntityIcon() {
            const iconMap = {
                person: '👤',
                organization: '🏢',
                book: '📚',
                concept: '💡',
                place: '📍',
                event: '📅'
            };
            
            return iconMap[this.data.type] || '🏷️';
        },
        
        getTopicIcon() {
            // Could be enhanced with topic-specific icons
            return '🏷️';
        },
        
        getVideoIdFromResult() {
            return this.data.video_id;
        },
        
        handleClick() {
            switch (this.type) {
                case 'video':
                    this.navigateToVideo();
                    break;
                case 'entity':
                    this.showEntityDetails();
                    break;
                case 'topic':
                    this.showTopicDetails();
                    break;
                case 'search_result':
                    this.navigateToResult();
                    break;
            }
        },
        
        navigateToVideo() {
            const url = `/video/${this.data.id}`;
            window.location.href = url;
            
            eventSystem.emit('videoSelected', this.data);
        },
        
        navigateToResult() {
            const timestamp = Math.floor((this.data.start_ms || 0) / 1000);
            const url = `/video/${this.data.video_id}?t=${timestamp}`;
            window.location.href = url;
            
            eventSystem.emit('searchResultSelected', this.data);
        },
        
        showEntityDetails() {
            eventSystem.emit('showModal', {
                type: 'entity',
                data: this.data
            });
        },
        
        showTopicDetails() {
            eventSystem.emit('showModal', {
                type: 'topic',
                data: this.data
            });
        },
        
        toggleExpanded() {
            this.expanded = !this.expanded;
        },
        
        formatDuration(seconds) {
            if (!seconds) return '0:00';
            
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = Math.floor(seconds % 60);
            
            if (hours > 0) {
                return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
            }
            
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        },
        
        formatTime(milliseconds) {
            if (!milliseconds) return '0:00';
            
            const totalSeconds = Math.floor(milliseconds / 1000);
            const minutes = Math.floor(totalSeconds / 60);
            const seconds = totalSeconds % 60;
            
            return `${minutes}:${seconds.toString().padStart(2, '0')}`;
        },
        
        formatDate(dateString) {
            if (!dateString) return '';
            
            const date = new Date(dateString);
            const now = new Date();
            const diffMs = now - date;
            const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
            
            if (diffDays === 0) return 'Today';
            if (diffDays === 1) return 'Yesterday';
            if (diffDays < 7) return `${diffDays} days ago`;
            if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
            if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
            
            return date.toLocaleDateString();
        },
        
        formatWeight(weight) {
            if (typeof weight !== 'number') return '0%';
            return `${Math.round(weight * 100)}%`;
        },
        
        formatScore(score) {
            if (typeof score !== 'number') return '0%';
            return `${Math.round(score * 100)}%`;
        },
        
        formatHighlightedText(text) {
            if (!text) return '';
            
            // Remove excessive HTML tags but preserve highlighting
            return text.replace(/<(?!\/?(mark|strong|em)\b)[^>]*>/gi, '');
        },
        
        truncateText(text, maxLength) {
            if (!text || text.length <= maxLength) return text;
            
            const truncated = text.substring(0, maxLength);
            const lastSpace = truncated.lastIndexOf(' ');
            
            if (lastSpace > maxLength * 0.7) {
                return truncated.substring(0, lastSpace) + '...';
            }
            
            return truncated + '...';
        },
        
        capitalizeFirst(str) {
            if (!str) return '';
            return str.charAt(0).toUpperCase() + str.slice(1);
        },
        
        getCardClasses() {
            const baseClasses = 'bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow cursor-pointer';
            const typeClasses = {
                video: 'hover:border-blue-300',
                entity: 'hover:border-green-300',
                topic: 'hover:border-purple-300',
                search_result: 'hover:border-orange-300'
            };
            
            return `${baseClasses} ${typeClasses[this.type] || ''}`;
        },
        
        getBadgeColor() {
            const colors = {
                video: 'bg-blue-100 text-blue-800',
                entity: 'bg-green-100 text-green-800',
                topic: 'bg-purple-100 text-purple-800',
                search_result: 'bg-orange-100 text-orange-800'
            };
            
            return colors[this.type] || 'bg-gray-100 text-gray-800';
        }
    };
}