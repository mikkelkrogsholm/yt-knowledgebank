# YouTube Knowledgebank - Troubleshooting Guide

## Quick Navigation
- [🚀 Quick Start Issues](#-quick-start-issues)
- [🌐 JavaScript & Frontend Errors](#-javascript--frontend-errors)  
- [📹 Video Processing Issues](#-video-processing-issues)
- [🔍 Search Problems](#-search-problems)
- [🐌 Performance Issues](#-performance-issues)
- [🔑 API Configuration Problems](#-api-configuration-problems)
- [🗄️ Database Issues](#️-database-issues)
- [🐳 Docker & Development Setup](#-docker--development-setup)
- [📊 Monitoring & Diagnostics](#-monitoring--diagnostics)
- [🆘 Getting Help](#-getting-help)

---

## 🚀 Quick Start Issues

### Problem: Application won't start
```bash
Error: Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Solution:**
1. **Start Docker Desktop**:
   ```bash
   # macOS: Start Docker Desktop application
   # Linux: Start Docker daemon
   sudo systemctl start docker
   ```

2. **Verify Docker is running**:
   ```bash
   docker --version
   docker compose version
   ```

3. **Build and start the application**:
   ```bash
   docker compose up --build
   ```

### Problem: Port 8765 already in use
```bash
Error: bind: address already in use
```

**Solution:**
1. **Check what's using the port**:
   ```bash
   lsof -i :8765
   # Or on some systems:
   netstat -tlnp | grep 8765
   ```

2. **Kill the process or change the port**:
   ```bash
   # Option 1: Kill the process
   kill -9 <PID>
   
   # Option 2: Use a different port
   docker compose down
   # Edit docker-compose.yml to use "8766:8765"
   docker compose up --build
   ```

### Problem: Permission denied on data directory
```bash
Error: mkdir: cannot create directory '/app/data': Permission denied
```

**Solution:**
1. **Fix directory permissions**:
   ```bash
   sudo chmod 755 ./data
   sudo chown -R $(whoami) ./data
   ```

2. **Restart the container**:
   ```bash
   docker compose down
   docker compose up --build
   ```

---

## 🌐 JavaScript & Frontend Errors

### Problem: Alpine.js components not initializing
```javascript
Uncaught ReferenceError: Alpine is not defined
```

**Symptoms:**
- Interactive elements don't respond
- Dark mode toggle doesn't work
- Search suggestions don't appear
- Modal windows won't open

**Solution:**
1. **Check browser console for errors** (F12 → Console):
   ```javascript
   // Look for these error patterns:
   ReferenceError: Alpine is not defined
   TypeError: Cannot read property 'data' of undefined
   SyntaxError: Unexpected token
   ```

2. **Clear browser cache and reload**:
   ```bash
   # Chrome: Ctrl+Shift+R (Cmd+Shift+R on macOS)
   # Firefox: Ctrl+F5
   # Safari: Cmd+Option+R
   ```

3. **Check network connectivity**:
   ```bash
   curl -I http://localhost:8765/static/js/components/
   # Should return 200 OK
   ```

4. **Restart the container**:
   ```bash
   docker compose restart
   ```

### Problem: Dark mode not working
```javascript
localStorage.getItem is not a function
```

**Solution:**
1. **Check localStorage access**:
   ```javascript
   // Open browser console and test:
   localStorage.setItem('test', 'value');
   console.log(localStorage.getItem('test'));
   // Should log: 'value'
   ```

2. **Clear localStorage if corrupted**:
   ```javascript
   // In browser console:
   localStorage.clear();
   location.reload();
   ```

3. **Reset dark mode setting**:
   ```javascript
   // In browser console:
   localStorage.removeItem('darkMode');
   location.reload();
   ```

### Problem: Search autocomplete not working
```javascript
TypeError: Cannot read property 'addEventListener' of null
```

**Solution:**
1. **Check search bar element exists**:
   ```javascript
   // In browser console:
   console.log(document.querySelector('#search-input'));
   // Should not be null
   ```

2. **Verify API connectivity**:
   ```bash
   curl -X POST http://localhost:8765/api/search \
     -H "Content-Type: application/json" \
     -d '{"query":"test","limit":1}'
   ```

3. **Check for JavaScript errors**:
   ```javascript
   // Common error patterns:
   Failed to fetch
   NetworkError when attempting to fetch resource
   ```

### Problem: Modal windows not opening
```javascript
ReferenceError: modal is not defined
```

**Solution:**
1. **Check modal component initialization**:
   ```html
   <!-- Look for this in the HTML: -->
   <div x-data="modal()">
   ```

2. **Verify Alpine.js is loaded before components**:
   ```html
   <!-- Order should be: -->
   <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
   <script src="/static/js/components/modal.js"></script>
   ```

3. **Test modal functionality**:
   ```javascript
   // In browser console:
   Alpine.data('modal')();
   // Should return a function
   ```

---

## 📹 Video Processing Issues

### Problem: YouTube video download fails
```python
ERROR: Video unavailable
```

**Common Causes:**
- Age-restricted videos
- Private/unlisted videos
- Regional restrictions
- Invalid YouTube URL
- Network connectivity issues

**Solution:**
1. **Test with a simple, public video**:
   ```bash
   # Try processing this test video:
   https://www.youtube.com/watch?v=dQw4w9WgXcQ
   ```

2. **Check video accessibility**:
   ```bash
   # Test if video is accessible:
   curl -I "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
   # Should return 200 OK
   ```

3. **Update yt-dlp**:
   ```bash
   docker compose exec web pip install --upgrade yt-dlp
   docker compose restart
   ```

4. **Check Docker container logs**:
   ```bash
   docker compose logs -f web
   # Look for specific error messages
   ```

### Problem: ElevenLabs transcription fails
```python
HTTP 401: Invalid API key
```

**Solution:**
1. **Verify API key format**:
   - ElevenLabs keys start with `sk-`
   - Should be 32+ characters long
   - No spaces or special characters

2. **Test API key validity**:
   ```bash
   curl -X GET "https://api.elevenlabs.io/v1/user" \
     -H "xi-api-key: YOUR_API_KEY"
   # Should return user information, not 401
   ```

3. **Re-configure API key**:
   - Visit http://localhost:8765/settings
   - Clear current key and enter new one
   - Test with a short video (< 1 minute)

4. **Check API quota/limits**:
   ```bash
   # Check your ElevenLabs dashboard for:
   # - Available character quota
   # - API rate limits
   # - Account status
   ```

### Problem: Audio extraction fails
```python
ERROR: ffmpeg not found
```

**Solution:**
1. **Verify ffmpeg installation in container**:
   ```bash
   docker compose exec web which ffmpeg
   # Should return: /usr/bin/ffmpeg
   ```

2. **Check container build**:
   ```bash
   docker compose down
   docker compose build --no-cache
   docker compose up
   ```

3. **Test audio extraction manually**:
   ```bash
   docker compose exec web ffmpeg -version
   # Should show ffmpeg version information
   ```

### Problem: Processing gets stuck at "transcribing"
```
Phase: transcribing, Status: Processing audio with ElevenLabs...
```

**Solution:**
1. **Check processing progress**:
   ```bash
   # Monitor progress endpoint:
   curl http://localhost:8765/progress/YOUR_TASK_ID
   ```

2. **Check ElevenLabs API status**:
   ```bash
   # Verify ElevenLabs service status:
   curl -I https://api.elevenlabs.io/v1/speech-to-text/transcribe
   ```

3. **Restart processing if stuck**:
   ```bash
   docker compose restart
   # Then retry video processing
   ```

4. **Check file sizes and limits**:
   ```bash
   # Check downloaded audio file:
   docker compose exec web ls -la /app/data/videos/*/audio.webm
   # Files >25MB may have processing limits
   ```

---

## 🔍 Search Problems

### Problem: Search returns no results
```json
{"query": "test", "results": [], "total_found": 0}
```

**Solution:**
1. **Check database has content**:
   ```bash
   docker compose exec web sqlite3 /app/data/knowledge_bank.db \
     "SELECT COUNT(*) FROM videos;"
   # Should return > 0
   ```

2. **Verify FTS5 search table**:
   ```bash
   docker compose exec web sqlite3 /app/data/knowledge_bank.db \
     "SELECT COUNT(*) FROM transcript_search;"
   # Should return > 0
   ```

3. **Test with simple search term**:
   ```bash
   curl -X POST http://localhost:8765/api/search \
     -H "Content-Type: application/json" \
     -d '{"query":"the","limit":5}'
   ```

4. **Rebuild search index**:
   ```bash
   docker compose exec web python -c "
   from app.migration import MigrationManager
   from app.database import init_database
   db = init_database()
   mgr = MigrationManager('/app/data/videos', db)
   mgr.rebuild_search_index()
   "
   ```

### Problem: Search is very slow (>5 seconds)
```json
{"query_time_ms": 15230.5}
```

**Solution:**
1. **Check database size**:
   ```bash
   docker compose exec web ls -la /app/data/knowledge_bank.db
   # Large files (>1GB) may need optimization
   ```

2. **Optimize database**:
   ```bash
   docker compose exec web sqlite3 /app/data/knowledge_bank.db \
     "VACUUM; ANALYZE;"
   ```

3. **Optimize FTS5 index**:
   ```bash
   docker compose exec web sqlite3 /app/data/knowledge_bank.db \
     "INSERT INTO transcript_search(transcript_search) VALUES('optimize');"
   ```

4. **Increase Docker memory**:
   ```yaml
   # In docker-compose.yml, add:
   services:
     web:
       deploy:
         resources:
           limits:
             memory: 2G
   ```

### Problem: Search highlighting not working
```json
{"highlighted_text": "plain text without <mark> tags"}
```

**Solution:**
1. **Check FTS5 snippet function**:
   ```bash
   docker compose exec web sqlite3 /app/data/knowledge_bank.db \
     "SELECT snippet(transcript_search, 2, '<mark>', '</mark>', '...', 10) 
      FROM transcript_search WHERE transcript_search MATCH 'test' LIMIT 1;"
   ```

2. **Verify search query format**:
   ```python
   # Query should use FTS5 syntax:
   # Good: "productivity tips"
   # Good: "productivity AND tips"
   # Avoid: special characters without escaping
   ```

3. **Test with simple terms**:
   ```bash
   curl -X POST http://localhost:8765/api/search \
     -H "Content-Type: application/json" \
     -d '{"query":"hello","limit":1}'
   ```

---

## 🐌 Performance Issues

### Problem: Application is slow to load (>10 seconds)
**Symptoms:**
- Long initial page load times
- Slow navigation between pages
- Delayed search results

**Solution:**
1. **Check Docker resource allocation**:
   ```bash
   docker stats
   # Look for high CPU/memory usage
   ```

2. **Increase Docker resources**:
   ```yaml
   # In docker-compose.yml:
   services:
     web:
       deploy:
         resources:
           limits:
             memory: 2G
             cpus: '2'
   ```

3. **Check database performance**:
   ```bash
   docker compose exec web python -m app.benchmarks
   # Should show performance metrics
   ```

4. **Monitor system resources**:
   ```bash
   # macOS:
   top -pid $(pgrep -f "com.docker.hyperkit")
   
   # Linux:
   htop
   ```

### Problem: Out of memory errors
```python
MemoryError: Unable to allocate array
```

**Solution:**
1. **Increase Docker memory limit**:
   ```bash
   # Docker Desktop: Settings → Resources → Memory
   # Increase to 4GB or more
   ```

2. **Check memory usage patterns**:
   ```bash
   docker compose exec web python -c "
   import psutil
   print(f'Memory: {psutil.virtual_memory().percent}%')
   "
   ```

3. **Optimize large video processing**:
   ```bash
   # For videos >1 hour, consider splitting or using lower quality audio
   ```

4. **Clean up temporary files**:
   ```bash
   docker compose exec web find /tmp -name "*.webm" -delete
   ```

### Problem: Database locks and timeouts
```python
sqlite3.OperationalError: database is locked
```

**Solution:**
1. **Check for hanging connections**:
   ```bash
   docker compose exec web ps aux | grep python
   ```

2. **Restart application**:
   ```bash
   docker compose restart
   ```

3. **Check database integrity**:
   ```bash
   docker compose exec web sqlite3 /app/data/knowledge_bank.db \
     "PRAGMA integrity_check;"
   ```

4. **Enable WAL mode for better concurrency**:
   ```bash
   docker compose exec web sqlite3 /app/data/knowledge_bank.db \
     "PRAGMA journal_mode=WAL;"
   ```

---

## 🔑 API Configuration Problems

### Problem: OpenAI API errors
```python
openai.error.AuthenticationError: Invalid API key
```

**Solution:**
1. **Verify OpenAI API key format**:
   - Should start with `sk-`
   - Should be 51+ characters long
   - No spaces or line breaks

2. **Test API key**:
   ```bash
   curl -X GET "https://api.openai.com/v1/models" \
     -H "Authorization: Bearer YOUR_API_KEY"
   ```

3. **Check API quota and billing**:
   ```bash
   # Visit: https://platform.openai.com/usage
   # Verify you have available credits
   ```

4. **Re-configure in settings**:
   - Visit http://localhost:8765/settings
   - Enter OpenAI API key in second field
   - Test with a simple question

### Problem: ElevenLabs API quota exceeded
```python
HTTP 402: Insufficient quota
```

**Solution:**
1. **Check quota usage**:
   ```bash
   # Visit ElevenLabs dashboard
   # Check character usage vs. limit
   ```

2. **Use shorter test videos**:
   ```bash
   # Try videos under 5 minutes for testing
   ```

3. **Upgrade ElevenLabs plan**:
   ```bash
   # Visit: https://elevenlabs.io/subscription
   ```

4. **Monitor usage**:
   ```bash
   # Keep track of processed minutes/characters
   ```

### Problem: API rate limiting
```python
HTTP 429: Too Many Requests
```

**Solution:**
1. **Implement rate limiting**:
   ```python
   # Wait between API calls
   import time
   time.sleep(1)  # 1 second between requests
   ```

2. **Process videos sequentially**:
   ```bash
   # Don't process multiple videos simultaneously
   ```

3. **Check API limits documentation**:
   ```bash
   # ElevenLabs: Check rate limits in dashboard
   # OpenAI: Check rate limits in documentation
   ```

---

## 🗄️ Database Issues

### Problem: Migration fails
```python
ERROR: Failed to migrate video data
```

**Solution:**
1. **Check JSON file integrity**:
   ```bash
   docker compose exec web python -c "
   import json
   with open('/app/data/videos/VIDEO_ID/metadata.json') as f:
       data = json.load(f)
       print('JSON valid')
   "
   ```

2. **Reset database and retry**:
   ```bash
   docker compose exec web rm /app/data/knowledge_bank.db
   curl -X POST http://localhost:8765/api/migration/run
   ```

3. **Check migration status**:
   ```bash
   curl http://localhost:8765/api/migration/status
   ```

4. **Manual migration if needed**:
   ```bash
   docker compose exec web python -m app.migration --migrate
   ```

### Problem: Database corruption
```python
sqlite3.DatabaseError: database disk image is malformed
```

**Solution:**
1. **Check database integrity**:
   ```bash
   docker compose exec web sqlite3 /app/data/knowledge_bank.db \
     "PRAGMA integrity_check;"
   ```

2. **Backup and recover**:
   ```bash
   # Backup current database
   docker compose exec web cp /app/data/knowledge_bank.db /app/data/backup.db
   
   # Try to recover
   docker compose exec web sqlite3 /app/data/knowledge_bank.db \
     ".dump" | sqlite3 /app/data/recovered.db
   
   # Replace if recovery successful
   docker compose exec web mv /app/data/recovered.db /app/data/knowledge_bank.db
   ```

3. **Recreate from JSON files**:
   ```bash
   docker compose exec web rm /app/data/knowledge_bank.db
   curl -X POST http://localhost:8765/api/migration/run
   ```

### Problem: FTS5 search table missing
```python
sqlite3.OperationalError: no such table: transcript_search
```

**Solution:**
1. **Recreate FTS5 table**:
   ```bash
   docker compose exec web sqlite3 /app/data/knowledge_bank.db \
     "CREATE VIRTUAL TABLE IF NOT EXISTS transcript_search 
      USING fts5(video_id, speaker_id, text, content='transcript_chunks', content_rowid='id');"
   ```

2. **Rebuild search index**:
   ```bash
   docker compose exec web python -c "
   from app.database import init_database
   db = init_database()
   db.rebuild_fts_index()
   "
   ```

---

## 🐳 Docker & Development Setup

### Problem: Docker build fails
```bash
ERROR: failed to solve: process "/bin/sh -c apt-get update" did not complete successfully
```

**Solution:**
1. **Clear Docker build cache**:
   ```bash
   docker builder prune -a
   docker compose build --no-cache
   ```

2. **Check Docker Hub connectivity**:
   ```bash
   docker pull python:3.11-slim
   ```

3. **Update Dockerfile if needed**:
   ```dockerfile
   # Use specific base image versions
   FROM python:3.11.6-slim
   ```

4. **Check system resources**:
   ```bash
   df -h  # Check disk space
   docker system prune  # Clean up if low on space
   ```

### Problem: Volume mounting issues
```bash
Error: cannot mount /path/to/data: no such file or directory
```

**Solution:**
1. **Create data directory**:
   ```bash
   mkdir -p ./data
   chmod 755 ./data
   ```

2. **Check Docker Compose configuration**:
   ```yaml
   volumes:
     - ./data:/app/data  # Relative path should work
   ```

3. **Use absolute paths if needed**:
   ```yaml
   volumes:
     - /absolute/path/to/data:/app/data
   ```

### Problem: Container won't stop
```bash
docker compose down  # Hangs indefinitely
```

**Solution:**
1. **Force stop containers**:
   ```bash
   docker compose kill
   docker compose down
   ```

2. **Remove orphaned containers**:
   ```bash
   docker compose down --remove-orphans
   ```

3. **Clean up if needed**:
   ```bash
   docker system prune
   ```

---

## 📊 Monitoring & Diagnostics

### Quick Health Check Script

Run our automated troubleshooting test script:
```bash
./scripts/troubleshoot-test.sh
```

This script will verify:
- ✅ Docker environment setup
- ✅ Application accessibility  
- ✅ Database connectivity
- ✅ File system permissions
- ✅ System resources

### Checking Application Health

1. **Basic health check**:
   ```bash
   curl -f http://localhost:8765/ || echo "App down"
   ```

2. **API endpoints status**:
   ```bash
   # Test key endpoints
   curl -I http://localhost:8765/api/search
   curl -I http://localhost:8765/api/migration/status
   curl -I http://localhost:8765/settings
   ```

3. **Database connectivity**:
   ```bash
   docker compose exec web sqlite3 /app/data/knowledge_bank.db "SELECT 1;"
   ```

### Performance Monitoring

1. **Run performance benchmarks**:
   ```bash
   docker compose exec web python -m app.benchmarks
   ```

2. **Monitor Docker resources**:
   ```bash
   docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
   ```

3. **Check response times**:
   ```bash
   curl -X POST http://localhost:8765/api/search \
     -d '{"query":"test","limit":1}' \
     -H "Content-Type: application/json" \
     --write-out "Response time: %{time_total}s\n"
   ```

### Log Analysis

1. **View application logs**:
   ```bash
   docker compose logs -f web
   ```

2. **Filter for errors**:
   ```bash
   docker compose logs web | grep -i error
   ```

3. **Monitor real-time logs**:
   ```bash
   docker compose logs -f web | grep -E "(ERROR|WARN|Exception)"
   ```

---

## 🆘 Getting Help

### Before Reporting Issues

1. **Gather system information**:
   ```bash
   echo "OS: $(uname -a)"
   echo "Docker: $(docker --version)"
   echo "Docker Compose: $(docker compose version)"
   ```

2. **Export error logs**:
   ```bash
   docker compose logs web > error_log.txt
   ```

3. **Check database status**:
   ```bash
   curl http://localhost:8765/api/migration/status
   ```

4. **Test with minimal configuration**:
   ```bash
   # Fresh start with clean data
   docker compose down
   rm -rf ./data/*
   docker compose up --build
   ```

### Information to Include in Bug Reports

1. **Environment details**:
   - Operating system and version
   - Docker and Docker Compose versions
   - Available system resources (RAM, disk space)

2. **Error reproduction steps**:
   - Exact steps to reproduce the issue
   - Expected behavior vs. actual behavior
   - Screenshots of error messages

3. **Log information**:
   - Full error messages from console/logs
   - Browser console errors (F12)
   - Network requests that failed

4. **Configuration details**:
   - API keys configured (masked)
   - Number of videos processed
   - Recent changes made to system

### Common Support Resources

1. **GitHub Issues**: Report bugs and feature requests
2. **Developer Documentation**: `/docs/developer-guide.md`
3. **API Documentation**: `/docs/api-endpoints.md`
4. **Database Schema**: `/docs/database-schema.md`

### Emergency Recovery

If everything fails, **complete reset**:
```bash
# ⚠️ This will delete all your data! Backup first if needed.
docker compose down
docker system prune -a
rm -rf ./data/*
git checkout -- .
docker compose up --build

# Visit http://localhost:8765/settings
# Reconfigure API keys
# Test with a short video
```

### Quick Validation

After implementing any solution, run our health check:
```bash
./scripts/troubleshoot-test.sh
```

---

## 🔧 Preventive Maintenance

### Regular Health Checks
```bash
# Run weekly
docker compose exec web python -m app.benchmarks
docker compose exec web sqlite3 /app/data/knowledge_bank.db "PRAGMA integrity_check;"
```

### Database Optimization
```bash
# Run monthly
docker compose exec web sqlite3 /app/data/knowledge_bank.db "VACUUM; ANALYZE;"
docker compose exec web sqlite3 /app/data/knowledge_bank.db \
  "INSERT INTO transcript_search(transcript_search) VALUES('optimize');"
```

### System Cleanup
```bash
# Run as needed
docker system prune
docker compose exec web find /tmp -name "*.webm" -mtime +7 -delete
```

---

*This troubleshooting guide is maintained alongside the codebase. For the latest updates and additional help, see the project repository documentation.*