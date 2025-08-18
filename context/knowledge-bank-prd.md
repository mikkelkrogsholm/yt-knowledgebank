# YouTube Knowledge Bank - Product Requirements Document

## Vision Statement
Transform the YouTube transcript viewer into an intelligent knowledge extraction and retrieval system that allows users to quickly access, connect, and discover insights from their collected video content.

## Current State
- YouTube video download and transcription system
- Individual video pages with clickable timestamps
- Basic overview of all processed videos
- Real-time processing with progress tracking

## Target State
An intelligent knowledge repository that enables:
- Semantic search across all transcripts
- Cross-video concept discovery
- AI-powered insight extraction
- Knowledge graph visualization
- Interactive question-answering system

## User Stories

### Primary User Stories
1. **As a learner**, I want to search "productivity habits" and find all relevant segments across my videos
2. **As a researcher**, I want to see how concepts evolve across different videos over time
3. **As a knowledge worker**, I want to ask questions like "What books were recommended?" and get comprehensive answers
4. **As a curious person**, I want to discover unexpected connections between ideas from different videos

### Secondary User Stories
1. **As a content creator**, I want to see which topics I've covered and identify gaps
2. **As a student**, I want to create study guides from my educational video collection
3. **As an organizer**, I want to automatically categorize videos by topic and theme

## Feature Requirements

### Phase 1: Database Foundation (MVP)
**Objective**: Migrate from file-based to database-driven architecture

#### Core Features
- **SQLite Database Integration**
  - Structured video metadata storage
  - Word-level transcript storage with timestamps
  - FTS5 full-text search capability
  - Migration from JSON file storage

- **Enhanced Search**
  - Full-text search across all transcripts
  - Filter by speaker, video, date range
  - Search result highlighting
  - Search history and saved searches

#### Success Criteria
- All existing data migrated without loss
- Search response time < 500ms
- Backward compatibility maintained

### Phase 2: Semantic Intelligence (Core Value)
**Objective**: Enable semantic understanding and retrieval

#### Core Features
- **Vector Embeddings**
  - OpenAI embedding integration
  - sqlite-vec for vector similarity search
  - Hybrid search (semantic + keyword)
  - Chunk-level embedding storage

- **Intelligent Search Interface**
  - Natural language queries
  - Semantic similarity results
  - Cross-video concept matching
  - Relevance scoring and ranking

#### Success Criteria
- Semantic search finds relevant content that keyword search misses
- Query understanding improves user satisfaction
- Response accuracy > 80% for concept-based queries

### Phase 3: Knowledge Extraction (Advanced Intelligence)
**Objective**: Automatically extract and organize knowledge

#### Core Features
- **Entity Recognition**
  - Auto-extract books, people, concepts mentioned
  - Canonical entity linking
  - Entity relationship mapping
  - Timeline tracking of entity mentions

- **Topic Modeling**
  - Automatic topic assignment
  - Topic evolution tracking
  - Topic-based video clustering
  - Topic relationship discovery

- **Summary Generation**
  - Per-video key insights
  - Topic-based summaries
  - Cross-video concept summaries
  - Actionable insight extraction

#### Success Criteria
- Entity extraction accuracy > 85%
- Topics are coherent and meaningful
- Summaries capture key insights effectively

### Phase 4: Knowledge Navigation (User Experience)
**Objective**: Provide intuitive ways to explore and connect knowledge

#### Core Features
- **Interactive Knowledge Graph**
  - Visual concept relationships
  - Video-to-video connections
  - Entity relationship visualization
  - Interactive exploration interface

- **Advanced Query Interface**
  - Question-answering system
  - Conversational search
  - Query suggestions and auto-complete
  - Contextual follow-up questions

- **Learning Pathways**
  - Suggested video sequences
  - Concept prerequisite mapping
  - Learning progress tracking
  - Personalized recommendations

#### Success Criteria
- Users can visually explore knowledge connections
- Question-answering provides accurate, sourced responses
- Learning pathways help users discover related content

## Technical Architecture

### Database Design
- **SQLite + Extensions**: Primary storage with FTS5 and sqlite-vec
- **Hybrid Storage**: Relational core with graph capabilities
- **Vector Store**: Embedded similarity search with sqlite-vec
- **Schema**: Designed for both relational queries and graph visualization

### API Architecture
- **Modular Backend**: Separate modules for search, extraction, analysis
- **RESTful APIs**: Clean separation between UI and logic
- **Async Processing**: Background tasks for embedding generation
- **Caching Strategy**: Redis for frequent queries and computed results

### Frontend Enhancement
- **Progressive Enhancement**: Build on existing UI framework
- **Component Architecture**: Reusable search and visualization components
- **Real-time Updates**: WebSocket for live search and processing updates
- **Responsive Design**: Mobile-optimized knowledge exploration

## Implementation Strategy

### Modular Development Approach
Each phase is designed as independent modules that can be developed in parallel:

1. **Database Module** (`feature/database-foundation`)
2. **Search Module** (`feature/semantic-search`) 
3. **Extraction Module** (`feature/knowledge-extraction`)
4. **Navigation Module** (`feature/knowledge-navigation`)

### Technology Stack
- **Backend**: FastAPI + SQLAlchemy + sqlite-vec
- **AI/ML**: OpenAI API for embeddings and LLM tasks
- **Search**: SQLite FTS5 + vector similarity
- **Frontend**: Enhanced Jinja2 templates + JavaScript components
- **Visualization**: D3.js for knowledge graphs

## Success Metrics

### Phase 1 Metrics
- Data migration success rate: 100%
- Search performance: < 500ms response time
- Feature parity: All existing functionality maintained

### Phase 2 Metrics
- Search relevance improvement: 40% better results vs keyword search
- User engagement: 50% increase in search usage
- Query success rate: 80% of semantic queries return relevant results

### Phase 3 Metrics
- Entity extraction accuracy: > 85%
- Topic coherence: User validation of auto-generated topics
- Summary quality: User rating of generated insights

### Phase 4 Metrics
- Knowledge discovery: Users find 30% more connections than before
- Question answering accuracy: > 80% correct responses
- User satisfaction: Improved knowledge retrieval efficiency

## Risk Assessment

### Technical Risks
- **SQLite Performance**: May need optimization for large datasets
- **OpenAI API Costs**: Monitor usage and implement caching
- **Embedding Quality**: May need fine-tuning for domain-specific content

### Mitigation Strategies
- **Performance Monitoring**: Implement query performance tracking
- **Cost Controls**: Implement embedding caching and rate limiting
- **Fallback Options**: Maintain keyword search as backup

## Timeline Estimates
- **Phase 1**: 2-3 weeks (Database foundation)
- **Phase 2**: 3-4 weeks (Semantic search)
- **Phase 3**: 4-5 weeks (Knowledge extraction)
- **Phase 4**: 3-4 weeks (Knowledge navigation)

**Total**: 12-16 weeks for complete knowledge bank transformation

## Future Considerations
- **Multi-modal Support**: Image and video content analysis
- **Collaborative Features**: Shared knowledge banks
- **Export Capabilities**: Knowledge graph export and sharing
- **Advanced Analytics**: Learning pattern analysis and recommendations