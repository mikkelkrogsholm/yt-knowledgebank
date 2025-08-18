from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, RedirectResponse
from app.processor import process_and_transcribe, progress_store, get_task_result, get_all_videos
from app.settings import get_api_key, save_api_key
import os
import uuid
import json
import asyncio

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)