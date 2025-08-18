# Developer Guide

## Overview

This guide provides comprehensive information for developers working on the YouTube Knowledgebank project. It covers the development environment setup, project architecture, testing procedures, and deployment guidelines.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Development Environment](#development-environment)
3. [Project Architecture](#project-architecture)
4. [Development Workflow](#development-workflow)
5. [Testing Guide](#testing-guide)
6. [Database Operations](#database-operations)
7. [Performance Optimization](#performance-optimization)
8. [Troubleshooting](#troubleshooting)
9. [Deployment](#deployment)
10. [Contributing Guidelines](#contributing-guidelines)

---

## Quick Start

### Prerequisites

- **Docker & Docker Compose**: Latest version
- **Git**: For version control
- **Code Editor**: VS Code recommended with Python extensions

### Initial Setup

```bash
# Clone repository
git clone git@github.com:mikkelkrogsholm/yt-knowledgebank.git
cd yt-knowledgebank

# Start development environment
docker compose up --build

# Access application
open http://localhost:8765
```

### First-Time Configuration

1. **Configure ElevenLabs API Key**:
   - Visit http://localhost:8765/settings
   - Enter your ElevenLabs API key
   - Test with a short YouTube video

2. **Verify Database Setup**:
   ```bash
   # Check migration status
   curl http://localhost:8765/api/migration/status
   
   # Run migration if needed
   curl -X POST http://localhost:8765/api/migration/run
   ```

3. **Test Search Functionality**:
   ```bash
   # Search test
   curl -X POST http://localhost:8765/api/search \
     -H "Content-Type: application/json" \
     -d '{"query": "test", "limit": 5}'
   ```

---

## Development Environment

### Docker Development Setup

**All development runs in Docker containers**. This ensures consistency across development environments and matches the production setup.

#### Container Architecture

```yaml
# docker-compose.yml structure
services:
  web:
    build: .
    ports:
      - "8765:8765"
    volumes:
      - "./app:/app/app"           # Live code reloading
      - "./templates:/app/templates"
      - "./tests:/app/tests"
      - "./data:/app/data"         # Persistent data
    environment:
      - PYTHONPATH=/app
```

#### Development Commands

```bash
# Start development environment
docker compose up --build

# Run commands in container
docker compose exec web bash
docker compose exec web python -m pytest
docker compose exec web python -m app.benchmarks

# View logs
docker compose logs -f

# Stop everything
docker compose down
```

### File Structure

```
yt-knowledgebank/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── database.py          # Database models and setup
│   ├── database_queries.py  # Database query functions
│   ├── downloader.py        # YouTube download functionality
│   ├── processor.py         # Video processing pipeline
│   ├── search.py           # Search functionality
│   ├── migration.py        # Data migration utilities
│   ├── settings.py         # Configuration management
│   └── benchmarks.py       # Performance benchmarking
├── templates/
│   ├── base.html           # Base template
│   ├── index.html          # Overview page
│   ├── process.html        # Processing interface
│   ├── video.html          # Video detail view
│   ├── settings.html       # Settings page
│   └── 404.html           # Error page
├── tests/
│   ├── test_database.py
│   ├── test_migration.py
│   ├── test_search.py
│   ├── test_api_integration.py
│   └── test_functions_coverage.py
├── docs/
│   ├── database-schema.md
│   ├── api-endpoints.md
│   └── developer-guide.md
├── context/
│   ├── git-strategy.md
│   ├── knowledge-bank-prd.md
│   └── knowledge-bank-todo.md
├── data/                   # Persistent data (gitignored)
│   ├── knowledge_bank.db   # Main database
│   ├── settings.json       # API keys
│   └── videos/            # Downloaded videos
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pytest.ini
└── CLAUDE.md              # Project instructions
```

### IDE Configuration

#### VS Code Settings

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "/usr/local/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"],
  "docker.defaultPlatform": "linux",
  "files.associations": {
    "*.html": "html"
  }
}
```

#### Recommended Extensions

- Python
- Docker
- Pylance
- Black Formatter
- SQLite Viewer

---

## Project Architecture

### Application Layers

```
┌─────────────────┐
│   Web Layer     │  FastAPI + Jinja2 Templates
├─────────────────┤
│  Service Layer  │  Business Logic & Processing
├─────────────────┤
│  Data Layer     │  SQLite + FTS5 + SQLAlchemy
├─────────────────┤
│ External APIs   │  ElevenLabs + yt-dlp + YouTube
└─────────────────┘
```

### Core Components

#### 1. Web Layer (`main.py`)

**Responsibilities**:
- HTTP request/response handling
- Template rendering
- API endpoint routing
- Real-time progress via Server-Sent Events

**Key Features**:
- FastAPI framework with automatic OpenAPI documentation
- Jinja2 templates for server-side rendering
- Background task processing
- Error handling and validation

#### 2. Processing Pipeline (`processor.py`)

**Workflow**:
1. **URL Validation**: Verify YouTube URL format
2. **Metadata Extraction**: Get video information
3. **Audio Download**: Extract audio using yt-dlp
4. **Transcription**: Speech-to-text via ElevenLabs
5. **Data Storage**: Save to database and files
6. **Progress Tracking**: Real-time status updates

**Functions**:
- `process_and_transcribe()`: Main processing function
- `get_all_videos()`: Retrieve video listings
- `get_task_result()`: Get processing results
- `format_duration()`, `format_date()`: Utility functions

#### 3. Database Layer (`database.py`, `database_queries.py`)

**Architecture**:
- SQLite with FTS5 for full-text search
- SQLAlchemy ORM for type safety
- Connection pooling and session management
- Migration system for data upgrade

**Models**:
- `Video`: Main video metadata
- `TranscriptChunk`: Word-level transcript data
- `Speaker`: Speaker identification and statistics

#### 4. Search System (`search.py`)

**Features**:
- Full-text search with FTS5
- Boolean query support
- Relevance ranking (BM25)
- Search result highlighting
- Filtering by video, speaker, date range

**Performance**:
- Sub-millisecond search times
- Concurrent search support
- Pagination for large result sets

### Data Flow

```
YouTube URL → Metadata → Audio → Transcript → Database → Search Index
     ↓            ↓        ↓         ↓           ↓           ↓
  Validation  → Storage → Files → Processing → SQLite → FTS5 Table
```

### Error Handling Strategy

1. **Graceful Degradation**: Continue operation even if some features fail
2. **Comprehensive Logging**: All errors logged with context
3. **User-Friendly Messages**: Clear error messages for end users
4. **Automatic Recovery**: Retry mechanisms for transient failures
5. **Fallback Systems**: JSON file backup if database unavailable

---

## Development Workflow

### Git Branch Strategy

Following the project's develop-first strategy:

```bash
# Main branches
main     # Production-ready releases
develop  # Integration branch for features

# Feature branches
feature/feature-name    # New features
bugfix/bug-description  # Bug fixes
hotfix/critical-issue   # Critical production fixes
```

### Development Process

1. **Create Feature Branch**:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Development Cycle**:
   ```bash
   # Make changes
   docker compose up --build    # Test changes
   docker compose exec web pytest  # Run tests
   git add .
   git commit -m "feat: add your feature description"
   ```

3. **Pre-merge Checklist**:
   - [ ] All tests passing
   - [ ] Code coverage maintained
   - [ ] Documentation updated
   - [ ] Performance benchmarks run
   - [ ] Manual testing completed

4. **Merge Process**:
   ```bash
   git push origin feature/your-feature-name
   # Create pull request to develop branch
   # After review and CI passes, merge
   ```

### Code Standards

#### Python Code Style

- **Formatter**: Black (automatic formatting)
- **Linting**: Pylint with project-specific rules
- **Import Order**: isort for consistent imports
- **Type Hints**: Required for new functions

#### Commit Message Format

```
type(scope): description

Body explaining the change

Fixes #issue-number
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

#### Example Commit Messages

```bash
git commit -m "feat(search): add boolean query support for advanced searches"
git commit -m "fix(database): resolve connection pooling issue under high load"
git commit -m "docs(api): update search endpoint documentation with examples"
```

---

## Testing Guide

### Test Structure

```
tests/
├── test_database.py           # Database model tests
├── test_migration.py          # Migration functionality
├── test_search.py            # Search functionality
├── test_api_integration.py   # API endpoint tests
└── test_functions_coverage.py # Coverage improvement tests
```

### Running Tests

```bash
# Run all tests
docker compose exec web pytest

# Run specific test file
docker compose exec web pytest tests/test_search.py

# Run with coverage
docker compose exec web pytest --cov=app --cov-report=html

# Run specific test
docker compose exec web pytest tests/test_search.py::TestSearchManager::test_basic_search
```

### Test Categories

#### 1. Unit Tests

Test individual functions and classes in isolation:

```python
def test_format_duration():
    assert format_duration(90) == "1:30"
    assert format_duration(3600) == "1:00:00"
    assert format_duration(None) == "0:00"
```

#### 2. Integration Tests

Test component interactions:

```python
def test_video_processing_pipeline():
    # Test entire process from URL to database
    result = process_and_transcribe(url, task_id, api_key)
    assert result["success"] is True
    
    # Verify database storage
    video = get_task_result(task_id)
    assert video is not None
```

#### 3. API Tests

Test HTTP endpoints:

```python
def test_search_endpoint():
    response = client.post("/api/search", json={
        "query": "test query",
        "limit": 10
    })
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
```

### Test Data Management

#### Fixtures

```python
@pytest.fixture
def sample_video_data():
    return {
        "id": "test-video-123",
        "title": "Test Video",
        "duration": 300
    }

@pytest.fixture
def db_session():
    # Create test database
    engine = create_engine("sqlite:///:memory:")
    session = Session(engine)
    yield session
    session.close()
```

#### Mocking External Services

```python
@patch('app.processor.ElevenLabs')
def test_transcription_with_mock(mock_elevenlabs):
    mock_client = MagicMock()
    mock_elevenlabs.return_value = mock_client
    
    # Test transcription logic without API calls
    result = transcribe_audio("test.webm", "test-key")
    assert result is not None
```

### Coverage Requirements

- **Minimum Coverage**: 80% overall
- **Critical Modules**: 90% coverage required
  - `database_queries.py`
  - `search.py`
  - `migration.py`
- **New Code**: 100% coverage required for new features

### Performance Testing

```bash
# Run performance benchmarks
docker compose exec web python -m app.benchmarks

# Performance requirements validation
# - Search queries: <500ms (currently ~0.86ms)
# - Database operations: <1000ms (currently ~5.79ms)
# - Memory growth: <1MB per operation (currently 0.000MB)
```

---

## Database Operations

### Database Management

#### Initialization

```python
from app.database import init_database

# Initialize database with tables
db_manager = init_database()

# Check if tables exist
tables = db_manager.get_table_names()
print(f"Available tables: {tables}")
```

#### Session Management

```python
from app.database import get_database_session

# Get session for database operations
session = get_database_session()
try:
    # Perform database operations
    videos = session.query(Video).all()
finally:
    session.close()
```

### Common Database Operations

#### Video Operations

```python
# Add new video
video = Video(
    id="test-123",
    title="Test Video",
    duration=300
)
session.add(video)
session.commit()

# Query videos
videos = session.query(Video).filter(
    Video.duration > 600
).order_by(Video.processed_date.desc()).all()

# Update video
video = session.query(Video).filter(Video.id == "test-123").first()
video.title = "Updated Title"
session.commit()
```

#### Search Operations

```python
from app.search import SearchManager

# Initialize search
search_manager = SearchManager()

# Perform search
results = search_manager.search(
    query="productivity tips",
    video_id="specific-video",  # Optional filter
    limit=20,
    offset=0
)

# Results structure
for result in results["results"]:
    print(f"Video: {result['video_id']}")
    print(f"Text: {result['highlighted_text']}")
    print(f"Relevance: {result['rank']}")
```

### Migration Operations

```python
from app.migration import MigrationManager

# Check migration status
migration_manager = MigrationManager(
    videos_directory="/app/data/videos",
    database_manager=db_manager
)

status = migration_manager.check_migration_status()
print(f"JSON files: {status['json_files_count']}")
print(f"Migrated: {status['migrated_count']}")

# Run migration
result = migration_manager.run_migration()
if result["status"] == "success":
    print(f"Migrated {result['migrated']} videos")
```

### Database Maintenance

```bash
# Database backup
docker compose exec web cp /app/data/knowledge_bank.db /app/data/backup_$(date +%Y%m%d).db

# Database optimization
docker compose exec web sqlite3 /app/data/knowledge_bank.db "VACUUM; ANALYZE;"

# FTS5 optimization
docker compose exec web sqlite3 /app/data/knowledge_bank.db \
  "INSERT INTO transcript_search(transcript_search) VALUES('optimize');"
```

---

## Performance Optimization

### Current Performance Benchmarks

Based on comprehensive testing:

| Operation | Current Performance | Target | Status |
|-----------|-------------------|--------|---------|
| Search queries | 0.86ms | <500ms | ✅ 584x better |
| Database operations | 5.79ms | <1000ms | ✅ 172x better |
| Single video retrieval | 0.86ms | <100ms | ✅ 116x better |
| Memory per operation | 0.000MB | <1MB | ✅ Perfect |

### Optimization Strategies

#### 1. Database Optimization

**Indexes**:
```sql
-- Ensure proper indexing
CREATE INDEX idx_videos_processed_date ON videos(processed_date);
CREATE INDEX idx_transcript_chunks_video_start ON transcript_chunks(video_id, start_ms);
CREATE INDEX idx_speakers_video_speaker ON speakers(video_id, speaker_id);
```

**Query Optimization**:
```python
# Use efficient queries with proper joins
query = session.query(Video).options(
    joinedload(Video.transcript_chunks),
    joinedload(Video.speakers)
).filter(Video.processed_date > cutoff_date)
```

#### 2. Search Optimization

**FTS5 Configuration**:
```sql
-- Optimize FTS5 table
INSERT INTO transcript_search(transcript_search) VALUES('optimize');

-- Configure FTS5 for better performance
PRAGMA foreign_keys=ON;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
```

**Search Query Patterns**:
```python
# Efficient search with pagination
results = search_manager.search(
    query=query,
    limit=min(limit, 100),  # Cap result size
    offset=offset,
    filters={"video_id": video_id} if video_id else None
)
```

#### 3. Memory Management

**Connection Pooling**:
```python
# Configure SQLAlchemy connection pool
engine = create_engine(
    database_url,
    poolclass=StaticPool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30
)
```

**Resource Cleanup**:
```python
# Always close sessions
try:
    # Database operations
    pass
finally:
    session.close()
```

### Profiling and Monitoring

#### Performance Profiling

```bash
# Run performance benchmarks
docker compose exec web python -m app.benchmarks

# Profile specific operations
docker compose exec web python -m cProfile -s cumtime -m app.search
```

#### Memory Monitoring

```python
import psutil
import os

def get_memory_usage():
    """Monitor memory usage during operations."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB
```

#### Query Analysis

```sql
-- Analyze query performance
EXPLAIN QUERY PLAN 
SELECT v.*, COUNT(tc.id) as word_count 
FROM videos v 
LEFT JOIN transcript_chunks tc ON v.id = tc.video_id 
GROUP BY v.id;
```

---

## Troubleshooting

### Common Issues

#### 1. Database Issues

**Problem**: Database locked error
```
sqlite3.OperationalError: database is locked
```

**Solutions**:
```bash
# Check for hanging processes
docker compose exec web ps aux | grep python

# Restart container
docker compose restart

# Check database integrity
docker compose exec web sqlite3 /app/data/knowledge_bank.db "PRAGMA integrity_check;"
```

**Problem**: Migration fails
```
ERROR: Failed to migrate video data
```

**Solutions**:
```bash
# Check JSON file integrity
docker compose exec web python -c "
import json
with open('/app/data/videos/video-id/metadata.json') as f:
    data = json.load(f)
    print('JSON valid')
"

# Reset migration
docker compose exec web rm /app/data/knowledge_bank.db
curl -X POST http://localhost:8765/api/migration/run
```

#### 2. Search Issues

**Problem**: Search returns no results
```
FTS5 table not found or corrupted
```

**Solutions**:
```bash
# Check FTS5 table
docker compose exec web sqlite3 /app/data/knowledge_bank.db \
  "SELECT COUNT(*) FROM transcript_search;"

# Rebuild FTS5 table
docker compose exec web python -c "
from app.migration import MigrationManager
from app.database import init_database
db = init_database()
mgr = MigrationManager('/app/data/videos', db)
mgr.rebuild_search_index()
"
```

#### 3. Performance Issues

**Problem**: Slow response times

**Diagnosis**:
```bash
# Run benchmarks
docker compose exec web python -m app.benchmarks

# Check system resources
docker stats

# Analyze database
docker compose exec web sqlite3 /app/data/knowledge_bank.db "ANALYZE;"
```

**Solutions**:
- Increase Docker memory allocation
- Optimize database indexes
- Review query patterns
- Consider result pagination

#### 4. API Issues

**Problem**: ElevenLabs API errors
```
HTTP 401: Invalid API key
```

**Solutions**:
```bash
# Verify API key
curl http://localhost:8765/settings

# Test API key
docker compose exec web python -c "
from app.settings import get_api_key
print('API Key:', get_api_key()[:10] + '...' if get_api_key() else 'Not set')
"
```

### Debugging Tools

#### Logging Configuration

```python
import logging

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Module-specific logging
logger = logging.getLogger(__name__)
logger.debug("Debug message here")
```

#### Database Inspection

```bash
# SQLite CLI access
docker compose exec web sqlite3 /app/data/knowledge_bank.db

# Common inspection commands
.tables                           # List all tables
.schema videos                    # Show table schema
SELECT COUNT(*) FROM videos;      # Count records
.quit                            # Exit
```

#### API Testing

```bash
# Test all endpoints
curl -X GET http://localhost:8765/
curl -X POST http://localhost:8765/api/search -d '{"query":"test"}'
curl -X GET http://localhost:8765/api/migration/status

# Monitor real-time logs
docker compose logs -f web
```

---

## Deployment

### Production Deployment

#### Environment Configuration

```bash
# Production environment variables
export ENVIRONMENT=production
export DATABASE_URL=/app/data/knowledge_bank.db
export LOG_LEVEL=INFO
export PORT=8765
```

#### Docker Production Build

```dockerfile
# Production Dockerfile optimizations
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/data

# Production optimizations
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8765
CMD ["python", "-m", "app.main"]
```

#### Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8765:8765"
    volumes:
      - "./data:/app/data"
    environment:
      - ENVIRONMENT=production
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8765/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Monitoring and Maintenance

#### Health Checks

```bash
# Application health
curl -f http://localhost:8765/ || echo "App down"

# Database health
docker compose exec web sqlite3 /app/data/knowledge_bank.db "SELECT 1;"

# Performance check
curl -X POST http://localhost:8765/api/search \
  -d '{"query":"test","limit":1}' \
  --write-out "Response time: %{time_total}s\n"
```

#### Backup Strategy

```bash
#!/bin/bash
# Production backup script

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# Database backup
cp /app/data/knowledge_bank.db "$BACKUP_DIR/knowledge_bank_$DATE.db"

# Settings backup
cp /app/data/settings.json "$BACKUP_DIR/settings_$DATE.json"

# Rotate old backups (keep 30 days)
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.json" -mtime +30 -delete
```

#### Log Management

```bash
# Configure log rotation
cat > /etc/logrotate.d/yt-knowledgebank << EOF
/var/log/yt-knowledgebank/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    copytruncate
}
EOF
```

---

## Contributing Guidelines

### Code Review Process

1. **All code must be reviewed** before merging to develop
2. **Automated checks must pass**: tests, linting, coverage
3. **Performance impact must be assessed** for search/database changes
4. **Documentation must be updated** for API/schema changes

### Review Checklist

- [ ] Code follows project style guidelines
- [ ] All tests pass and coverage is maintained
- [ ] Performance benchmarks show no regression
- [ ] API changes are documented
- [ ] Error handling is comprehensive
- [ ] Security implications are considered

### Release Process

1. **Feature Complete**: All planned features implemented
2. **Testing Complete**: Full test suite passes
3. **Performance Validated**: Benchmarks meet requirements
4. **Documentation Updated**: All docs current
5. **Migration Tested**: Data migration works correctly
6. **Production Ready**: Docker build and deployment tested

### Getting Help

- **Documentation**: Check this guide and API docs
- **Issues**: Create GitHub issue with reproduction steps
- **Performance**: Run benchmarks and share results
- **Questions**: Include relevant logs and configuration

---

*This developer guide is maintained alongside the codebase. For the latest updates, see the project repository and documentation.*