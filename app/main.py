from fastapi import FastAPI, Request, Form, Query, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, validator
from app.processor import process_and_transcribe, progress_store, get_task_result, get_all_videos
from app.settings import get_api_key, save_api_key, get_openai_api_key, save_openai_api_key, get_model_config
from app.database import init_database, get_database_session, QASession, QAExchange, AnswerFeedback
from app.migration import MigrationManager
from app.search import SearchManager, SearchResult
from app.rag_service import RAGService
import os
import sys
import argparse
import uuid
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict

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
    video_title: Optional[str] = None

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultResponse]
    total_found: int
    has_more: bool
    query_time_ms: float

# Pydantic models for Q&A API
class AskRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    
    @validator('question')
    def question_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Question cannot be empty')
        return v.strip()

class SourceResponse(BaseModel):
    video_id: str
    chunk_id: int
    start_ms: int
    end_ms: int
    text: str
    relevance_score: float

class AskResponse(BaseModel):
    question: str
    answer: str
    sources: List[SourceResponse]
    confidence_score: float
    response_time_ms: int
    session_id: str

class FeedbackRequest(BaseModel):
    exchange_id: str
    rating: int
    feedback_text: Optional[str] = None
    feedback_type: Optional[str] = None
    
    @validator('rating')
    def rating_must_be_valid(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v

class FeedbackResponse(BaseModel):
    success: bool
    feedback_id: Optional[str] = None
    message: Optional[str] = None

class QAExchangeResponse(BaseModel):
    id: str
    question: str
    answer: str
    sources: List[Dict]
    timestamp: str
    response_time_ms: Optional[int] = None

class HistoryResponse(BaseModel):
    session_id: str
    exchanges: List[QAExchangeResponse]
    total_count: int
    has_more: bool

class QASessionResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    created_at: str
    last_activity: str
    exchange_count: int

class SessionsResponse(BaseModel):
    sessions: List[QASessionResponse]
    total_count: int

app = FastAPI()

# Static files configuration
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    try:
        # Initialize database (creates tables if they don't exist)
        db_manager = init_database()
        print(f"🗄️  Database initialized successfully")
        
        # Auto-run migration if there are unmigrated JSON files
        try:
            migration_manager = MigrationManager(
                videos_directory="/app/data/videos",
                database_manager=db_manager
            )
            status = migration_manager.check_migration_status()
            
            if status["json_files_count"] > 0 and status["migrated_count"] == 0:
                print(f"🔄 Found {status['json_files_count']} unmigrated videos. Running auto-migration...")
                result = migration_manager.run_migration()
                if result["status"] == "success":
                    print(f"✅ Auto-migration completed: {result['migrated']} videos migrated")
                else:
                    print(f"⚠️  Auto-migration failed: {result.get('error', 'Unknown error')}")
            elif status["json_files_count"] > 0 and status["unmigrated_count"] > 0:
                print(f"📝 Found {status['unmigrated_count']} unmigrated videos out of {status['json_files_count']} total")
                
        except Exception as migration_error:
            print(f"⚠️  Auto-migration check failed: {migration_error}")
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        # Continue startup anyway - the app can function with JSON files only

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Knowledge Dashboard - main landing page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request
    })

@app.get("/videos", response_class=HTMLResponse)
async def videos_overview(request: Request):
    """Video library overview page"""
    videos = get_all_videos()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "videos": videos
    })

@app.get("/process", response_class=HTMLResponse)
async def process_page(request: Request, task_id: Optional[str] = Query(None)):
    """Video processing page"""
    # Check if there's an ongoing processing task
    current_processing_task = None
    if task_id and task_id in progress_store:
        current_processing_task = {
            "task_id": task_id,
            **progress_store[task_id]
        }
    
    return templates.TemplateResponse("process.html", {
        "request": request,
        "current_task": current_processing_task
    })

@app.post("/process")
async def process_video(url: str = Form(...)):
    api_key = get_api_key()
    if not api_key:
        return JSONResponse({"error": "Please configure your ElevenLabs API key in settings"}, status_code=400)
    
    task_id = str(uuid.uuid4())
    # Start download + transcribe in background
    asyncio.create_task(process_and_transcribe(url, task_id, api_key))
    return JSONResponse({"task_id": task_id, "redirect_url": f"/process?task_id={task_id}"})

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
    # ElevenLabs API key
    api_key = get_api_key()
    api_key_masked = f"sk-...{api_key[-4:]}" if api_key and len(api_key) > 4 else ""
    has_key = bool(api_key)
    
    # OpenAI API key
    openai_key = get_openai_api_key()
    openai_key_masked = f"sk-...{openai_key[-4:]}" if openai_key and len(openai_key) > 4 else ""
    has_openai_key = bool(openai_key)
    
    # Model configuration
    model_config = get_model_config()
    
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "api_key_masked": api_key_masked,
        "has_key": has_key,
        "openai_key_masked": openai_key_masked,
        "has_openai_key": has_openai_key,
        "model_config": model_config
    })

@app.post("/settings/save")
async def save_settings(request: Request, api_key: str = Form(...)):
    try:
        save_api_key(api_key)
        
        # Get current state for response
        openai_key = get_openai_api_key()
        openai_key_masked = f"sk-...{openai_key[-4:]}" if openai_key and len(openai_key) > 4 else ""
        has_openai_key = bool(openai_key)
        model_config = get_model_config()
        
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "api_key_masked": f"sk-...{api_key[-4:]}" if len(api_key) > 4 else "",
            "has_key": True,
            "openai_key_masked": openai_key_masked,
            "has_openai_key": has_openai_key,
            "model_config": model_config,
            "success": "ElevenLabs API key saved successfully!"
        })
    except Exception as e:
        # Get current state for error response
        openai_key = get_openai_api_key()
        openai_key_masked = f"sk-...{openai_key[-4:]}" if openai_key and len(openai_key) > 4 else ""
        has_openai_key = bool(openai_key)
        model_config = get_model_config()
        
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "api_key_masked": "",
            "has_key": False,
            "openai_key_masked": openai_key_masked,
            "has_openai_key": has_openai_key,
            "model_config": model_config,
            "error": f"Error saving ElevenLabs API key: {str(e)}"
        })

@app.post("/settings/save-openai")
async def save_openai_settings(request: Request, openai_api_key: str = Form(...)):
    try:
        save_openai_api_key(openai_api_key)
        
        # Get current state for response
        api_key = get_api_key()
        api_key_masked = f"sk-...{api_key[-4:]}" if api_key and len(api_key) > 4 else ""
        has_key = bool(api_key)
        model_config = get_model_config()
        
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "api_key_masked": api_key_masked,
            "has_key": has_key,
            "openai_key_masked": f"sk-...{openai_api_key[-4:]}" if len(openai_api_key) > 4 else "",
            "has_openai_key": True,
            "model_config": model_config,
            "success": "OpenAI API key saved successfully!"
        })
    except Exception as e:
        # Get current state for error response
        api_key = get_api_key()
        api_key_masked = f"sk-...{api_key[-4:]}" if api_key and len(api_key) > 4 else ""
        has_key = bool(api_key)
        model_config = get_model_config()
        
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "api_key_masked": api_key_masked,
            "has_key": has_key,
            "openai_key_masked": "",
            "has_openai_key": False,
            "model_config": model_config,
            "error": f"Error saving OpenAI API key: {str(e)}"
        })

@app.post("/settings/validate-elevenlabs")
async def validate_elevenlabs_key(api_key: str = Form(...)):
    """Validate ElevenLabs API key by making a test request."""
    try:
        # Basic validation - check key format
        if not api_key or not api_key.startswith('sk-'):
            return JSONResponse({
                "valid": False,
                "error": "Invalid API key format. ElevenLabs API keys should start with 'sk-'"
            })
        
        # For now, just return success for properly formatted keys
        # In production, you could make a test API call to ElevenLabs
        return JSONResponse({
            "valid": True,
            "message": "API key format is valid"
        })
    except Exception as e:
        return JSONResponse({
            "valid": False,
            "error": f"Validation error: {str(e)}"
        })

@app.post("/settings/validate-openai")
async def validate_openai_key(openai_api_key: str = Form(...)):
    """Validate OpenAI API key by making a test request."""
    try:
        # Basic validation - check key format
        if not openai_api_key or not openai_api_key.startswith('sk-'):
            return JSONResponse({
                "valid": False,
                "error": "Invalid API key format. OpenAI API keys should start with 'sk-'"
            })
        
        # For now, just return success for properly formatted keys
        # In production, you could make a test API call to OpenAI
        return JSONResponse({
            "valid": True,
            "message": "API key format is valid"
        })
    except Exception as e:
        return JSONResponse({
            "valid": False,
            "error": f"Validation error: {str(e)}"
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
                word_count=result.word_count,
                video_title=result.video_title
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

# Q&A API Endpoints

@app.post("/api/ask", response_model=AskResponse)
async def ask_question(ask_request: AskRequest):
    """
    Ask a question and get an AI-generated answer with sources.
    
    Uses RAG (Retrieval-Augmented Generation) to find relevant context
    and generate comprehensive answers with source attribution.
    """
    try:
        # Check OpenAI API key
        if not get_openai_api_key():
            raise HTTPException(
                status_code=500,
                detail="OpenAI API key not configured. Please set it in settings."
            )
        
        # Initialize RAG service and process question
        rag_service = RAGService()
        result = rag_service.ask(
            question=ask_request.question,
            session_id=ask_request.session_id
        )
        
        # Convert sources to response format
        source_responses = [
            SourceResponse(
                video_id=source["video_id"],
                chunk_id=source["chunk_id"],
                start_ms=source["start_ms"],
                end_ms=source["end_ms"],
                text=source["text"],
                relevance_score=source["relevance_score"]
            ) for source in result.sources
        ]
        
        return AskResponse(
            question=result.question,
            answer=result.answer,
            sources=source_responses,
            confidence_score=result.confidence_score,
            response_time_ms=result.response_time_ms,
            session_id=result.session_id
        )
        
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/api/qa/history", response_model=HistoryResponse)
async def get_qa_history(
    session_id: str = Query(..., description="Session ID to get history for"),
    limit: int = Query(20, ge=1, le=100, description="Number of exchanges to return"),
    offset: int = Query(0, ge=0, description="Number of exchanges to skip")
):
    """
    Get Q&A conversation history for a specific session.
    
    Returns chronological list of questions and answers with pagination.
    """
    try:
        session = get_database_session()
        
        # Get total count
        total_count = session.query(QAExchange).filter(
            QAExchange.session_id == session_id
        ).count()
        
        # Get exchanges with pagination
        exchanges = session.query(QAExchange).filter(
            QAExchange.session_id == session_id
        ).order_by(QAExchange.timestamp).offset(offset).limit(limit).all()
        
        session.close()
        
        # Convert to response format
        exchange_responses = []
        for exchange in exchanges:
            sources = json.loads(exchange.sources) if exchange.sources else []
            
            exchange_responses.append(QAExchangeResponse(
                id=exchange.id,
                question=exchange.question,
                answer=exchange.answer,
                sources=sources,
                timestamp=exchange.timestamp.isoformat(),
                response_time_ms=exchange.response_time_ms
            ))
        
        has_more = (offset + len(exchanges)) < total_count
        
        return HistoryResponse(
            session_id=session_id,
            exchanges=exchange_responses,
            total_count=total_count,
            has_more=has_more
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Q&A history: {str(e)}"
        )

@app.post("/api/qa/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback_request: FeedbackRequest):
    """
    Submit feedback for a Q&A exchange.
    
    Allows users to rate answers and provide qualitative feedback
    to improve the system's performance.
    """
    try:
        session = get_database_session()
        
        # Verify exchange exists
        exchange = session.query(QAExchange).filter_by(
            id=feedback_request.exchange_id
        ).first()
        
        if not exchange:
            session.close()
            raise HTTPException(
                status_code=404,
                detail=f"Exchange {feedback_request.exchange_id} not found"
            )
        
        # Create feedback record
        feedback_id = f"feedback_{uuid.uuid4().hex[:12]}"
        feedback = AnswerFeedback(
            id=feedback_id,
            exchange_id=feedback_request.exchange_id,
            rating=feedback_request.rating,
            feedback_text=feedback_request.feedback_text,
            feedback_type=feedback_request.feedback_type,
            created_at=datetime.now(timezone.utc)
        )
        
        session.add(feedback)
        session.commit()
        session.close()
        
        return FeedbackResponse(
            success=True,
            feedback_id=feedback_id,
            message="Feedback submitted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit feedback: {str(e)}"
        )

@app.get("/api/qa/sessions", response_model=SessionsResponse)
async def get_qa_sessions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(20, ge=1, le=100, description="Number of sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip")
):
    """
    Get list of Q&A sessions with basic statistics.
    
    Returns sessions ordered by last activity with exchange counts.
    """
    try:
        session = get_database_session()
        
        # Build query
        query = session.query(QASession)
        if user_id:
            query = query.filter(QASession.user_id == user_id)
        
        # Get total count
        total_count = query.count()
        
        # Get sessions with pagination
        sessions = query.order_by(
            QASession.last_activity.desc()
        ).offset(offset).limit(limit).all()
        
        # Convert to response format with exchange counts
        session_responses = []
        for qa_session in sessions:
            exchange_count = session.query(QAExchange).filter(
                QAExchange.session_id == qa_session.id
            ).count()
            
            session_responses.append(QASessionResponse(
                id=qa_session.id,
                user_id=qa_session.user_id,
                created_at=qa_session.created_at.isoformat(),
                last_activity=qa_session.last_activity.isoformat(),
                exchange_count=exchange_count
            ))
        
        session.close()
        
        return SessionsResponse(
            sessions=session_responses,
            total_count=total_count
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Q&A sessions: {str(e)}"
        )

# Dashboard API Endpoints
@app.get("/api/dashboard/stats")
async def get_knowledge_stats():
    """Get knowledge base statistics for dashboard"""
    try:
        videos = get_all_videos()
        total_videos = len(videos)
        total_hours = sum(v.get('duration', 0) for v in videos) / 3600
        
        return JSONResponse({
            "total_videos": total_videos,
            "total_hours": round(total_hours, 1)
        })
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to get stats: {str(e)}"},
            status_code=500
        )

@app.get("/api/dashboard/summaries")
async def get_recent_summaries(limit: int = Query(5, ge=1, le=20)):
    """Get recent AI-generated summaries"""
    try:
        # No real summaries implemented yet - return empty list
        return JSONResponse({
            "summaries": [],
            "total_count": 0
        })
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to get summaries: {str(e)}"},
            status_code=500
        )

@app.get("/api/dashboard/topics")
async def get_topic_trends(limit: int = Query(10, ge=1, le=50)):
    """Get trending topics"""
    try:
        # No real topic analysis implemented yet - return empty list
        return JSONResponse({
            "topics": []
        })
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to get topics: {str(e)}"},
            status_code=500
        )

@app.get("/api/dashboard/entities")
async def get_entity_highlights(limit: int = Query(10, ge=1, le=50)):
    """Get key entities discovered"""
    try:
        # No real entity extraction implemented yet - return empty list
        return JSONResponse({
            "entities": []
        })
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to get entities: {str(e)}"},
            status_code=500
        )

@app.get("/api/dashboard/processing")
async def get_processing_status():
    """Get current processing status"""
    try:
        # Check actual processing status from progress store
        processing_jobs = []
        current_job = None
        
        for task_id, progress_data in progress_store.items():
            phase = progress_data.get('phase', '')
            if phase in ['downloading', 'transcribing']:
                current_job = {
                    "task_id": task_id,
                    "title": progress_data.get('metadata', {}).get('title', 'Processing...'),
                    "phase": phase,
                    "percent": progress_data.get('percent', 0),
                    "status": progress_data.get('status', ''),
                    "url": f"/process?task_id={task_id}"
                }
                processing_jobs.append(task_id)
                break  # Take the first active processing job
        
        return JSONResponse({
            "queue_length": len(processing_jobs),
            "in_progress": 1 if current_job else 0,
            "current_job": current_job
        })
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to get processing status: {str(e)}"},
            status_code=500
        )

@app.get("/api/dashboard/activity")
async def get_recent_activity(limit: int = Query(10, ge=1, le=50)):
    """Get recent user activity"""
    try:
        # No real activity tracking implemented yet - return empty list
        return JSONResponse({
            "activities": []
        })
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to get activity: {str(e)}"},
            status_code=500
        )

@app.get("/api/videos/recent")
async def get_recent_videos(limit: int = Query(5, ge=1, le=20)):
    """Get recent processed videos"""
    try:
        videos = get_all_videos()
        # Get the most recent videos (they're already sorted by date)
        recent_videos = videos[:limit]
        
        # Transform to simpler format for dashboard
        simplified_videos = []
        for video in recent_videos:
            simplified_videos.append({
                "id": video.get("task_id"),
                "title": video.get("title", "Unknown Title"),
                "created_at": video.get("processed_date", video.get("upload_date", "")),
                "duration": video.get("duration", 0)
            })
        
        return JSONResponse({
            "videos": simplified_videos,
            "total_count": len(videos)
        })
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to get recent videos: {str(e)}"},
            status_code=500
        )

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