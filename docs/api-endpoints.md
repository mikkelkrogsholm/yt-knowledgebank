# API Endpoints Documentation

## Overview

The YouTube Knowledgebank provides a comprehensive REST API for video processing, search, and data management. This documentation covers all available endpoints with examples, request/response formats, and error handling.

## Base URL

```
http://localhost:8765
```

## Authentication

Currently, the API uses API key authentication for external services (ElevenLabs). No authentication required for main application endpoints.

## Content Types

- **Request**: `application/json`, `application/x-www-form-urlencoded`, `multipart/form-data`
- **Response**: `application/json`, `text/html`, `text/event-stream`

## Endpoints Overview

| Method | Endpoint | Purpose | Response Type |
|--------|----------|---------|---------------|
| GET | `/` | Main overview page | HTML |
| GET | `/process` | Video processing form | HTML |
| POST | `/process` | Submit video for processing | JSON |
| GET | `/progress/{task_id}` | Real-time progress updates | Server-Sent Events |
| GET | `/result/{task_id}` | Get processing results | JSON |
| GET | `/video/{task_id}` | Video detail page | HTML |
| GET | `/settings` | Settings management page | HTML |
| POST | `/settings` | Save API settings | HTML/Redirect |
| POST | `/api/search` | Search transcripts | JSON |
| GET | `/api/migration/status` | Migration status | JSON |
| POST | `/api/migration/run` | Run migration | JSON |

---

## Web Interface Endpoints

### GET `/` - Overview Page

**Purpose**: Main dashboard showing all processed videos.

**Response**: HTML page with video grid

**Template**: `index.html`

**Query Parameters**: None

**Example**:
```bash
curl -X GET "http://localhost:8765/"
```

**Response**: HTML content with video listings

---

### GET `/process` - Processing Form

**Purpose**: Form interface for submitting YouTube URLs.

**Response**: HTML page with URL input form

**Template**: `process.html`

**Example**:
```bash
curl -X GET "http://localhost:8765/process"
```

---

### POST `/process` - Submit Video Processing

**Purpose**: Submit a YouTube URL for processing and transcription.

**Request Body**: 
- Content-Type: `application/x-www-form-urlencoded`
- Parameter: `url` (YouTube URL)

**Response**: JSON with task identifier

**Example Request**:
```bash
curl -X POST "http://localhost:8765/process" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "url=https://youtu.be/dQw4w9WgXcQ"
```

**Success Response** (200):
```json
{
  "task_id": "e1a792d7-3080-47d0-b199-8bccee31e555"
}
```

**Error Response** (400):
```json
{
  "error": "Please configure your ElevenLabs API key in settings"
}
```

**Error Codes**:
- `400`: Missing API key or invalid URL format
- `500`: Internal processing error

---

### GET `/progress/{task_id}` - Real-time Progress

**Purpose**: Server-Sent Events stream for real-time processing updates.

**Path Parameters**:
- `task_id`: Task identifier from processing submission

**Response**: `text/event-stream`

**Example**:
```bash
curl -X GET "http://localhost:8765/progress/e1a792d7-3080-47d0-b199-8bccee31e555" \
  -H "Accept: text/event-stream"
```

**Response Stream**:
```
data: {"phase":"downloading","progress":25,"message":"Downloading audio..."}

data: {"phase":"transcribing","progress":75,"message":"Transcribing audio..."}

data: {"phase":"completed","progress":100,"message":"Processing completed"}
```

**Progress Phases**:
- `downloading`: Audio extraction from YouTube
- `transcribing`: Speech-to-text conversion
- `saving`: Storing data to database/files
- `completed`: Successfully finished
- `error`: Processing failed

---

### GET `/result/{task_id}` - Get Results

**Purpose**: Retrieve final processing results for a completed task.

**Path Parameters**:
- `task_id`: Task identifier

**Response**: JSON with metadata and transcript

**Example**:
```bash
curl -X GET "http://localhost:8765/result/e1a792d7-3080-47d0-b199-8bccee31e555"
```

**Success Response** (200):
```json
{
  "metadata": {
    "task_id": "e1a792d7-3080-47d0-b199-8bccee31e555",
    "title": "Life-Changing Books Everyone Should Read",
    "duration": 1704,
    "duration_formatted": "28:24",
    "uploader": "BookTube Channel",
    "view_count": 50096,
    "upload_date": "20250817",
    "url": "https://youtu.be/dQw4w9WgXcQ",
    "video_id": "dQw4w9WgXcQ",
    "processed_date": "2025-08-18T13:36:03.974979",
    "processed_date_formatted": "Aug 18, 2025 at 1:36 PM",
    "word_count": 2847,
    "speaker_count": 2
  },
  "transcript": {
    "language_code": "eng",
    "language_probability": 0.9888704419136047,
    "text": "Welcome to today's video about life-changing books...",
    "words": [
      {
        "speaker_id": "speaker_0",
        "start_ms": 0,
        "end_ms": 1000,
        "text": "Welcome to today's"
      }
    ]
  }
}
```

**Error Response** (404):
```json
{
  "error": "Video not found or processing not completed"
}
```

---

### GET `/video/{task_id}` - Video Detail Page

**Purpose**: Detailed view of processed video with interactive transcript.

**Path Parameters**:
- `task_id`: Video identifier

**Response**: HTML page with embedded video player and transcript

**Template**: `video.html`

**Example**:
```bash
curl -X GET "http://localhost:8765/video/e1a792d7-3080-47d0-b199-8bccee31e555"
```

**Features**:
- Embedded YouTube video player
- Clickable transcript with timestamps
- Speaker identification
- Word-level navigation

---

### GET `/settings` - Settings Page

**Purpose**: Configuration interface for API keys and preferences.

**Response**: HTML settings form

**Template**: `settings.html`

**Example**:
```bash
curl -X GET "http://localhost:8765/settings"
```

---

### POST `/settings` - Save Settings

**Purpose**: Save API key and application settings.

**Request Body**:
- Content-Type: `application/x-www-form-urlencoded`
- Parameter: `api_key` (ElevenLabs API key)

**Response**: Redirect to settings page with success message

**Example**:
```bash
curl -X POST "http://localhost:8765/settings" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "api_key=sk_your_elevenlabs_api_key_here"
```

**Success Response** (302/303): Redirect to `/settings`

---

## API Endpoints

### POST `/api/search` - Search Transcripts

**Purpose**: Full-text search across all video transcripts with advanced filtering.

**Request Body**: JSON with search parameters

**Content-Type**: `application/json`

**Request Schema**:
```json
{
  "query": "string (required)",
  "video_id": "string (optional)",
  "speaker_id": "string (optional)", 
  "start_date": "string (optional, ISO format)",
  "end_date": "string (optional, ISO format)",
  "limit": "integer (optional, default: 50)",
  "offset": "integer (optional, default: 0)"
}
```

**Example Request**:
```bash
curl -X POST "http://localhost:8765/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "productivity tips",
    "limit": 10,
    "offset": 0
  }'
```

**Success Response** (200):
```json
{
  "query": "productivity tips",
  "results": [
    {
      "id": 123,
      "video_id": "e1a792d7-3080-47d0-b199-8bccee31e555",
      "speaker_id": "speaker_0",
      "start_ms": 45000,
      "end_ms": 48000,
      "text": "Here are some amazing productivity tips that changed my life",
      "highlighted_text": "Here are some amazing <mark>productivity</mark> <mark>tips</mark> that changed my life",
      "rank": 1.2847,
      "word_count": 11
    }
  ],
  "total_found": 24,
  "has_more": true,
  "query_time_ms": 2.3
}
```

**Advanced Search Examples**:

1. **Phrase Search**:
```json
{
  "query": "\"time management\"",
  "limit": 5
}
```

2. **Filtered Search**:
```json
{
  "query": "books",
  "video_id": "specific-video-id",
  "speaker_id": "speaker_0",
  "limit": 20
}
```

3. **Date Range Search**:
```json
{
  "query": "productivity",
  "start_date": "2025-01-01T00:00:00",
  "end_date": "2025-12-31T23:59:59",
  "limit": 50
}
```

**Error Responses**:

**400 - Invalid Date Format**:
```json
{
  "error": "Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
}
```

**422 - Validation Error**:
```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**500 - Search Error**:
```json
{
  "error": "Search operation failed",
  "details": "Database connection error"
}
```

---

### GET `/api/migration/status` - Migration Status

**Purpose**: Check the status of data migration from JSON files to database.

**Response**: JSON with migration statistics

**Example**:
```bash
curl -X GET "http://localhost:8765/api/migration/status"
```

**Success Response** (200):
```json
{
  "json_files_count": 15,
  "migrated_count": 12,
  "unmigrated_count": 3,
  "database_videos_count": 12,
  "migration_status": "partial",
  "last_migration": "2025-08-18T14:30:22.123456"
}
```

**Migration Status Values**:
- `not_started`: No migration has been performed
- `partial`: Some videos migrated, some remain
- `completed`: All JSON files have been migrated
- `up_to_date`: Database is current with JSON files

---

### POST `/api/migration/run` - Run Migration

**Purpose**: Execute migration from JSON files to database.

**Request Body**: None (empty POST)

**Response**: JSON with migration results

**Example**:
```bash
curl -X POST "http://localhost:8765/api/migration/run" \
  -H "Content-Type: application/json"
```

**Success Response** (200):
```json
{
  "success": true,
  "result": {
    "status": "success",
    "migrated": 8,
    "skipped": 2,
    "errors": 0,
    "total_time": 2.47,
    "details": "Successfully migrated 8 videos to database"
  }
}
```

**Error Response** (500):
```json
{
  "success": false,
  "error": "Migration failed: Database connection error"
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Description | Usage |
|------|-------------|--------|
| 200 | OK | Successful request |
| 302/303 | Redirect | Form submissions, navigation |
| 400 | Bad Request | Invalid parameters or missing data |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation errors |
| 500 | Internal Server Error | Server-side errors |

### Error Response Format

All JSON error responses follow this format:

```json
{
  "error": "Human-readable error message",
  "code": "OPTIONAL_ERROR_CODE",
  "details": "Optional additional details",
  "timestamp": "2025-08-18T14:30:22.123456Z"
}
```

### Common Error Scenarios

1. **Missing API Key**:
   - Endpoint: `POST /process`
   - Response: 400 with API key configuration message

2. **Video Not Found**:
   - Endpoints: `GET /video/{task_id}`, `GET /result/{task_id}`
   - Response: 404 with not found message

3. **Invalid Search Query**:
   - Endpoint: `POST /api/search`
   - Response: 400 with validation details

4. **Database Unavailable**:
   - All endpoints may return 500 with database error message

---

## Rate Limiting

Currently, no rate limiting is implemented. For production deployments, consider:

- **Search endpoints**: 100 requests/minute per IP
- **Processing endpoints**: 10 requests/hour per IP
- **General endpoints**: 1000 requests/hour per IP

## Response Times

Based on performance benchmarks:

| Endpoint Category | Average Response Time | SLA Target |
|-------------------|----------------------|------------|
| Search operations | **0.86ms** | <500ms |
| Database queries | **5.79ms** | <1000ms |
| Video retrieval | **0.86ms** | <100ms |
| File operations | **13.78ms** | <5000ms |

## WebSocket/SSE Support

### Server-Sent Events

The `/progress/{task_id}` endpoint uses Server-Sent Events for real-time updates:

**Connection**:
```javascript
const eventSource = new EventSource('/progress/task-id-123');

eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Progress:', data.progress, data.message);
};

eventSource.onerror = function(event) {
  console.error('Connection error:', event);
};
```

**Event Format**:
```
data: {"phase":"downloading","progress":25,"message":"Processing..."}

data: {"phase":"completed","progress":100,"message":"Done!"}
```

---

## Development and Testing

### API Testing Examples

**Using curl**:
```bash
# Test search functionality
curl -X POST "http://localhost:8765/api/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "limit": 5}'

# Test video processing
curl -X POST "http://localhost:8765/process" \
  -d "url=https://youtu.be/dQw4w9WgXcQ"

# Monitor progress
curl -H "Accept: text/event-stream" \
  "http://localhost:8765/progress/task-id"
```

**Using Python requests**:
```python
import requests
import json

# Search example
search_data = {
    "query": "productivity tips",
    "limit": 10
}
response = requests.post(
    "http://localhost:8765/api/search",
    json=search_data
)
results = response.json()

# Process video example
process_data = {"url": "https://youtu.be/dQw4w9WgXcQ"}
response = requests.post(
    "http://localhost:8765/process",
    data=process_data
)
task_info = response.json()
```

### Monitoring Endpoints

For production monitoring, these endpoints are most critical:

- `GET /` - Application availability
- `POST /api/search` - Core functionality
- `GET /api/migration/status` - Data integrity
- `POST /process` - Video processing pipeline

---

## Future API Enhancements

### Planned Additions

1. **Authentication API**: User management and API key authentication
2. **Analytics API**: Usage statistics and performance metrics
3. **Webhook API**: Notifications for completed processing
4. **Batch API**: Multiple video processing in single request
5. **Export API**: Data export in various formats (CSV, JSON, XML)

### API Versioning

Future versions will use URL path versioning:
- `v1`: Current version (implicit)
- `v2`: Future version with breaking changes

Example: `/api/v2/search` for next-generation search API.

---

*This documentation is current as of Phase 1 completion. For the latest updates, see the source code in `app/main.py`.*