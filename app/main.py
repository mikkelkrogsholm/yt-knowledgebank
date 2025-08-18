from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, RedirectResponse
from app.processor import process_and_transcribe, progress_store, get_task_result, get_all_videos
from app.settings import get_api_key, save_api_key
from app.database import init_database, get_database_session
from app.migration import MigrationManager
import os
import sys
import argparse
import uuid
import json
import asyncio
import logging

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