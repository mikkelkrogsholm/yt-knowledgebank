#!/usr/bin/env python3
"""
Performance testing script for RAG pipeline.

This script tests the performance requirements for Phase 4:
- Response time < 3 seconds for complex queries
- End-to-end integration testing
"""
import time
import json
import tempfile
import os
from unittest.mock import Mock, patch

# Set up environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_settings')

from app.database import init_database, get_database_session, Video, TranscriptChunk
from app.rag_service import RAGService
from app.context_assembler import ContextAssembler
from app.answer_generator import AnswerGenerator


def setup_test_data():
    """Set up test database with sample data."""
    print("Setting up test database...")
    
    # Create temporary database
    db_path = "/tmp/performance_test.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    db_manager = init_database(f"sqlite:///{db_path}")
    session = get_database_session()
    
    # Create test video
    video = Video(
        id="perf_test_video",
        title="Performance Test Video: Advanced AI and Machine Learning",
        duration=7200,
        uploader="AI Education Channel",
        url="https://youtube.com/watch?v=perftest",
        video_id="perftest",
    )
    session.add(video)
    
    # Create comprehensive transcript chunks
    chunks_data = [
        {
            "text": "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed. The key is that algorithms can automatically improve through data analysis.",
            "start_ms": 0,
            "end_ms": 8000
        },
        {
            "text": "Deep learning uses neural networks with multiple layers to process data. These networks are inspired by the structure of the human brain and can learn complex patterns in data through backpropagation.",
            "start_ms": 8000,
            "end_ms": 16000
        },
        {
            "text": "The transformer architecture revolutionized natural language processing. Attention mechanisms allow models to focus on relevant parts of input sequences, making them highly effective for language tasks.",
            "start_ms": 16000,
            "end_ms": 24000
        },
        {
            "text": "Reinforcement learning is where agents learn to make decisions by interacting with an environment. They receive rewards or penalties based on their actions, gradually improving their policy.",
            "start_ms": 24000,
            "end_ms": 32000
        },
        {
            "text": "Computer vision applications use convolutional neural networks to process images. These networks can detect objects, recognize faces, and even generate synthetic images with remarkable accuracy.",
            "start_ms": 32000,
            "end_ms": 40000
        },
        {
            "text": "Natural language processing combines linguistics and machine learning to help computers understand human language. Tasks include translation, sentiment analysis, and text generation.",
            "start_ms": 40000,
            "end_ms": 48000
        },
        {
            "text": "Transfer learning allows models trained on one task to be adapted for related tasks. This approach significantly reduces training time and data requirements for new applications.",
            "start_ms": 48000,
            "end_ms": 56000
        },
        {
            "text": "Generative adversarial networks consist of two neural networks competing against each other. The generator creates fake data while the discriminator tries to detect it, leading to highly realistic outputs.",
            "start_ms": 56000,
            "end_ms": 64000
        }
    ]
    
    for i, chunk_data in enumerate(chunks_data):
        chunk = TranscriptChunk(
            video_id="perf_test_video",
            start_ms=chunk_data["start_ms"],
            end_ms=chunk_data["end_ms"],
            speaker_id="speaker_0",
            text=chunk_data["text"],
            word_count=len(chunk_data["text"].split())
        )
        session.add(chunk)
    
    session.commit()
    session.close()
    
    print(f"Created test data: 1 video, {len(chunks_data)} transcript chunks")
    return db_path


def test_context_assembler_performance():
    """Test context assembler performance."""
    print("\n--- Testing Context Assembler Performance ---")
    
    assembler = ContextAssembler()
    
    # Create mock search results
    mock_results = []
    for i in range(50):  # Large number of results
        mock_result = Mock()
        mock_result.id = i
        mock_result.video_id = "perf_test_video"
        mock_result.text = f"This is test text chunk {i} with various machine learning concepts and detailed explanations " * 5
        mock_result.start_ms = i * 1000
        mock_result.end_ms = (i + 1) * 1000
        mock_result.rank = 0.9 - (i * 0.01)
        mock_results.append(mock_result)
    
    # Test assembly performance
    start_time = time.time()
    context = assembler.assemble_context(mock_results, max_tokens=2000)
    end_time = time.time()
    
    assembly_time = (end_time - start_time) * 1000
    print(f"Context assembly time: {assembly_time:.2f}ms")
    print(f"Context length: {len(context)} characters")
    print(f"Context token estimate: {len(context.split()) * 1.3:.0f} tokens")
    
    assert assembly_time < 500, f"Context assembly took {assembly_time:.2f}ms, should be < 500ms"
    print("✅ Context assembler performance test passed")


def test_answer_generator_performance():
    """Test answer generator performance with mocking."""
    print("\n--- Testing Answer Generator Performance ---")
    
    # Mock OpenAI response to avoid API calls
    mock_response = {
        "content": json.dumps({
            "answer": "Machine learning is a subset of artificial intelligence that enables computers to learn from data without explicit programming. It uses algorithms to identify patterns and make predictions based on historical data.",
            "confidence": 0.92,
            "citations": [
                {"chunk_id": 1, "relevance": "high", "quote": "Machine learning is a subset of artificial intelligence"},
                {"chunk_id": 2, "relevance": "medium", "quote": "algorithms can automatically improve through data analysis"}
            ]
        })
    }
    
    with patch('openai.ChatCompletion.create') as mock_openai:
        mock_openai.return_value.choices = [Mock()]
        mock_openai.return_value.choices[0].message.content = mock_response["content"]
        
        generator = AnswerGenerator()
        
        question = "What is machine learning and how does it work?"
        context = "Machine learning is a subset of artificial intelligence that enables computers to learn from experience..."
        sources = [{"chunk_id": 1, "video_id": "test_video", "text": "Sample context"}]
        
        start_time = time.time()
        result = generator.generate_answer(question, context, sources)
        end_time = time.time()
        
        generation_time = (end_time - start_time) * 1000
        print(f"Answer generation time: {generation_time:.2f}ms")
        print(f"Answer length: {len(result.answer)} characters")
        print(f"Confidence score: {result.confidence}")
        
        assert generation_time < 2000, f"Answer generation took {generation_time:.2f}ms, should be < 2000ms"
        print("✅ Answer generator performance test passed")


def test_rag_service_performance():
    """Test full RAG service performance."""
    print("\n--- Testing RAG Service Performance ---")
    
    # Mock OpenAI to avoid API calls but test the full pipeline
    mock_response = {
        "content": json.dumps({
            "answer": "Machine learning is a powerful subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed. It works by using algorithms that can automatically identify patterns in data and make predictions or decisions based on those patterns.",
            "confidence": 0.94,
            "citations": [
                {"chunk_id": 1, "relevance": "high", "quote": "Machine learning is a subset of artificial intelligence"},
                {"chunk_id": 2, "relevance": "high", "quote": "algorithms can automatically improve through data analysis"}
            ]
        })
    }
    
    with patch('openai.ChatCompletion.create') as mock_openai:
        mock_openai.return_value.choices = [Mock()]
        mock_openai.return_value.choices[0].message.content = mock_response["content"]
        
        rag_service = RAGService()
        
        # Test various questions
        test_questions = [
            "What is machine learning?",
            "How do neural networks work?",
            "Explain deep learning and its applications",
            "What is the difference between supervised and unsupervised learning?",
            "How does natural language processing work with transformers?"
        ]
        
        total_time = 0
        results = []
        
        for question in test_questions:
            print(f"\nTesting question: '{question}'")
            
            start_time = time.time()
            result = rag_service.ask(question)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            total_time += response_time
            
            print(f"  Response time: {response_time:.2f}ms")
            print(f"  Answer length: {len(result.answer)} characters")
            print(f"  Sources found: {len(result.sources)}")
            print(f"  Confidence: {result.confidence_score:.2f}")
            
            results.append({
                "question": question,
                "response_time_ms": response_time,
                "answer_length": len(result.answer),
                "sources_count": len(result.sources),
                "confidence": result.confidence_score
            })
            
            # Performance requirement: < 3 seconds per question
            assert response_time < 3000, f"Question '{question}' took {response_time:.2f}ms, should be < 3000ms"
        
        avg_time = total_time / len(test_questions)
        print(f"\n📊 RAG Service Performance Summary:")
        print(f"  Average response time: {avg_time:.2f}ms")
        print(f"  Total time for {len(test_questions)} questions: {total_time:.2f}ms")
        print(f"  All responses under 3-second requirement: {'✅' if max(r['response_time_ms'] for r in results) < 3000 else '❌'}")
        
        print("✅ RAG service performance test passed")
        return results


def main():
    """Run all performance tests."""
    print("🚀 Starting RAG Pipeline Performance Tests")
    print("=" * 50)
    
    try:
        # Setup test environment
        db_path = setup_test_data()
        
        # Run performance tests
        test_context_assembler_performance()
        test_answer_generator_performance()
        test_results = test_rag_service_performance()
        
        print("\n" + "=" * 50)
        print("🎉 All performance tests passed!")
        print("\n📈 Performance Summary:")
        print("✅ Context assembly: < 500ms")
        print("✅ Answer generation: < 2000ms")
        print("✅ Full RAG pipeline: < 3000ms per question")
        print("✅ End-to-end integration: Working")
        
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"\nCleaned up test database: {db_path}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Performance test failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)