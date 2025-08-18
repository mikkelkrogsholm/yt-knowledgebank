"""
RAG (Retrieval-Augmented Generation) Service for YouTube Knowledgebank.

This module orchestrates the complete RAG pipeline: question processing,
context retrieval, answer generation, and result persistence.

Phase 4 Module 1: RAG Pipeline Orchestration
"""
import json
import uuid
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from app.database import get_database_session, QASession, QAExchange
from app.search import SearchManager
from app.context_assembler import ContextAssembler
from app.answer_generator import AnswerGenerator
from app.settings import get_openai_api_key


@dataclass
class RAGResult:
    """Represents the result of a RAG pipeline execution."""
    question: str
    answer: str
    sources: List[Dict[str, Any]]
    confidence_score: float
    response_time_ms: int
    session_id: Optional[str] = None
    context_length: int = 0


class RAGService:
    """
    Main RAG service that orchestrates the complete question-answering pipeline.
    
    Combines search, context assembly, answer generation, and persistence
    to provide comprehensive question-answering capabilities.
    """
    
    def __init__(self):
        """Initialize the RAG service with all required components."""
        # Verify OpenAI API key is configured
        api_key = get_openai_api_key()
        if not api_key:
            raise ValueError("OpenAI API key not configured. Please set it in settings.")
        
        # Initialize pipeline components
        self.search_manager = SearchManager()
        self.context_assembler = ContextAssembler()
        self.answer_generator = AnswerGenerator()
        
        # Configuration
        self.max_search_results = 10
        self.max_context_tokens = 2000
        self.confidence_threshold = 0.3
    
    def ask(self, question: str, session_id: Optional[str] = None, 
            user_id: Optional[str] = None) -> RAGResult:
        """
        Process a question through the complete RAG pipeline.
        
        Args:
            question: The question to answer
            session_id: Optional session ID for conversational context
            user_id: Optional user ID for session tracking
            
        Returns:
            RAGResult with answer, sources, and metadata
        """
        start_time = time.time()
        
        # Validate inputs
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        
        question = question.strip()
        
        try:
            # Step 1: Retrieve relevant context through search
            search_results = self.search_manager.search(
                query=question,
                limit=self.max_search_results
            )
            
            if not search_results:
                return self._create_no_results_response(question, session_id, start_time)
            
            # Step 2: Assemble context from search results
            context = self.context_assembler.assemble_context(
                search_results, 
                max_tokens=self.max_context_tokens
            )
            
            # Step 3: Get conversation history if session exists
            conversation_history = []
            if session_id:
                conversation_history = self._get_conversation_history(session_id)
            
            # Step 4: Generate answer using context
            generated_answer = self.answer_generator.generate_answer(
                question=question,
                context=context,
                sources=self._format_sources(search_results),
                conversation_history=conversation_history
            )
            
            # Step 5: Calculate response time
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)
            
            # Step 6: Create result
            result = RAGResult(
                question=question,
                answer=generated_answer.answer,
                sources=self._format_sources_for_response(search_results),
                confidence_score=generated_answer.confidence,
                response_time_ms=response_time_ms,
                session_id=session_id,
                context_length=len(context.split())
            )
            
            # Step 7: Persist the exchange
            if session_id is None:
                session_id = self.start_session(user_id=user_id)
                result.session_id = session_id
            
            self._persist_exchange(result, context, generated_answer.citations)
            
            return result
            
        except Exception as e:
            # Log error and return error response
            print(f"RAG pipeline error: {e}")
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)
            
            return RAGResult(
                question=question,
                answer=f"I apologize, but I encountered an error while processing your question: {str(e)}",
                sources=[],
                confidence_score=0.0,
                response_time_ms=response_time_ms,
                session_id=session_id,
                context_length=0
            )
    
    def start_session(self, user_id: Optional[str] = None) -> str:
        """
        Start a new Q&A session.
        
        Args:
            user_id: Optional user identifier
            
        Returns:
            Session ID
        """
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        
        session = get_database_session()
        try:
            qa_session = QASession(
                id=session_id,
                user_id=user_id,
                created_at=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc)
            )
            
            session.add(qa_session)
            session.commit()
            
            return session_id
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_session_history(self, session_id: str, limit: int = 20, 
                          offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of exchanges to return
            offset: Number of exchanges to skip
            
        Returns:
            List of exchange dictionaries
        """
        session = get_database_session()
        try:
            exchanges = session.query(QAExchange).filter(
                QAExchange.session_id == session_id
            ).order_by(QAExchange.timestamp).offset(offset).limit(limit).all()
            
            history = []
            for exchange in exchanges:
                history.append({
                    "id": exchange.id,
                    "question": exchange.question,
                    "answer": exchange.answer,
                    "sources": json.loads(exchange.sources) if exchange.sources else [],
                    "timestamp": exchange.timestamp.isoformat(),
                    "response_time_ms": exchange.response_time_ms
                })
            
            return history
            
        finally:
            session.close()
    
    def _get_conversation_history(self, session_id: str, limit: int = 5) -> List[Dict[str, str]]:
        """
        Get recent conversation history formatted for OpenAI.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of recent exchanges
            
        Returns:
            List of conversation messages
        """
        session = get_database_session()
        try:
            exchanges = session.query(QAExchange).filter(
                QAExchange.session_id == session_id
            ).order_by(QAExchange.timestamp.desc()).limit(limit).all()
            
            # Reverse to get chronological order
            exchanges = list(reversed(exchanges))
            
            conversation = []
            for exchange in exchanges:
                conversation.extend([
                    {"role": "user", "content": exchange.question},
                    {"role": "assistant", "content": exchange.answer}
                ])
            
            return conversation
            
        finally:
            session.close()
    
    def _format_sources(self, search_results) -> List[Dict[str, Any]]:
        """Format search results as sources for answer generation."""
        sources = []
        for result in search_results:
            sources.append({
                "chunk_id": result.id,
                "video_id": result.video_id,
                "text": result.text,
                "start_ms": result.start_ms,
                "end_ms": result.end_ms,
                "relevance_score": result.rank
            })
        return sources
    
    def _format_sources_for_response(self, search_results) -> List[Dict[str, Any]]:
        """Format search results for API response."""
        sources = []
        for result in search_results:
            sources.append({
                "video_id": result.video_id,
                "chunk_id": result.id,
                "start_ms": result.start_ms,
                "end_ms": result.end_ms,
                "text": result.text[:200] + "..." if len(result.text) > 200 else result.text,
                "relevance_score": float(result.rank)
            })
        return sources
    
    def _create_no_results_response(self, question: str, session_id: Optional[str], 
                                  start_time: float) -> RAGResult:
        """Create response when no search results are found."""
        end_time = time.time()
        response_time_ms = int((end_time - start_time) * 1000)
        
        return RAGResult(
            question=question,
            answer="I couldn't find any relevant information in the knowledge base to answer your question. Please try rephrasing your question or asking about different topics covered in the videos.",
            sources=[],
            confidence_score=0.0,
            response_time_ms=response_time_ms,
            session_id=session_id,
            context_length=0
        )
    
    def _persist_exchange(self, result: RAGResult, context: str, citations: List[Dict]):
        """Persist the Q&A exchange to the database."""
        session = get_database_session()
        try:
            exchange_id = f"exchange_{uuid.uuid4().hex[:12]}"
            
            # Update session last activity
            qa_session = session.query(QASession).filter_by(id=result.session_id).first()
            if qa_session:
                qa_session.last_activity = datetime.now(timezone.utc)
            
            # Create exchange record
            exchange = QAExchange(
                id=exchange_id,
                session_id=result.session_id,
                question=result.question,
                answer=result.answer,
                sources=json.dumps(result.sources),
                context_used=context,
                response_time_ms=result.response_time_ms,
                model_used=self.answer_generator.model,
                timestamp=datetime.now(timezone.utc)
            )
            
            session.add(exchange)
            session.commit()
            
        except Exception as e:
            session.rollback()
            print(f"Error persisting exchange: {e}")
        finally:
            session.close()


def ask_question(question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Standalone function for asking questions through RAG pipeline.
    
    This is a convenience function that can be used independently
    of the RAGService class.
    
    Args:
        question: Question to ask
        session_id: Optional session ID for context
        
    Returns:
        Dictionary with answer and metadata
    """
    rag_service = RAGService()
    result = rag_service.ask(question, session_id=session_id)
    
    return {
        "question": result.question,
        "answer": result.answer,
        "sources": result.sources,
        "confidence_score": result.confidence_score,
        "response_time_ms": result.response_time_ms,
        "session_id": result.session_id
    }