# Quick Troubleshooting Reference

> **For comprehensive solutions, see [Troubleshooting Guide](troubleshooting-guide.md)**

## 🚨 Most Common Issues & Quick Fixes

### App Won't Start
```bash
# Fix: Check Docker is running
docker --version
docker compose up --build
```

### Port 8765 In Use
```bash
# Fix: Use different port or kill process
lsof -i :8765  # Find what's using port
kill -9 <PID>  # Kill the process
# OR change port in docker-compose.yml to "8766:8765"
```

### Video Processing Fails
1. **Check API key**: Visit http://localhost:8765/settings
2. **Test with public video**: Try https://www.youtube.com/watch?v=dQw4w9WgXcQ
3. **Check logs**: `docker compose logs -f web`

### Search Returns Nothing
```bash
# Fix: Check database has content
docker compose exec web sqlite3 /app/data/knowledge_bank.db "SELECT COUNT(*) FROM videos;"
# If 0, run migration: curl -X POST http://localhost:8765/api/migration/run
```

### JavaScript Errors
1. **Clear browser cache**: Ctrl+Shift+R (Cmd+Shift+R on Mac)
2. **Check console**: F12 → Console tab
3. **Restart container**: `docker compose restart`

### Database Locked Error
```bash
# Fix: Restart application
docker compose restart
# If still locked: docker compose down && docker compose up
```

### Out of Memory
1. **Increase Docker memory**: Docker Desktop → Settings → Resources → Memory (4GB+)
2. **Restart Docker Desktop**
3. **Try smaller videos first**

### API Key Errors
- **ElevenLabs**: Must start with `sk-`, check quota at dashboard
- **OpenAI**: Must start with `sk-`, check billing at platform.openai.com

## 🔧 Quick Health Check
```bash
# Run automated diagnostic
./scripts/troubleshoot-test.sh
```

## 🆘 Emergency Reset
```bash
# ⚠️ Deletes all data - backup first!
docker compose down
docker system prune -a
rm -rf ./data/*
docker compose up --build
```

---
*For detailed solutions with explanations, see [Troubleshooting Guide](troubleshooting-guide.md)*