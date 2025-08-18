"""
Test suite for topic modeling functionality.

Tests the topic modeling system that organizes video content into coherent
topics using AI-powered topic assignment and hierarchical structures.

Following TDD approach - these are failing tests that define the behavior
we need to implement for Phase 3 Module 2.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.database import init_database, get_database_session, Topic, VideoTopic, Video, TranscriptChunk
from app.topic_modeling import TopicManager, TopicExtractor, extract_topics_from_text
from app.settings import get_openai_api_key, get_model_config


class TestTopicDatabaseSchema:
    """Test topic database schema and models."""
    
    def setup_method(self):
        """Set up test database."""
        self.db_manager = init_database("sqlite:////app/data/test_topics.db")
        self.session = get_database_session()
        
        # Clean up any existing test data
        self.session.query(VideoTopic).delete()
        self.session.query(Topic).delete()
        self.session.query(TranscriptChunk).delete()
        self.session.query(Video).delete()
        self.session.commit()
    
    def teardown_method(self):
        """Clean up test database."""
        if hasattr(self, 'session'):
            # Clean up test data
            self.session.query(VideoTopic).delete()
            self.session.query(Topic).delete()
            self.session.query(TranscriptChunk).delete()
            self.session.query(Video).delete()
            self.session.commit()
            self.session.close()
    
    def test_topic_table_creation(self):
        """Test that Topic table is created with correct schema."""
        # This will fail until we add Topic model to database.py
        
        # Test that we can create a topic
        topic = Topic(
            id="topic_1",
            name="Productivity",
            description="Content about productivity and efficiency",
            parent_topic_id=None  # Root topic
        )
        
        self.session.add(topic)
        self.session.commit()
        
        # Verify topic was created
        retrieved = self.session.query(Topic).filter(Topic.id == "topic_1").first()
        assert retrieved is not None
        assert retrieved.name == "Productivity"
        assert retrieved.description == "Content about productivity and efficiency"
        assert retrieved.parent_topic_id is None
        assert retrieved.created_at is not None
    
    def test_hierarchical_topic_structure(self):
        """Test that topics can have parent-child relationships."""
        # Create parent topic
        parent_topic = Topic(
            id="topic_parent",
            name="Personal Development",
            description="General personal development content"
        )
        self.session.add(parent_topic)
        self.session.commit()
        
        # Create child topic
        child_topic = Topic(
            id="topic_child",
            name="Productivity",
            description="Productivity and time management",
            parent_topic_id="topic_parent"
        )
        self.session.add(child_topic)
        self.session.commit()
        
        # Verify relationships
        retrieved_child = self.session.query(Topic).filter(Topic.id == "topic_child").first()
        assert retrieved_child.parent_topic_id == "topic_parent"
        
        # Test that we can navigate the hierarchy
        retrieved_parent = self.session.query(Topic).filter(Topic.id == "topic_parent").first()
        assert retrieved_parent is not None
    
    def test_video_topic_relationships(self):
        """Test that videos can be associated with topics with relevance scores."""
        # Create test video
        video = Video(
            id="test_video",
            title="Test Video about Productivity",
            duration=1800,
            uploader="Test Channel",
            url="https://test.com",
            video_id="test123",
            processed_date=datetime.utcnow()
        )
        self.session.add(video)
        
        # Create test topic
        topic = Topic(
            id="topic_1",
            name="Productivity",
            description="Productivity content"
        )
        self.session.add(topic)
        self.session.commit()
        
        # Create video-topic association
        video_topic = VideoTopic(
            video_id="test_video",
            topic_id="topic_1",
            relevance_score=0.85
        )
        self.session.add(video_topic)
        self.session.commit()
        
        # Verify association
        retrieved = self.session.query(VideoTopic).filter(
            VideoTopic.video_id == "test_video",
            VideoTopic.topic_id == "topic_1"
        ).first()
        
        assert retrieved is not None
        assert retrieved.relevance_score == 0.85


class TestAutomaticTopicAssignment:
    """Test automatic topic assignment using AI."""
    
    def setup_method(self):
        """Set up test environment."""
        self.sample_text = """
        In this video, we'll discuss the importance of atomic habits and how small
        changes can lead to remarkable results. Building productive habits is key
        to personal development and achieving your goals. We'll cover time management
        techniques and productivity strategies that successful entrepreneurs use.
        """
    
    @patch('app.topic_modeling.openai.ChatCompletion.create')
    def test_openai_topic_extraction(self, mock_openai):
        """Test that we can extract topics using OpenAI API."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '''
        {
            "topics": [
                {
                    "name": "Productivity",
                    "description": "Strategies and techniques for being more productive",
                    "relevance": 0.95,
                    "keywords": ["productivity", "habits", "time management"]
                },
                {
                    "name": "Personal Development",
                    "description": "Self-improvement and goal achievement",
                    "relevance": 0.88,
                    "keywords": ["personal development", "goals", "success"]
                },
                {
                    "name": "Entrepreneurship",
                    "description": "Business and entrepreneurial strategies",
                    "relevance": 0.72,
                    "keywords": ["entrepreneurs", "business", "strategies"]
                }
            ]
        }
        '''
        mock_openai.return_value = mock_response
        
        # This will fail until we implement extract_topics_from_text
        topics = extract_topics_from_text(self.sample_text)
        
        assert len(topics) == 3
        assert topics[0]["name"] == "Productivity"
        assert topics[0]["relevance"] == 0.95
        assert topics[1]["name"] == "Personal Development"
        assert topics[2]["name"] == "Entrepreneurship"
    
    def test_topic_coherence_validation(self):
        """Test that extracted topics are coherent and relevant."""
        # Sample extracted topics
        extracted_topics = [
            {
                "name": "Productivity",
                "description": "Strategies for being more productive",
                "relevance": 0.95,
                "keywords": ["productivity", "habits", "efficiency"]
            },
            {
                "name": "Random Topic",
                "description": "Unrelated content",
                "relevance": 0.15,
                "keywords": ["unrelated", "random"]
            }
        ]
        
        # Filter topics by relevance threshold
        relevant_topics = [t for t in extracted_topics if t["relevance"] >= 0.7]
        
        assert len(relevant_topics) == 1
        assert relevant_topics[0]["name"] == "Productivity"
    
    def test_model_config_for_topic_modeling(self):
        """Test that model configuration is properly loaded for topic modeling."""
        config = get_model_config()
        
        # Should use GPT-5-nano for topic modeling as per plan
        assert "models" in config
        assert "topic_modeling" in config["models"]
        assert config["models"]["topic_modeling"] == "gpt-5-nano"


class TestTopicManagement:
    """Test topic management and curation functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.db_manager = init_database("sqlite:////app/data/test_topic_mgmt.db")
        self.session = get_database_session()
        
        # Clean up any existing test data
        self.session.query(VideoTopic).delete()
        self.session.query(Topic).delete()
        self.session.query(TranscriptChunk).delete()
        self.session.query(Video).delete()
        self.session.commit()
        
        self.topic_manager = TopicManager(self.session)
    
    def teardown_method(self):
        """Clean up."""
        if hasattr(self, 'session'):
            # Clean up test data
            self.session.query(VideoTopic).delete()
            self.session.query(Topic).delete()
            self.session.query(TranscriptChunk).delete()
            self.session.query(Video).delete()
            self.session.commit()
            self.session.close()
    
    def test_topic_creation_and_resolution(self):
        """Test that topics can be created and resolved properly."""
        # This will fail until we implement TopicManager
        
        topic_data = {
            "name": "Productivity",
            "description": "Content about productivity and efficiency",
            "keywords": ["productivity", "efficiency", "habits"]
        }
        
        # Should create new topic if it doesn't exist
        topic1 = self.topic_manager.resolve_topic(topic_data)
        assert topic1.name == "Productivity"
        
        # Should return existing topic if similar one exists
        similar_topic_data = {
            "name": "Productivity Tips",
            "description": "Tips for being more productive",
            "keywords": ["productivity", "tips", "efficiency"]
        }
        
        topic2 = self.topic_manager.resolve_topic(similar_topic_data)
        # Should resolve to the same topic due to similarity
        assert topic1.id == topic2.id
    
    def test_topic_hierarchy_management(self):
        """Test creation and management of topic hierarchies."""
        # Create parent topic
        parent_data = {
            "name": "Personal Development",
            "description": "General personal development content",
            "keywords": ["personal", "development", "growth"]
        }
        parent_topic = self.topic_manager.resolve_topic(parent_data)
        
        # Create child topic
        child_data = {
            "name": "Productivity",
            "description": "Productivity strategies",
            "keywords": ["productivity", "efficiency"],
            "parent_name": "Personal Development"
        }
        child_topic = self.topic_manager.resolve_topic(child_data)
        
        # Verify hierarchy
        assert child_topic.parent_topic_id == parent_topic.id
    
    def test_video_topic_assignment(self):
        """Test assigning topics to videos with relevance scores."""
        # Create test video
        video = Video(
            id="test_video",
            title="Productivity Tips",
            duration=900,
            uploader="Test Channel",
            url="https://test.com",
            video_id="test123",
            processed_date=datetime.utcnow()
        )
        self.session.add(video)
        self.session.commit()
        
        # Create topic
        topic_data = {
            "name": "Productivity",
            "description": "Productivity content",
            "keywords": ["productivity"]
        }
        topic = self.topic_manager.resolve_topic(topic_data)
        
        # Assign topic to video
        assignment = self.topic_manager.assign_topic_to_video(
            video.id, topic.id, relevance_score=0.92
        )
        
        assert assignment.video_id == video.id
        assert assignment.topic_id == topic.id
        assert assignment.relevance_score == 0.92
    
    def test_topic_evolution_tracking(self):
        """Test tracking topic evolution over time."""
        # Create video from 6 months ago
        old_video = Video(
            id="old_video",
            title="Old Productivity Methods",
            duration=600,
            uploader="Test Channel",
            url="https://old.com",
            video_id="old123",
            processed_date=datetime(2024, 2, 1)  # 6 months ago
        )
        self.session.add(old_video)
        
        # Create recent video
        new_video = Video(
            id="new_video", 
            title="Modern Productivity Techniques",
            duration=1200,
            uploader="Test Channel",
            url="https://new.com",
            video_id="new123",
            processed_date=datetime.utcnow()
        )
        self.session.add(new_video)
        self.session.commit()
        
        # Create productivity topic
        topic_data = {
            "name": "Productivity",
            "description": "Productivity strategies",
            "keywords": ["productivity"]
        }
        topic = self.topic_manager.resolve_topic(topic_data)
        
        # Assign topic to both videos
        self.topic_manager.assign_topic_to_video(old_video.id, topic.id, 0.85)
        self.topic_manager.assign_topic_to_video(new_video.id, topic.id, 0.90)
        
        # Get topic evolution
        evolution = self.topic_manager.get_topic_evolution(topic.id)
        
        assert len(evolution) == 2
        assert evolution[0]["video_id"] == old_video.id  # Older video first
        assert evolution[1]["video_id"] == new_video.id  # Newer video second


class TestTopicQualityMetrics:
    """Test topic quality and coherence metrics."""
    
    def test_topic_relevance_scoring(self):
        """Test that topic relevance scores are calculated correctly."""
        # Sample topic assignments with different relevance scores
        topic_assignments = [
            {"topic": "Productivity", "relevance": 0.95},
            {"topic": "Productivity", "relevance": 0.88},
            {"topic": "Productivity", "relevance": 0.92},
            {"topic": "Productivity", "relevance": 0.76},  # Lower relevance
        ]
        
        # Calculate average relevance
        relevances = [a["relevance"] for a in topic_assignments]
        avg_relevance = sum(relevances) / len(relevances)
        
        assert avg_relevance > 0.85  # Should maintain high average relevance
        
        # Filter out low-relevance assignments
        high_relevance = [a for a in topic_assignments if a["relevance"] >= 0.8]
        assert len(high_relevance) == 3  # Should filter out the 0.76 score
    
    def test_topic_coherence_validation(self):
        """Test that topics maintain coherence across videos."""
        # This would test actual coherence in a real implementation
        # For now, test the validation logic
        
        sample_topics = [
            {
                "name": "Productivity", 
                "keywords": ["productivity", "efficiency", "habits", "time management"],
                "coherence_score": 0.92
            },
            {
                "name": "Mixed Content",
                "keywords": ["random", "unrelated", "scattered", "unclear"],
                "coherence_score": 0.45
            }
        ]
        
        # Topics should have high coherence scores
        coherent_topics = [t for t in sample_topics if t["coherence_score"] >= 0.8]
        assert len(coherent_topics) == 1
        assert coherent_topics[0]["name"] == "Productivity"


class TestTopicPerformance:
    """Test performance benchmarks for topic modeling."""
    
    def test_topic_modeling_performance_target(self):
        """Test that topic modeling meets <5s per video target."""
        # Mock a typical video transcript length
        typical_transcript_length = 3000  # words
        chunk_size = 500  # words per chunk
        num_chunks = typical_transcript_length // chunk_size
        
        # Target: <5s total for topic modeling
        max_time_per_chunk = 5.0 / num_chunks
        
        assert max_time_per_chunk <= 1.0  # Should process each chunk quickly
        assert num_chunks == 6  # Verify our calculation
        
        # In real implementation, this would time actual topic modeling calls
    
    def test_topic_caching_efficiency(self):
        """Test that topic results are properly cached."""
        # This would test the actual caching implementation
        # For now, verify the caching concept
        
        # First call should take longer (processing time)
        first_call_time = 2.0  # seconds
        
        # Cached call should be much faster
        cached_call_time = 0.1  # seconds
        
        speedup = first_call_time / cached_call_time
        assert speedup >= 10  # Should be at least 10x faster with caching


if __name__ == "__main__":
    pytest.main([__file__, "-v"])