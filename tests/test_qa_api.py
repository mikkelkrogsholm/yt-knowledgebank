"""
Tests for Q&A API endpoints.

This test suite covers the FastAPI endpoints for the question-answering system,
testing request/response handling, validation, and integration with the RAG pipeline.

Phase 4 Module 1: Q&A API Integration
"""
import pytest
import json
import time
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_database, get_database_session, QASession, QAExchange, AnswerFeedback
from app.rag_service import RAGResult


class TestQAAPIEndpoints:
    """Test Q&A API endpoints functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def setup_database(self, tmp_path):
        """Set up test database."""
        db_path = tmp_path / "test_qa_api.db"
        db_manager = init_database(f"sqlite:///{db_path}")
        return db_manager
    
    @patch('app.rag_service.RAGService')
    def test_ask_question_endpoint(self, mock_rag_service, client, setup_database):
        """Test POST /api/ask endpoint."""
        # Mock RAG service response
        mock_rag = Mock()
        mock_result = RAGResult(
            question="What is machine learning?",
            answer="Machine learning is a subset of AI that enables computers to learn from data.",
            sources=[
                {
                    "video_id": "test_video_1",
                    "chunk_id": 1,
                    "start_ms": 0,
                    "end_ms": 5000,
                    "text": "Machine learning is...",
                    "relevance_score": 0.95
                }
            ],
            confidence_score=0.92,
            response_time_ms=1200,
            session_id="session_123"
        )
        mock_rag.ask.return_value = mock_result
        mock_rag_service.return_value = mock_rag
        
        # Make request
        response = client.post("/api/ask", json={
            "question": "What is machine learning?",
            "session_id": None
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["question"] == "What is machine learning?"
        assert data["answer"] == "Machine learning is a subset of AI that enables computers to learn from data."
        assert len(data["sources"]) == 1
        assert data["confidence_score"] == 0.92
        assert data["response_time_ms"] == 1200
        assert "session_id" in data
    
    @patch('app.rag_service.RAGService')
    def test_ask_question_with_session_context(self, mock_rag_service, client, setup_database):
        """Test asking question with existing session context."""
        mock_rag = Mock()
        mock_result = RAGResult(
            question="How does it work?",
            answer="It works by using algorithms to find patterns in data and make predictions.",
            sources=[{"video_id": "test_video_1", "chunk_id": 2, "relevance_score": 0.88}],
            confidence_score=0.89,
            response_time_ms=1100,
            session_id="existing_session_456"
        )
        mock_rag.ask.return_value = mock_result
        mock_rag_service.return_value = mock_rag
        
        response = client.post("/api/ask", json={
            "question": "How does it work?",
            "session_id": "existing_session_456"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["session_id"] == "existing_session_456"
        assert data["question"] == "How does it work?"
        assert "works by using algorithms" in data["answer"]
    
    def test_ask_question_validation(self, client, setup_database):
        """Test request validation for ask endpoint."""
        # Empty question
        response = client.post("/api/ask", json={
            "question": "",
            "session_id": None
        })
        assert response.status_code == 422
        
        # Missing question
        response = client.post("/api/ask", json={
            "session_id": None
        })
        assert response.status_code == 422
        
        # Invalid JSON
        response = client.post("/api/ask", data="invalid json")
        assert response.status_code == 422
    
    @patch('app.rag_service.RAGService')
    def test_ask_question_performance_monitoring(self, mock_rag_service, client, setup_database):
        """Test that response times are properly tracked."""
        mock_rag = Mock()
        mock_result = RAGResult(
            question="Test question",
            answer="Test answer",
            sources=[],
            confidence_score=0.85,
            response_time_ms=2800,  # Just under 3 second limit
            session_id="perf_session"
        )
        mock_rag.ask.return_value = mock_result
        mock_rag_service.return_value = mock_rag
        
        start_time = time.time()
        response = client.post("/api/ask", json={
            "question": "Test question",
            "session_id": None
        })
        end_time = time.time()
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response time tracking
        assert data["response_time_ms"] == 2800
        assert (end_time - start_time) * 1000 < 3000  # Total API response time
    
    def test_get_qa_history_endpoint(self, client, setup_database):
        """Test GET /api/qa/history endpoint."""
        # Create test session and exchanges
        session = get_database_session()
        
        qa_session = QASession(id="history_session", user_id="test_user")
        session.add(qa_session)
        
        exchanges = [
            QAExchange(
                id="exchange_1",
                session_id="history_session",
                question="What is AI?",
                answer="AI is artificial intelligence...",
                sources='[{"video_id": "video1", "chunk_id": 1}]',
                response_time_ms=1000
            ),
            QAExchange(
                id="exchange_2", 
                session_id="history_session",
                question="How does machine learning work?",
                answer="Machine learning works by...",
                sources='[{"video_id": "video1", "chunk_id": 2}]',
                response_time_ms=1200
            )
        ]
        
        for exchange in exchanges:
            session.add(exchange)
        
        session.commit()
        session.close()
        
        # Test endpoint
        response = client.get("/api/qa/history?session_id=history_session")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["exchanges"]) == 2
        assert data["exchanges"][0]["question"] == "What is AI?"
        assert data["exchanges"][1]["question"] == "How does machine learning work?"
        assert data["session_id"] == "history_session"
    
    def test_get_qa_history_pagination(self, client, setup_database):
        """Test Q&A history with pagination."""
        # Create test session with many exchanges
        session = get_database_session()
        
        qa_session = QASession(id="paginated_session")
        session.add(qa_session)
        
        # Create 25 exchanges
        for i in range(25):
            exchange = QAExchange(
                id=f"exchange_{i}",
                session_id="paginated_session", 
                question=f"Question {i}",
                answer=f"Answer {i}",
                response_time_ms=1000
            )
            session.add(exchange)
        
        session.commit()
        session.close()
        
        # Test pagination
        response = client.get("/api/qa/history?session_id=paginated_session&limit=10&offset=0")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["exchanges"]) == 10
        assert data["total_count"] == 25
        assert data["has_more"] == True
        
        # Test second page
        response = client.get("/api/qa/history?session_id=paginated_session&limit=10&offset=10")
        data = response.json()
        
        assert len(data["exchanges"]) == 10
        assert data["has_more"] == True
    
    def test_submit_feedback_endpoint(self, client, setup_database):
        """Test POST /api/qa/feedback endpoint."""
        # Create test exchange first
        session = get_database_session()
        
        qa_session = QASession(id="feedback_session")
        session.add(qa_session)
        
        exchange = QAExchange(
            id="feedback_exchange",
            session_id="feedback_session",
            question="Test question",
            answer="Test answer"
        )
        session.add(exchange)
        session.commit()
        session.close()
        
        # Submit feedback
        response = client.post("/api/qa/feedback", json={
            "exchange_id": "feedback_exchange",
            "rating": 4,
            "feedback_text": "Good answer, very helpful",
            "feedback_type": "helpful"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["feedback_id"] is not None
        
        # Verify feedback was stored
        session = get_database_session()
        feedback = session.query(AnswerFeedback).filter_by(exchange_id="feedback_exchange").first()
        
        assert feedback is not None
        assert feedback.rating == 4
        assert feedback.feedback_text == "Good answer, very helpful"
        assert feedback.feedback_type == "helpful"
        
        session.close()
    
    def test_submit_feedback_validation(self, client, setup_database):
        """Test feedback submission validation."""
        # Invalid rating (out of range)
        response = client.post("/api/qa/feedback", json={
            "exchange_id": "test_exchange",
            "rating": 6,  # Should be 1-5
            "feedback_type": "helpful"
        })
        assert response.status_code == 422
        
        # Missing exchange_id
        response = client.post("/api/qa/feedback", json={
            "rating": 4,
            "feedback_type": "helpful"
        })
        assert response.status_code == 422
        
        # Non-existent exchange
        response = client.post("/api/qa/feedback", json={
            "exchange_id": "non_existent",
            "rating": 4
        })
        assert response.status_code == 404
    
    def test_get_qa_sessions_endpoint(self, client, setup_database):
        """Test GET /api/qa/sessions endpoint."""
        # Create test sessions
        session = get_database_session()
        
        sessions = [
            QASession(id="session_1", user_id="user_1"),
            QASession(id="session_2", user_id="user_1"),
            QASession(id="session_3", user_id="user_2")
        ]
        
        for qa_session in sessions:
            session.add(qa_session)
        
        # Add some exchanges to sessions
        exchanges = [
            QAExchange(id="ex_1", session_id="session_1", question="Q1", answer="A1"),
            QAExchange(id="ex_2", session_id="session_1", question="Q2", answer="A2"),
            QAExchange(id="ex_3", session_id="session_2", question="Q3", answer="A3")
        ]
        
        for exchange in exchanges:
            session.add(exchange)
        
        session.commit()
        session.close()
        
        # Test endpoint
        response = client.get("/api/qa/sessions?user_id=user_1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["sessions"]) == 2
        assert data["sessions"][0]["id"] in ["session_1", "session_2"]
        assert data["sessions"][0]["exchange_count"] in [2, 1]  # session_1 has 2, session_2 has 1
    
    def test_qa_error_handling(self, client, setup_database):
        """Test error handling in Q&A endpoints."""
        # Test with missing OpenAI API key
        with patch('app.settings.get_openai_api_key', return_value=None):
            response = client.post("/api/ask", json={
                "question": "Test question"
            })
            
            assert response.status_code == 500
            data = response.json()
            assert "OpenAI API key not configured" in data["detail"]
        
        # Test with service failure
        with patch('app.rag_service.RAGService') as mock_service:
            mock_service.side_effect = Exception("Service unavailable")
            
            response = client.post("/api/ask", json={
                "question": "Test question"
            })
            
            assert response.status_code == 500


class TestQAAPIModels:
    """Test Pydantic models for Q&A API."""
    
    def test_ask_request_model(self):
        """Test AskRequest Pydantic model."""
        # This will be implemented with the API endpoints
        # For now, we're testing the expected structure
        pass
    
    def test_ask_response_model(self):
        """Test AskResponse Pydantic model."""
        # This will be implemented with the API endpoints
        pass
    
    def test_feedback_request_model(self):
        """Test FeedbackRequest Pydantic model."""
        pass
    
    def test_history_response_model(self):
        """Test HistoryResponse Pydantic model."""
        pass


class TestQAAPIIntegration:
    """Integration tests for Q&A API with full pipeline."""
    
    @pytest.fixture
    def setup_full_environment(self, tmp_path):
        """Set up complete test environment."""
        db_path = tmp_path / "test_qa_integration.db" 
        db_manager = init_database(f"sqlite:///{db_path}")
        
        # Set up test data similar to RAG pipeline tests
        from app.database import Video, TranscriptChunk
        
        session = get_database_session()
        
        video = Video(
            id="api_test_video",
            title="API Test Video",
            duration=1800,
            uploader="Test Channel", 
            url="https://youtube.com/watch?v=apitest",
            video_id="apitest",
            processed_date=datetime.now(timezone.utc)
        )
        session.add(video)
        
        chunks = [
            TranscriptChunk(
                video_id="api_test_video",
                start_ms=0,
                end_ms=5000,
                speaker_id="speaker_0",
                text="Machine learning algorithms can automatically improve through experience and data analysis.",
                word_count=12
            ),
            TranscriptChunk(
                video_id="api_test_video",
                start_ms=5000,
                end_ms=10000,
                speaker_id="speaker_0",
                text="Neural networks are inspired by biological neural networks and can solve complex problems.",
                word_count=14
            )
        ]
        
        for chunk in chunks:
            session.add(chunk)
        
        session.commit()
        session.close()
        
        return db_manager
    
    @patch('openai.ChatCompletion.create')
    def test_full_api_integration_flow(self, mock_openai, setup_full_environment):
        """Test complete flow from API request to database persistence."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "answer": "Machine learning algorithms automatically improve through experience by analyzing data patterns and adjusting their internal parameters.",
            "confidence": 0.91,
            "citations": [{"chunk_id": 1, "relevance": "high"}]
        })
        mock_openai.return_value = mock_response
        
        client = TestClient(app)
        
        # First question
        response1 = client.post("/api/ask", json={
            "question": "How do machine learning algorithms improve?"
        })
        
        assert response1.status_code == 200
        data1 = response1.json()
        session_id = data1["session_id"]
        
        # Follow-up question
        response2 = client.post("/api/ask", json={
            "question": "What about neural networks?",
            "session_id": session_id
        })
        
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["session_id"] == session_id
        
        # Check history
        history_response = client.get(f"/api/qa/history?session_id={session_id}")
        assert history_response.status_code == 200
        history_data = history_response.json()
        
        assert len(history_data["exchanges"]) == 2
        assert history_data["exchanges"][0]["question"] == "How do machine learning algorithms improve?"
        assert history_data["exchanges"][1]["question"] == "What about neural networks?"
        
        # Submit feedback
        exchange_id = history_data["exchanges"][0]["id"]
        feedback_response = client.post("/api/qa/feedback", json={
            "exchange_id": exchange_id,
            "rating": 5,
            "feedback_text": "Excellent explanation!",
            "feedback_type": "accurate"
        })
        
        assert feedback_response.status_code == 200
        assert feedback_response.json()["success"] == True