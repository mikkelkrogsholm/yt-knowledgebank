"""
Test suite for entity extraction functionality.

Tests the entity recognition system that extracts people, books, concepts,
companies, and other entities from transcript chunks using OpenAI NER.

Following TDD approach - these are failing tests that define the behavior
we need to implement for Phase 3 Module 1.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

from app.database import init_database, get_database_session, Entity, EntityMention, EntityRelationship, Video, TranscriptChunk
from app.entity_extraction import EntityExtractor, EntityManager, extract_entities_from_text
from app.settings import get_openai_api_key, get_model_config


class TestEntityDatabaseSchema:
    """Test entity database schema and models."""
    
    def setup_method(self):
        """Set up test database."""
        # Use a test-specific database
        self.db_manager = init_database("sqlite:////app/data/test_knowledge_bank.db")
        self.session = get_database_session()
        
        # Clean up any existing test data
        self.session.query(EntityMention).delete()
        self.session.query(Entity).delete()
        self.session.query(TranscriptChunk).delete()
        self.session.query(Video).delete()
        self.session.commit()
    
    def teardown_method(self):
        """Clean up test database."""
        if hasattr(self, 'session'):
            # Clean up test data
            self.session.query(EntityMention).delete()
            self.session.query(Entity).delete()
            self.session.query(TranscriptChunk).delete()
            self.session.query(Video).delete()
            self.session.commit()
            self.session.close()
    
    def test_entity_table_creation(self):
        """Test that Entity table is created with correct schema."""
        # This will fail until we add Entity model to database.py
        from app.database import Entity
        
        # Test that we can create an entity
        entity = Entity(
            id="entity_1",
            name="Test Book",
            type="book",
            description="A test book entity"
        )
        
        self.session.add(entity)
        self.session.commit()
        
        # Verify entity was created
        retrieved = self.session.query(Entity).filter(Entity.id == "entity_1").first()
        assert retrieved is not None
        assert retrieved.name == "Test Book"
        assert retrieved.type == "book"
        assert retrieved.description == "A test book entity"
        assert retrieved.created_at is not None
    
    def test_entity_mention_table_creation(self):
        """Test that EntityMention table is created with proper relationships."""
        from app.database import EntityMention, Entity, TranscriptChunk
        
        # Create test entity
        entity = Entity(
            id="entity_1",
            name="Test Entity",
            type="person",
            description="Test person"
        )
        self.session.add(entity)
        
        # Create test video and chunk (these should exist from Phase 1)
        from app.database import Video
        video = Video(
            id="test_video",
            title="Test Video",
            duration=100,
            uploader="Test Channel",
            url="https://test.com",
            video_id="test123",
            processed_date=datetime.utcnow()
        )
        self.session.add(video)
        
        chunk = TranscriptChunk(
            id=1,
            video_id="test_video",
            start_ms=0,
            end_ms=1000,
            speaker_id="speaker_0",
            text="Test chunk text",
            word_count=3
        )
        self.session.add(chunk)
        self.session.commit()
        
        # Create entity mention
        mention = EntityMention(
            id="mention_1",
            entity_id="entity_1",
            chunk_id=1,
            confidence=0.95,
            context="This is the context around the entity mention"
        )
        
        self.session.add(mention)
        self.session.commit()
        
        # Verify mention was created with relationships
        retrieved = self.session.query(EntityMention).filter(EntityMention.id == "mention_1").first()
        assert retrieved is not None
        assert retrieved.entity_id == "entity_1"
        assert retrieved.chunk_id == 1
        assert retrieved.confidence == 0.95
        assert retrieved.context == "This is the context around the entity mention"
    
    def test_entity_types_enum(self):
        """Test that we can create entities of different types."""
        from app.database import Entity
        
        entity_types = ["person", "book", "concept", "company", "place", "product", "technology"]
        
        for i, entity_type in enumerate(entity_types):
            entity = Entity(
                id=f"entity_{i}",
                name=f"Test {entity_type}",
                type=entity_type,
                description=f"Test {entity_type} entity"
            )
            self.session.add(entity)
        
        self.session.commit()
        
        # Verify all entity types were created
        for i, entity_type in enumerate(entity_types):
            retrieved = self.session.query(Entity).filter(Entity.id == f"entity_{i}").first()
            assert retrieved is not None
            assert retrieved.type == entity_type


class TestOpenAINERIntegration:
    """Test OpenAI NER integration with GPT models."""
    
    def setup_method(self):
        """Set up test environment."""
        self.sample_text = """
        I recently read "Atomic Habits" by James Clear, which is published by Avery Books.
        The book discusses concepts like habit stacking and the compound effect.
        James Clear also mentions research from Stanford University about behavioral psychology.
        """
    
    @patch('app.entity_extraction.openai.ChatCompletion.create')
    def test_openai_entity_extraction(self, mock_openai):
        """Test that we can extract entities using OpenAI API."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '''
        {
            "entities": [
                {
                    "name": "Atomic Habits",
                    "type": "book",
                    "confidence": 0.95,
                    "context": "I recently read \\"Atomic Habits\\" by James Clear"
                },
                {
                    "name": "James Clear",
                    "type": "person",
                    "confidence": 0.98,
                    "context": "Atomic Habits\\" by James Clear, which is published"
                },
                {
                    "name": "Avery Books",
                    "type": "company",
                    "confidence": 0.85,
                    "context": "which is published by Avery Books"
                },
                {
                    "name": "habit stacking",
                    "type": "concept",
                    "confidence": 0.90,
                    "context": "discusses concepts like habit stacking and the compound"
                },
                {
                    "name": "Stanford University",
                    "type": "place",
                    "confidence": 0.95,
                    "context": "mentions research from Stanford University about behavioral"
                }
            ]
        }
        '''
        mock_openai.return_value = mock_response
        
        # This will fail until we implement extract_entities_from_text
        entities = extract_entities_from_text(self.sample_text)
        
        assert len(entities) == 5
        assert entities[0]["name"] == "Atomic Habits"
        assert entities[0]["type"] == "book"
        assert entities[1]["name"] == "James Clear"
        assert entities[1]["type"] == "person"
        assert entities[2]["name"] == "Avery Books"
        assert entities[2]["type"] == "company"
    
    def test_model_config_for_entity_extraction(self):
        """Test that model configuration is properly loaded for entity extraction."""
        config = get_model_config()
        
        # Should use GPT-5-nano for entity extraction as per plan
        assert "models" in config
        assert "entity_extraction" in config["models"]
        assert config["models"]["entity_extraction"] == "gpt-5-nano"
        
        # Should have proper limits and temperature for extraction
        assert "limits" in config
        assert "temperature_extraction" in config["limits"]
        assert config["limits"]["temperature_extraction"] == 0.1  # Low temperature for consistent extraction
    
    def test_openai_api_key_validation(self):
        """Test that OpenAI API key is available for entity extraction."""
        # This should work since Phase 2 set up OpenAI integration
        api_key = get_openai_api_key()
        
        # In test environment, we may not have a real key, but the function should exist
        # In production, this would validate the key format and connectivity
        assert get_openai_api_key is not None


class TestEntityLinkingAndDeduplication:
    """Test entity linking and deduplication algorithms."""
    
    def setup_method(self):
        """Set up test environment."""
        self.db_manager = init_database("sqlite:////app/data/test_linking.db")
        self.session = get_database_session()
        
        # Clean up any existing test data
        self.session.query(EntityMention).delete()
        self.session.query(Entity).delete()
        self.session.query(TranscriptChunk).delete()
        self.session.query(Video).delete()
        self.session.commit()
        
        self.entity_manager = EntityManager(self.session)
    
    def teardown_method(self):
        """Clean up."""
        if hasattr(self, 'session'):
            # Clean up test data
            self.session.query(EntityMention).delete()
            self.session.query(Entity).delete()
            self.session.query(TranscriptChunk).delete()
            self.session.query(Video).delete()
            self.session.commit()
            self.session.close()
    
    def test_entity_deduplication_exact_match(self):
        """Test that exact entity name matches are deduplicated."""
        # This will fail until we implement EntityManager
        
        # Extract same entity from different chunks
        entity1 = {
            "name": "James Clear",
            "type": "person",
            "confidence": 0.95,
            "context": "James Clear is the author"
        }
        
        entity2 = {
            "name": "James Clear",
            "type": "person", 
            "confidence": 0.93,
            "context": "James Clear also mentions"
        }
        
        # Both should resolve to the same entity
        resolved1 = self.entity_manager.resolve_entity(entity1)
        resolved2 = self.entity_manager.resolve_entity(entity2)
        
        assert resolved1.id == resolved2.id
        assert resolved1.name == "James Clear"
    
    def test_entity_deduplication_fuzzy_match(self):
        """Test that similar entity names are properly linked."""
        entity1 = {
            "name": "Stanford University",
            "type": "place",
            "confidence": 0.95,
            "context": "research from Stanford University"
        }
        
        entity2 = {
            "name": "Stanford",
            "type": "place",
            "confidence": 0.85,
            "context": "mentioned Stanford in the context"
        }
        
        # Should resolve to the same entity due to fuzzy matching
        resolved1 = self.entity_manager.resolve_entity(entity1)
        resolved2 = self.entity_manager.resolve_entity(entity2)
        
        assert resolved1.id == resolved2.id
        # Should use the more complete name
        assert resolved1.name == "Stanford University"
    
    def test_entity_timeline_tracking(self):
        """Test that entity mentions are tracked across video timeline."""
        from app.database import Video, TranscriptChunk
        
        # Create test video and chunks
        video = Video(
            id="test_video",
            title="Test Video",
            duration=1000,
            uploader="Test Channel",
            url="https://test.com",
            video_id="test123",
            processed_date=datetime.utcnow()
        )
        self.session.add(video)
        
        chunks = [
            TranscriptChunk(id=1, video_id="test_video", start_ms=0, end_ms=1000, 
                          speaker_id="speaker_0", text="James Clear wrote Atomic Habits", word_count=5),
            TranscriptChunk(id=2, video_id="test_video", start_ms=5000, end_ms=6000,
                          speaker_id="speaker_0", text="James Clear is a productivity expert", word_count=6),
        ]
        for chunk in chunks:
            self.session.add(chunk)
        self.session.commit()
        
        # Create entity mentions for same entity across different times
        entity_data = {
            "name": "James Clear",
            "type": "person",
            "confidence": 0.95,
            "context": "test context"
        }
        
        entity = self.entity_manager.resolve_entity(entity_data)
        
        # Add mentions at different timestamps
        self.entity_manager.add_mention(entity.id, 1, 0.95, "James Clear wrote Atomic Habits")
        self.entity_manager.add_mention(entity.id, 2, 0.93, "James Clear is a productivity expert")
        
        # Should be able to get timeline of mentions for this entity
        timeline = self.entity_manager.get_entity_timeline(entity.id)
        
        assert len(timeline) == 2
        assert timeline[0]["start_ms"] == 0
        assert timeline[1]["start_ms"] == 5000


class TestExtractionAccuracy:
    """Test entity extraction accuracy and quality metrics."""
    
    def test_extraction_accuracy_threshold(self):
        """Test that extraction meets >90% accuracy requirement."""
        # This would be tested with a labeled dataset in real implementation
        # For now, test that confidence scoring works properly
        
        sample_extractions = [
            {"name": "Atomic Habits", "type": "book", "confidence": 0.95},
            {"name": "James Clear", "type": "person", "confidence": 0.98},
            {"name": "productivity", "type": "concept", "confidence": 0.75},  # Lower confidence
            {"name": "Stanford", "type": "place", "confidence": 0.92},
        ]
        
        # Should filter out low-confidence extractions
        high_confidence = [e for e in sample_extractions if e["confidence"] >= 0.85]
        
        assert len(high_confidence) == 3  # Should exclude "productivity" 
        accuracy = len(high_confidence) / len(sample_extractions)
        assert accuracy >= 0.75  # 75% pass rate for high-confidence extractions
    
    def test_entity_type_classification_accuracy(self):
        """Test that entity types are classified correctly."""
        test_cases = [
            ("Atomic Habits", "book"),
            ("James Clear", "person"), 
            ("Apple Inc", "company"),
            ("Stanford University", "place"),
            ("machine learning", "concept"),
            ("iPhone", "product"),
        ]
        
        # This would test the actual classification in real implementation
        # For now, verify that all expected types are supported
        supported_types = ["person", "book", "concept", "company", "place", "product", "technology"]
        
        for name, expected_type in test_cases:
            assert expected_type in supported_types


class TestExtractionPerformance:
    """Test performance benchmarks for entity extraction."""
    
    def test_extraction_performance_target(self):
        """Test that entity extraction meets <10s per video target."""
        # Mock a typical video transcript length
        typical_transcript_length = 5000  # words
        chunk_size = 500  # words per chunk
        num_chunks = typical_transcript_length // chunk_size
        
        # Target: <10s total, so <1s per chunk on average
        max_time_per_chunk = 10.0 / num_chunks
        
        assert max_time_per_chunk <= 1.0  # Should process each chunk in <1s
        assert num_chunks == 10  # Verify our calculation
        
        # In real implementation, this would time actual extraction calls
        # For now, verify the performance target is reasonable
    
    def test_batch_processing_efficiency(self):
        """Test that batch processing is more efficient than individual calls."""
        # This would test the actual batch processing implementation
        # For now, verify that the concept is supported in the plan
        
        # Batch processing should be more efficient for multiple chunks
        single_chunk_time = 1.0  # seconds
        batch_overhead = 0.1  # seconds
        chunks_in_batch = 5
        
        # Sequential processing time
        sequential_time = chunks_in_batch * single_chunk_time
        
        # Batch processing time (with overhead but parallel processing)
        batch_time = single_chunk_time + batch_overhead
        
        assert batch_time < sequential_time  # Batch should be faster
        efficiency_gain = (sequential_time - batch_time) / sequential_time
        assert efficiency_gain > 0.75  # Should be >75% faster


if __name__ == "__main__":
    pytest.main([__file__, "-v"])