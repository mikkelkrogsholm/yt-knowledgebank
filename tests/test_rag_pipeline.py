"""
Tests for RAG (Retrieval-Augmented Generation) pipeline implementation.

This test suite follows TDD principles - these tests should fail initially
and pass once the RAG components are implemented.

Phase 4 Module 1: Question-Answering System
"""
import pytest
import json
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from app.database import (
    init_database, get_database_session, 
    QASession, QAExchange, AnswerFeedback,
    Video, TranscriptChunk
)
from app.rag_service import RAGService, RAGResult
from app.context_assembler import ContextAssembler, ContextChunk
from app.answer_generator import AnswerGenerator, GeneratedAnswer


class TestRAGService:
    """Test the main RAG service orchestration."""
    
    @pytest.fixture
    def setup_database(self, tmp_path):
        """Set up test database with sample data."""
        db_path = tmp_path / "test_rag.db"
        db_manager = init_database(f"sqlite:///{db_path}")
        
        session = get_database_session()
        
        # Create test video
        video = Video(
            id="test_video_1",
            title="Test Video About AI",
            duration=3600,
            uploader="Test Channel",
            url="https://youtube.com/watch?v=test1",
            video_id="test1",
            processed_date=datetime.now(timezone.utc)
        )
        session.add(video)
        
        # Create test transcript chunks
        chunks = [
            TranscriptChunk(
                video_id="test_video_1",
                start_ms=0,
                end_ms=5000,
                speaker_id="speaker_0",
                text="Machine learning is a subset of artificial intelligence that enables computers to learn without being explicitly programmed.",
                word_count=18
            ),
            TranscriptChunk(
                video_id="test_video_1", 
                start_ms=5000,
                end_ms=10000,
                speaker_id="speaker_0",
                text="Deep learning uses neural networks with multiple layers to process data and make decisions.",
                word_count=15
            ),
            TranscriptChunk(
                video_id="test_video_1",
                start_ms=10000,
                end_ms=15000,
                speaker_id="speaker_0",
                text="The transformer architecture revolutionized natural language processing with attention mechanisms.",
                word_count=12
            )
        ]
        
        for chunk in chunks:
            session.add(chunk)
        
        session.commit()
        session.close()
        
        return db_manager
    
    def test_rag_service_initialization(self, setup_database):
        """Test RAG service can be initialized properly."""
        rag_service = RAGService()
        
        assert rag_service is not None
        assert hasattr(rag_service, 'context_assembler')
        assert hasattr(rag_service, 'answer_generator')
        assert hasattr(rag_service, 'search_manager')
    
    def test_rag_service_ask_question(self, setup_database):
        """Test asking a question through RAG pipeline."""
        rag_service = RAGService()
        
        question = "What is machine learning?"
        result = rag_service.ask(question)
        
        assert isinstance(result, RAGResult)
        assert result.question == question
        assert len(result.answer) > 0
        assert len(result.sources) > 0
        assert result.response_time_ms > 0
        assert result.confidence_score >= 0.0
        assert result.confidence_score <= 1.0
    
    def test_rag_service_conversational_context(self, setup_database):
        """Test conversational follow-up with session context."""
        rag_service = RAGService()
        
        # First question
        session_id = rag_service.start_session()
        result1 = rag_service.ask("What is machine learning?", session_id=session_id)
        
        # Follow-up question with context
        result2 = rag_service.ask("How does it differ from traditional programming?", session_id=session_id)
        
        assert result2.session_id == session_id
        assert len(result2.answer) > 0
        # Follow-up should reference previous context
        assert result2.context_length > result1.context_length
    
    def test_rag_service_performance_requirements(self, setup_database):
        """Test RAG service meets performance requirements."""
        rag_service = RAGService()
        
        question = "Explain deep learning and neural networks"
        start_time = time.time()
        
        result = rag_service.ask(question)
        
        end_time = time.time()
        total_time_ms = (end_time - start_time) * 1000
        
        # Should complete in under 3 seconds
        assert total_time_ms < 3000
        assert result.response_time_ms < 3000
    
    def test_rag_service_source_attribution(self, setup_database):
        """Test that answers include proper source attribution."""
        rag_service = RAGService()
        
        result = rag_service.ask("What is the transformer architecture?")
        
        assert len(result.sources) > 0
        for source in result.sources:
            assert 'video_id' in source
            assert 'chunk_id' in source
            assert 'start_ms' in source
            assert 'end_ms' in source
            assert 'relevance_score' in source


class TestContextAssembler:
    """Test the context assembly component."""
    
    def test_context_assembler_initialization(self):
        """Test context assembler can be initialized."""
        assembler = ContextAssembler()
        assert assembler is not None
    
    def test_assemble_context_from_search_results(self):
        """Test assembling context from search results."""
        assembler = ContextAssembler()
        
        # Mock search results
        search_results = [
            Mock(
                id=1,
                video_id="test_video_1",
                text="Machine learning is a subset of AI",
                start_ms=0,
                end_ms=5000,
                rank=0.95
            ),
            Mock(
                id=2,
                video_id="test_video_1", 
                text="Deep learning uses neural networks",
                start_ms=5000,
                end_ms=10000,
                rank=0.88
            )
        ]
        
        context = assembler.assemble_context(search_results, max_tokens=1000)
        
        assert isinstance(context, str)
        assert len(context) > 0
        assert "Machine learning" in context
        assert "Deep learning" in context
    
    def test_context_assembler_token_limits(self):
        """Test context assembler respects token limits."""
        assembler = ContextAssembler()
        
        # Create many mock results
        search_results = []
        for i in range(50):
            search_results.append(Mock(
                id=i,
                video_id="test_video_1",
                text=f"This is a long piece of text about topic {i} " * 10,
                start_ms=i*1000,
                end_ms=(i+1)*1000,
                rank=0.9 - (i*0.01)
            ))
        
        context = assembler.assemble_context(search_results, max_tokens=500)
        
        # Should not exceed token limit
        estimated_tokens = len(context.split()) * 1.3  # Rough estimation
        assert estimated_tokens <= 600  # Some buffer for token counting differences
    
    def test_context_assembler_deduplication(self):
        """Test context assembler removes duplicate content."""
        assembler = ContextAssembler()
        
        # Mock duplicate search results
        search_results = [
            Mock(
                id=1,
                video_id="test_video_1",
                text="Machine learning is important for AI",
                start_ms=0,
                end_ms=5000,
                rank=0.95
            ),
            Mock(
                id=2,
                video_id="test_video_1",
                text="Machine learning is important for AI",  # Duplicate
                start_ms=10000,
                end_ms=15000,
                rank=0.90
            ),
            Mock(
                id=3,
                video_id="test_video_1",
                text="Deep learning is a subset of machine learning",
                start_ms=20000,
                end_ms=25000,
                rank=0.85
            )
        ]
        
        context = assembler.assemble_context(search_results)
        
        # Should only contain the text once
        assert context.count("Machine learning is important for AI") == 1
        assert "Deep learning is a subset" in context


class TestAnswerGenerator:
    """Test the answer generation component."""
    
    @patch('openai.ChatCompletion.create')
    def test_answer_generator_initialization(self, mock_openai):
        """Test answer generator can be initialized."""
        generator = AnswerGenerator()
        assert generator is not None
        assert hasattr(generator, 'model')
        assert hasattr(generator, 'temperature')
    
    @patch('openai.ChatCompletion.create')
    def test_generate_answer_from_context(self, mock_openai):
        """Test generating answer from context."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "answer": "Machine learning is a subset of artificial intelligence that enables computers to learn without explicit programming.",
            "confidence": 0.92,
            "citations": [
                {"chunk_id": 1, "relevance": "high"},
                {"chunk_id": 2, "relevance": "medium"}
            ]
        })
        mock_openai.return_value = mock_response
        
        generator = AnswerGenerator()
        
        question = "What is machine learning?"
        context = "Machine learning is a subset of artificial intelligence..."
        sources = [{"chunk_id": 1, "video_id": "test_video_1"}]
        
        result = generator.generate_answer(question, context, sources)
        
        assert isinstance(result, GeneratedAnswer)
        assert result.answer == "Machine learning is a subset of artificial intelligence that enables computers to learn without explicit programming."
        assert result.confidence == 0.92
        assert len(result.citations) == 2
    
    @patch('openai.ChatCompletion.create')
    def test_generate_answer_with_conversation_history(self, mock_openai):
        """Test generating answer with conversation context."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "answer": "It differs by learning from data rather than following explicit instructions.",
            "confidence": 0.88,
            "citations": [{"chunk_id": 1, "relevance": "high"}]
        })
        mock_openai.return_value = mock_response
        
        generator = AnswerGenerator()
        
        conversation_history = [
            {"role": "user", "content": "What is machine learning?"},
            {"role": "assistant", "content": "Machine learning is a subset of AI..."}
        ]
        
        question = "How does it differ from traditional programming?"
        context = "Traditional programming vs machine learning differences..."
        sources = [{"chunk_id": 1, "video_id": "test_video_1"}]
        
        result = generator.generate_answer(
            question, context, sources, conversation_history=conversation_history
        )
        
        assert isinstance(result, GeneratedAnswer)
        assert "differs" in result.answer.lower()
        assert result.confidence > 0.0


class TestQAModels:
    """Test the QA database models."""
    
    @pytest.fixture
    def setup_database(self, tmp_path):
        """Set up test database."""
        db_path = tmp_path / "test_qa.db"
        db_manager = init_database(f"sqlite:///{db_path}")
        return db_manager
    
    def test_qa_session_creation(self, setup_database):
        """Test creating QA session."""
        session = get_database_session()
        
        qa_session = QASession(
            id="session_123",
            user_id="user_456",
            session_token="token_789"
        )
        
        session.add(qa_session)
        session.commit()
        
        # Retrieve and verify
        retrieved = session.query(QASession).filter_by(id="session_123").first()
        assert retrieved is not None
        assert retrieved.user_id == "user_456"
        assert retrieved.session_token == "token_789"
        
        session.close()
    
    def test_qa_exchange_creation(self, setup_database):
        """Test creating QA exchange."""
        session = get_database_session()
        
        # Create session first
        qa_session = QASession(id="session_123")
        session.add(qa_session)
        session.commit()
        
        # Create exchange
        exchange = QAExchange(
            id="exchange_456",
            session_id="session_123",
            question="What is AI?",
            answer="AI is artificial intelligence...",
            sources=json.dumps([{"video_id": "test_video_1", "chunk_id": 1}]),
            response_time_ms=1500,
            model_used="gpt-5-mini"
        )
        
        session.add(exchange)
        session.commit()
        
        # Retrieve and verify
        retrieved = session.query(QAExchange).filter_by(id="exchange_456").first()
        assert retrieved is not None
        assert retrieved.question == "What is AI?"
        assert retrieved.answer == "AI is artificial intelligence..."
        assert retrieved.response_time_ms == 1500
        assert retrieved.model_used == "gpt-5-mini"
        
        session.close()
    
    def test_answer_feedback_creation(self, setup_database):
        """Test creating answer feedback."""
        session = get_database_session()
        
        # Create session and exchange first
        qa_session = QASession(id="session_123")
        session.add(qa_session)
        
        exchange = QAExchange(
            id="exchange_456",
            session_id="session_123",
            question="Test question",
            answer="Test answer"
        )
        session.add(exchange)
        session.commit()
        
        # Create feedback
        feedback = AnswerFeedback(
            id="feedback_789",
            exchange_id="exchange_456",
            rating=4,
            feedback_text="Good answer but could be more detailed",
            feedback_type="helpful"
        )
        
        session.add(feedback)
        session.commit()
        
        # Retrieve and verify
        retrieved = session.query(AnswerFeedback).filter_by(id="feedback_789").first()
        assert retrieved is not None
        assert retrieved.rating == 4
        assert retrieved.feedback_text == "Good answer but could be more detailed"
        assert retrieved.feedback_type == "helpful"
        
        session.close()
    
    def test_qa_relationships(self, setup_database):
        """Test relationships between QA models."""
        session = get_database_session()
        
        # Create full chain
        qa_session = QASession(id="session_123")
        session.add(qa_session)
        
        exchange = QAExchange(
            id="exchange_456",
            session_id="session_123",
            question="Test question",
            answer="Test answer"
        )
        session.add(exchange)
        
        feedback = AnswerFeedback(
            id="feedback_789",
            exchange_id="exchange_456",
            rating=5,
            feedback_type="accurate"
        )
        session.add(feedback)
        session.commit()
        
        # Test relationships
        retrieved_session = session.query(QASession).filter_by(id="session_123").first()
        assert len(retrieved_session.exchanges) == 1
        assert retrieved_session.exchanges[0].id == "exchange_456"
        
        retrieved_exchange = session.query(QAExchange).filter_by(id="exchange_456").first()
        assert retrieved_exchange.session.id == "session_123"
        assert len(retrieved_exchange.feedback) == 1
        assert retrieved_exchange.feedback[0].rating == 5
        
        session.close()


class TestRAGIntegration:
    """Integration tests for the complete RAG pipeline."""
    
    @pytest.fixture
    def setup_full_environment(self, tmp_path):
        """Set up complete test environment with data."""
        db_path = tmp_path / "test_integration.db"
        db_manager = init_database(f"sqlite:///{db_path}")
        
        session = get_database_session()
        
        # Create comprehensive test data
        video = Video(
            id="integration_video",
            title="Comprehensive AI Tutorial",
            duration=7200,
            uploader="AI Education",
            url="https://youtube.com/watch?v=integration",
            video_id="integration",
            processed_date=datetime.now(timezone.utc)
        )
        session.add(video)
        
        # Create rich transcript content
        chunks = [
            TranscriptChunk(
                video_id="integration_video",
                start_ms=0,
                end_ms=10000,
                speaker_id="speaker_0",
                text="Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed. It focuses on developing algorithms that can process data and make predictions.",
                word_count=32
            ),
            TranscriptChunk(
                video_id="integration_video",
                start_ms=10000,
                end_ms=20000,
                speaker_id="speaker_0", 
                text="Deep learning is a specialized subset of machine learning that uses neural networks with multiple layers. These networks can automatically learn features from data, making them particularly effective for tasks like image recognition and natural language processing.",
                word_content=38
            ),
            TranscriptChunk(
                video_id="integration_video",
                start_ms=20000,
                end_ms=30000,
                speaker_id="speaker_0",
                text="The transformer architecture, introduced in the paper 'Attention Is All You Need', revolutionized natural language processing. It uses attention mechanisms to process sequences of data in parallel, making it much more efficient than previous sequential models.",
                word_count=38
            )
        ]
        
        for chunk in chunks:
            session.add(chunk)
        
        session.commit()
        session.close()
        
        return db_manager
    
    @patch('openai.ChatCompletion.create')
    def test_full_rag_pipeline_integration(self, mock_openai, setup_full_environment):
        """Test complete RAG pipeline from question to answer."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "answer": "Machine learning is a subset of artificial intelligence that enables computers to learn from experience without explicit programming. It uses algorithms to process data and make predictions automatically.",
            "confidence": 0.94,
            "citations": [
                {"chunk_id": 1, "relevance": "high"},
                {"chunk_id": 2, "relevance": "medium"}
            ]
        })
        mock_openai.return_value = mock_response
        
        rag_service = RAGService()
        
        # Test complex question requiring multiple sources
        question = "Can you explain machine learning and how it relates to deep learning?"
        
        start_time = time.time()
        result = rag_service.ask(question)
        end_time = time.time()
        
        # Verify comprehensive result
        assert isinstance(result, RAGResult)
        assert result.question == question
        assert len(result.answer) > 50  # Substantial answer
        assert len(result.sources) >= 2  # Multiple sources
        assert result.confidence_score > 0.8  # High confidence
        assert result.response_time_ms < 3000  # Performance requirement
        assert (end_time - start_time) * 1000 < 3000  # Total time requirement
        
        # Verify source attribution
        for source in result.sources:
            assert 'video_id' in source
            assert source['video_id'] == "integration_video"
            assert 'chunk_id' in source
            assert 'relevance_score' in source
    
    def test_rag_persistence_integration(self, setup_full_environment):
        """Test that RAG results are properly persisted."""
        rag_service = RAGService()
        
        session_id = rag_service.start_session(user_id="test_user")
        question = "What is machine learning?"
        
        # Mock the generation to avoid OpenAI calls
        with patch.object(rag_service.answer_generator, 'generate_answer') as mock_generate:
            mock_generate.return_value = Mock(
                answer="Machine learning is...",
                confidence=0.9,
                citations=[{"chunk_id": 1, "relevance": "high"}]
            )
            
            result = rag_service.ask(question, session_id=session_id)
        
        # Verify persistence
        db_session = get_database_session()
        
        # Check session exists
        qa_session = db_session.query(QASession).filter_by(id=session_id).first()
        assert qa_session is not None
        assert qa_session.user_id == "test_user"
        
        # Check exchange exists
        exchanges = db_session.query(QAExchange).filter_by(session_id=session_id).all()
        assert len(exchanges) == 1
        assert exchanges[0].question == question
        assert exchanges[0].answer == "Machine learning is..."
        
        db_session.close()