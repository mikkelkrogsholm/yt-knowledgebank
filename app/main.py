from fastapi import FastAPI, Request, Form, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from app.processor import process_and_transcribe, progress_store, get_task_result, get_all_videos
from app.settings import get_api_key, save_api_key
from app.database import init_database, get_database_session
from app.migration import MigrationManager
from app.search import SearchManager, SearchResult
import os
import sys
import argparse
import uuid
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, List

# Pydantic models for search API
class SearchRequest(BaseModel):
    query: str
    video_id: Optional[str] = None
    speaker_id: Optional[str] = None
    start_date: Optional[str] = None  # ISO format string
    end_date: Optional[str] = None    # ISO format string
    limit: int = 50
    offset: int = 0

class SearchResultResponse(BaseModel):
    id: int
    video_id: str
    speaker_id: str
    start_ms: int
    end_ms: int
    text: str
    highlighted_text: str
    rank: float
    word_count: int

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultResponse]
    total_found: int
    has_more: bool
    query_time_ms: float

app = FastAPI()

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def overview(request: Request):
    """Main overview page showing all processed videos"""
    videos = get_all_videos()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "videos": videos
    })

@app.get("/process", response_class=HTMLResponse)
async def process_page(request: Request):
    """Video processing page"""
    return templates.TemplateResponse("process.html", {"request": request})

@app.post("/process")
async def process_video(url: str = Form(...)):
    api_key = get_api_key()
    if not api_key:
        return JSONResponse({"error": "Please configure your ElevenLabs API key in settings"}, status_code=400)
    
    task_id = str(uuid.uuid4())
    # Start download + transcribe in background
    asyncio.create_task(process_and_transcribe(url, task_id, api_key))
    return JSONResponse({"task_id": task_id})

@app.get("/progress/{task_id}")
async def get_progress(task_id: str):
    async def generate():
        while True:
            if task_id in progress_store:
                data = progress_store[task_id]
                yield f"data: {json.dumps(data)}\n\n"
                if data.get("phase") in ["completed", "error"]:
                    await asyncio.sleep(1)  # Give client time to receive final update
                    break
            await asyncio.sleep(0.5)
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/result/{task_id}")
async def get_result(task_id: str):
    """Get the final result for a completed task"""
    try:
        result = get_task_result(task_id)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=404)

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    api_key = get_api_key()
    api_key_masked = f"sk-...{api_key[-4:]}" if api_key and len(api_key) > 4 else ""
    has_key = bool(api_key)
    
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "api_key_masked": api_key_masked,
        "has_key": has_key
    })

@app.post("/settings/save")
async def save_settings(request: Request, api_key: str = Form(...)):
    try:
        save_api_key(api_key)
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "api_key_masked": f"sk-...{api_key[-4:]}" if len(api_key) > 4 else "",
            "has_key": True,
            "success": "API key saved successfully!"
        })
    except Exception as e:
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "api_key_masked": "",
            "has_key": False,
            "error": f"Error saving API key: {str(e)}"
        })

@app.get("/video/{task_id}", response_class=HTMLResponse)
async def video_detail(request: Request, task_id: str):
    """Individual video detail page"""
    try:
        result = get_task_result(task_id)
        if not result.get('metadata'):
            # Video not found
            return templates.TemplateResponse("404.html", {
                "request": request,
                "message": "Video not found"
            }, status_code=404)
        
        return templates.TemplateResponse("video.html", {
            "request": request,
            "video": result.get('metadata', {}),
            "transcript": result.get('transcript', {}),
            "task_id": task_id
        })
    except Exception as e:
        return templates.TemplateResponse("404.html", {
            "request": request,
            "message": f"Error loading video: {str(e)}"
        }, status_code=500)

@app.post("/api/search", response_model=SearchResponse)
async def search_transcripts(search_request: SearchRequest):
    """
    Search through transcript chunks using FTS5 full-text search.
    
    Returns search results with highlighting, filtering, and pagination.
    """
    try:
        import time
        
        # Parse date strings if provided
        start_date = None
        end_date = None
        
        if search_request.start_date:
            try:
                start_date = datetime.fromisoformat(search_request.start_date.replace('Z', '+00:00'))
            except ValueError:
                return JSONResponse(
                    {"error": "Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"},
                    status_code=400
                )
        
        if search_request.end_date:
            try:
                end_date = datetime.fromisoformat(search_request.end_date.replace('Z', '+00:00'))
            except ValueError:
                return JSONResponse(
                    {"error": "Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"},
                    status_code=400
                )
        
        # Perform search
        search_manager = SearchManager()
        start_time = time.time()
        
        results = search_manager.search(
            query=search_request.query,
            video_id=search_request.video_id,
            speaker_id=search_request.speaker_id,
            start_date=start_date,
            end_date=end_date,
            limit=search_request.limit + 1,  # Get one extra to check if there are more results
            offset=search_request.offset
        )
        
        end_time = time.time()
        query_time_ms = (end_time - start_time) * 1000
        
        # Check if there are more results
        has_more = len(results) > search_request.limit
        if has_more:
            results = results[:-1]  # Remove the extra result
        
        # Convert to response model
        result_responses = [
            SearchResultResponse(
                id=result.id,
                video_id=result.video_id,
                speaker_id=result.speaker_id,
                start_ms=result.start_ms,
                end_ms=result.end_ms,
                text=result.text,
                highlighted_text=result.highlighted_text,
                rank=result.rank,
                word_count=result.word_count
            ) for result in results
        ]
        
        return SearchResponse(
            query=search_request.query,
            results=result_responses,
            total_found=len(result_responses),
            has_more=has_more,
            query_time_ms=query_time_ms
        )
        
    except Exception as e:
        return JSONResponse(
            {"error": f"Search error: {str(e)}"},
            status_code=500
        )

@app.get("/api/search", response_model=SearchResponse)
async def search_transcripts_get(
    q: str = Query(..., description="Search query"),
    video_id: Optional[str] = Query(None, description="Filter by video ID"),
    speaker_id: Optional[str] = Query(None, description="Filter by speaker ID"),
    start_date: Optional[str] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (ISO format)"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
):
    """
    Search through transcript chunks using GET request.
    
    This is an alternative to the POST endpoint for simple searches.
    """
    search_request = SearchRequest(
        query=q,
        video_id=video_id,
        speaker_id=speaker_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    
    return await search_transcripts(search_request)

@app.get("/api/search/stats")
async def search_stats():
    """Get search index statistics."""
    try:
        search_manager = SearchManager()
        stats = search_manager.get_search_stats()
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to get search stats: {str(e)}"},
            status_code=500
        )

@app.get("/api/migration/status")
async def migration_status():
    """Get migration status - returns info about database and migration readiness."""
    try:
        # Check if database is initialized
        from app.database import _db_manager
        if _db_manager is None:
            return JSONResponse({
                "status": "not_initialized",
                "message": "Database not initialized",
                "migrated": False
            })
        
        # Check if any videos exist in database
        session = get_database_session()
        try:
            from app.database import Video
            video_count = session.query(Video).count()
            session.close()
            
            return JSONResponse({
                "status": "initialized",
                "message": f"Database initialized with {video_count} videos",
                "migrated": video_count > 0,
                "video_count": video_count
            })
        except Exception as e:
            session.close()
            return JSONResponse({
                "status": "error",
                "message": f"Database error: {str(e)}",
                "migrated": False
            })
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e),
            "migrated": False
        })

@app.post("/api/migration/run")
async def run_migration():
    """Run migration from JSON files to database."""
    try:
        # Initialize database if not already done
        db_manager = init_database()
        
        # Run migration
        migration_manager = MigrationManager(
            videos_directory="/app/data/videos",
            database_manager=db_manager
        )
        
        result = migration_manager.run_migration()
        
        return JSONResponse({
            "success": result["status"] == "success",
            "result": result
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": f"Migration failed: {str(e)}"
        }, status_code=500)

def run_migration_cli():
    """CLI function to run migration."""
    from app.migration import run_migration_cli as run_migration_func
    return run_migration_func()

def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(description="YouTube Knowledgebank Application")
    parser.add_argument(
        "--migrate", 
        action="store_true", 
        help="Run data migration from JSON files to database"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to run the web server on (default: 8765)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the web server to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set the logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Handle migration command
    if args.migrate:
        return run_migration_cli()
    
    # Otherwise run the web server
    print(f"🌐 Starting YouTube Knowledgebank web server on {args.host}:{args.port}")
    print("🔧 Use --migrate flag to run data migration")
    
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)
    return 0

if __name__ == "__main__":
    sys.exit(main())