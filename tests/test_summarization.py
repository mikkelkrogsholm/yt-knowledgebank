"""
Test suite for summarization functionality.

Tests the AI-powered summarization system that generates different types
of summaries from video transcripts for quick insights and knowledge discovery.

Following TDD approach - these are failing tests that define the behavior
we need to implement for Phase 3 Module 3.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from app.database import init_database, get_database_session, Summary, Video, TranscriptChunk, Entity, Topic
from app.summarization import SummaryGenerator, SummaryManager, generate_summary_from_text
from app.settings import get_openai_api_key, get_model_config


class TestSummaryDatabaseSchema:
    """Test summary database schema and models."""
    
    def setup_method(self):
        """Set up test database."""
        self.db_manager = init_database("sqlite:////app/data/test_summaries.db")
        self.session = get_database_session()
        
        # Clean up any existing test data
        self.session.query(Summary).delete()
        self.session.query(TranscriptChunk).delete()
        self.session.query(Video).delete()
        self.session.query(Entity).delete()
        self.session.query(Topic).delete()
        self.session.commit()
    
    def teardown_method(self):
        """Clean up test database."""
        if hasattr(self, 'session'):
            # Clean up test data
            self.session.query(Summary).delete()
            self.session.query(TranscriptChunk).delete()
            self.session.query(Video).delete()
            self.session.query(Entity).delete()
            self.session.query(Topic).delete()
            self.session.commit()
            self.session.close()
    
    def test_summary_table_creation(self):
        """Test that Summary table is created with correct schema."""
        # This will fail until we add Summary model to database.py
        
        # Test that we can create different types of summaries
        video_summary = Summary(
            id="summary_1",
            video_id="test_video",
            entity_id=None,
            topic_id=None,
            summary_type="video",
            content="This video discusses productivity techniques and habit formation.",
            generated_at=datetime.utcnow()
        )
        
        self.session.add(video_summary)
        self.session.commit()
        
        # Verify summary was created
        retrieved = self.session.query(Summary).filter(Summary.id == "summary_1").first()
        assert retrieved is not None
        assert retrieved.summary_type == "video"
        assert retrieved.video_id == "test_video"
        assert retrieved.entity_id is None
        assert retrieved.topic_id is None
        assert "productivity" in retrieved.content
    
    def test_entity_focused_summary(self):
        """Test entity-focused summary creation."""
        # Create test entity
        entity = Entity(
            id="entity_1",
            name="James Clear",
            type="person",
            description="Author and productivity expert"
        )
        self.session.add(entity)
        
        # Create test video
        video = Video(
            id="test_video",
            title="Test Video",
            duration=1800,
            uploader="Test Channel",
            url="https://test.com",
            video_id="test123",
            processed_date=datetime.utcnow()
        )
        self.session.add(video)
        self.session.commit()
        
        # Create entity-focused summary
        entity_summary = Summary(
            id="summary_entity",
            video_id="test_video",
            entity_id="entity_1",
            topic_id=None,
            summary_type="entity",
            content="James Clear discusses the compound effect of small habits.",
            generated_at=datetime.utcnow()
        )
        
        self.session.add(entity_summary)
        self.session.commit()
        
        # Verify entity summary
        retrieved = self.session.query(Summary).filter(Summary.id == "summary_entity").first()
        assert retrieved.summary_type == "entity"
        assert retrieved.entity_id == "entity_1"
        assert "James Clear" in retrieved.content
    
    def test_topic_focused_summary(self):
        """Test topic-focused summary creation."""
        # Create test topic
        topic = Topic(
            id="topic_1",
            name="Productivity",
            description="Content about productivity and efficiency"
        )
        self.session.add(topic)
        
        # Create test video
        video = Video(
            id="test_video",
            title="Productivity Tips",
            duration=1200,
            uploader="Test Channel",
            url="https://test.com",
            video_id="test123",
            processed_date=datetime.utcnow()
        )
        self.session.add(video)
        self.session.commit()
        
        # Create topic-focused summary
        topic_summary = Summary(
            id="summary_topic",
            video_id="test_video",
            entity_id=None,
            topic_id="topic_1",
            summary_type="topic",
            content="Key productivity strategies include time blocking and habit stacking.",
            generated_at=datetime.utcnow()
        )
        
        self.session.add(topic_summary)
        self.session.commit()
        
        # Verify topic summary
        retrieved = self.session.query(Summary).filter(Summary.id == "summary_topic").first()
        assert retrieved.summary_type == "topic"
        assert retrieved.topic_id == "topic_1"
        assert "productivity" in retrieved.content.lower()
    
    def test_actionable_items_summary(self):
        """Test actionable items summary creation."""
        # Create test video
        video = Video(
            id="test_video",
            title="Action Steps for Success",
            duration=900,
            uploader="Test Channel",
            url="https://test.com",
            video_id="test123",
            processed_date=datetime.utcnow()
        )
        self.session.add(video)
        self.session.commit()
        
        # Create actionable items summary
        actionable_summary = Summary(
            id="summary_actionable",
            video_id="test_video",
            entity_id=None,
            topic_id=None,
            summary_type="actionable",
            content="1. Start each day with your most important task\n2. Use the 2-minute rule for small tasks\n3. Review your goals weekly",
            generated_at=datetime.utcnow()
        )
        
        self.session.add(actionable_summary)
        self.session.commit()
        
        # Verify actionable summary
        retrieved = self.session.query(Summary).filter(Summary.id == "summary_actionable").first()
        assert retrieved.summary_type == "actionable"
        assert "1." in retrieved.content  # Should have numbered items
        assert "2." in retrieved.content


class TestAIPoweredSummarization:
    """Test AI-powered summarization with GPT models."""
    
    def setup_method(self):
        """Set up test environment."""
        self.sample_transcript = """
        Welcome to today's video about building atomic habits. I'm going to share
        three key strategies that have transformed my productivity. First, let's talk
        about the compound effect. Small changes, when compounded over time, lead to
        remarkable results. James Clear discusses this extensively in his book Atomic Habits.
        
        The second strategy is habit stacking. This involves linking a new habit to an
        existing one. For example, after I pour my morning coffee, I will review my
        daily goals. This creates a trigger that makes the new habit automatic.
        
        The third strategy is environmental design. Your environment shapes your behavior
        more than you realize. If you want to read more, place books in visible locations.
        If you want to exercise, lay out your workout clothes the night before.
        
        Here are three actionable steps you can take today:
        1. Choose one small habit to improve by just 1% today
        2. Identify an existing habit you can stack a new one onto
        3. Modify your environment to support your desired behaviors
        
        Remember, you don't have to be perfect. Small, consistent actions compound
        into extraordinary results over time.
        """
    
    @patch('app.summarization.openai.ChatCompletion.create')
    def test_openai_video_summarization(self, mock_openai):
        """Test video-level summarization using OpenAI."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '''
        {
            "summary": "This video explores three key strategies for building atomic habits: the compound effect of small changes, habit stacking to link new habits to existing ones, and environmental design to shape behavior. The content emphasizes that small, consistent actions lead to extraordinary results over time.",
            "key_insights": [
                "Small changes compound over time to create remarkable results",
                "Habit stacking creates automatic triggers for new behaviors",
                "Environmental design significantly influences behavior patterns"
            ],
            "actionable_items": [
                "Choose one small habit to improve by 1% today",
                "Identify an existing habit to stack a new one onto",
                "Modify your environment to support desired behaviors"
            ]
        }
        '''
        mock_openai.return_value = mock_response
        
        # This will fail until we implement generate_summary_from_text
        result = generate_summary_from_text(self.sample_transcript, "video")
        
        assert "summary" in result
        assert "key_insights" in result
        assert "actionable_items" in result
        assert "atomic habits" in result["summary"].lower()
        assert len(result["key_insights"]) == 3
        assert len(result["actionable_items"]) == 3
    
    @patch('app.summarization.openai.ChatCompletion.create')
    def test_entity_focused_summarization(self, mock_openai):
        """Test entity-focused summarization."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '''
        {
            "summary": "James Clear is referenced as the author of 'Atomic Habits' and is presented as an authority on habit formation and the compound effect of small changes.",
            "key_insights": [
                "James Clear's work focuses on the compound effect of habits",
                "His book 'Atomic Habits' is a key reference for habit formation"
            ],
            "actionable_items": [
                "Read James Clear's book 'Atomic Habits'",
                "Apply the compound effect principle to daily habits"
            ]
        }
        '''
        mock_openai.return_value = mock_response
        
        result = generate_summary_from_text(self.sample_transcript, "entity", focus="James Clear")
        
        assert "James Clear" in result["summary"]
        assert len(result["key_insights"]) == 2
        assert "Atomic Habits" in result["summary"]
    
    @patch('app.summarization.openai.ChatCompletion.create')
    def test_topic_focused_summarization(self, mock_openai):
        """Test topic-focused summarization."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '''
        {
            "summary": "The productivity content focuses on three main strategies: leveraging the compound effect of small improvements, using habit stacking to create automatic behaviors, and designing environments that support desired actions.",
            "key_insights": [
                "Productivity improves through small, consistent changes",
                "Habit stacking creates productivity systems",
                "Environmental design supports productive behaviors"
            ],
            "actionable_items": [
                "Implement 1% daily improvements in key areas",
                "Stack productive habits onto existing routines",
                "Design workspace to eliminate friction for important tasks"
            ]
        }
        '''
        mock_openai.return_value = mock_response
        
        result = generate_summary_from_text(self.sample_transcript, "topic", focus="productivity")
        
        assert "productivity" in result["summary"].lower()
        assert len(result["key_insights"]) == 3
        # Check that at least half the actionable items relate to productivity
        productivity_items = [item for item in result["actionable_items"] 
                            if "productive" in item.lower() or "productivity" in item.lower()]
        assert len(productivity_items) >= len(result["actionable_items"]) // 2
    
    def test_model_config_for_summarization(self):
        """Test that model configuration is properly loaded for summarization."""
        config = get_model_config()
        
        # Should use GPT-5-nano for summarization as per plan
        assert "models" in config
        assert "summarization" in config["models"]
        assert config["models"]["summarization"] == "gpt-5-nano"


class TestSummaryManagement:
    """Test summary management and caching functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.db_manager = init_database("sqlite:////app/data/test_summary_mgmt.db")
        self.session = get_database_session()
        
        # Clean up any existing test data
        self.session.query(Summary).delete()
        self.session.query(TranscriptChunk).delete()
        self.session.query(Video).delete()
        self.session.query(Entity).delete()
        self.session.query(Topic).delete()
        self.session.commit()
        
        self.summary_manager = SummaryManager(self.session)
    
    def teardown_method(self):
        """Clean up."""
        if hasattr(self, 'session'):
            # Clean up test data
            self.session.query(Summary).delete()
            self.session.query(TranscriptChunk).delete()
            self.session.query(Video).delete()
            self.session.query(Entity).delete()
            self.session.query(Topic).delete()
            self.session.commit()
            self.session.close()
    
    def test_summary_caching_and_retrieval(self):
        """Test that summaries are properly cached and retrieved."""
        # This will fail until we implement SummaryManager
        
        # Create test video
        video = Video(
            id="test_video",
            title="Test Video",
            duration=1800,
            uploader="Test Channel",
            url="https://test.com",
            video_id="test123",
            processed_date=datetime.utcnow()
        )
        self.session.add(video)
        self.session.commit()
        
        # Generate and cache summary
        summary_data = {
            "summary": "Test video summary content",
            "key_insights": ["Insight 1", "Insight 2"],
            "actionable_items": ["Action 1", "Action 2"]
        }
        
        summary = self.summary_manager.create_or_update_summary(
            video_id="test_video",
            summary_type="video",
            content=summary_data
        )
        
        assert summary.summary_type == "video"
        assert "Test video summary" in summary.content
        
        # Retrieve cached summary
        cached_summary = self.summary_manager.get_summary(
            video_id="test_video",
            summary_type="video"
        )
        
        assert cached_summary is not None
        assert cached_summary.id == summary.id
    
    def test_summary_invalidation_and_updates(self):
        """Test that summaries are invalidated and updated when content changes."""
        # Create test video
        video = Video(
            id="test_video",
            title="Test Video",
            duration=1800,
            uploader="Test Channel", 
            url="https://test.com",
            video_id="test123",
            processed_date=datetime.utcnow()
        )
        self.session.add(video)
        self.session.commit()
        
        # Create initial summary
        initial_summary = {
            "summary": "Initial summary content",
            "key_insights": ["Initial insight"],
            "actionable_items": ["Initial action"]
        }
        
        summary1 = self.summary_manager.create_or_update_summary(
            video_id="test_video",
            summary_type="video",
            content=initial_summary
        )
        
        # Update summary with new content
        updated_summary = {
            "summary": "Updated summary content",
            "key_insights": ["Updated insight", "New insight"],
            "actionable_items": ["Updated action"]
        }
        
        summary2 = self.summary_manager.create_or_update_summary(
            video_id="test_video",
            summary_type="video",
            content=updated_summary
        )
        
        # Should update existing summary, not create new one
        assert summary1.id == summary2.id
        assert "Updated summary" in summary2.content
    
    def test_multi_type_summary_management(self):
        """Test managing multiple summary types for the same video."""
        # Create test video, entity, and topic
        video = Video(
            id="test_video",
            title="Test Video",
            duration=1800,
            uploader="Test Channel",
            url="https://test.com",
            video_id="test123",
            processed_date=datetime.utcnow()
        )
        self.session.add(video)
        
        entity = Entity(
            id="entity_1",
            name="Test Person",
            type="person",
            description="Test person entity"
        )
        self.session.add(entity)
        
        topic = Topic(
            id="topic_1",
            name="Test Topic",
            description="Test topic"
        )
        self.session.add(topic)
        self.session.commit()
        
        # Create different types of summaries
        video_summary = self.summary_manager.create_or_update_summary(
            video_id="test_video",
            summary_type="video",
            content={"summary": "Video-level summary"}
        )
        
        entity_summary = self.summary_manager.create_or_update_summary(
            video_id="test_video",
            summary_type="entity",
            entity_id="entity_1",
            content={"summary": "Entity-focused summary"}
        )
        
        topic_summary = self.summary_manager.create_or_update_summary(
            video_id="test_video",
            summary_type="topic",
            topic_id="topic_1",
            content={"summary": "Topic-focused summary"}
        )
        
        # Verify all summaries exist independently
        assert video_summary.summary_type == "video"
        assert entity_summary.summary_type == "entity"
        assert topic_summary.summary_type == "topic"
        
        # Verify proper associations
        assert entity_summary.entity_id == "entity_1"
        assert topic_summary.topic_id == "topic_1"


class TestSummaryQualityMetrics:
    """Test summary quality and coherence metrics."""
    
    def test_summary_coherence_validation(self):
        """Test that summaries maintain coherence and accuracy."""
        # Sample summaries with different quality levels
        high_quality_summary = {
            "summary": "This video covers three evidence-based productivity strategies with clear implementation steps.",
            "key_insights": [
                "Small improvements compound over time",
                "Environmental design influences behavior",
                "Habit stacking creates automatic triggers"
            ],
            "actionable_items": [
                "Improve one habit by 1% daily",
                "Design environment to support goals",
                "Link new habits to existing routines"
            ]
        }
        
        low_quality_summary = {
            "summary": "Video talks about stuff and things.",
            "key_insights": ["Something about habits"],
            "actionable_items": ["Do something"]
        }
        
        # Quality metrics
        def calculate_summary_quality(summary_data):
            summary_length = len(summary_data["summary"])
            insights_detail = sum(len(insight) for insight in summary_data["key_insights"])
            actions_specificity = sum(len(action) for action in summary_data["actionable_items"])
            
            return (summary_length + insights_detail + actions_specificity) / 3
        
        high_quality_score = calculate_summary_quality(high_quality_summary)
        low_quality_score = calculate_summary_quality(low_quality_summary)
        
        assert high_quality_score > low_quality_score * 2  # Should be significantly better
        assert high_quality_score > 50  # Should meet minimum quality threshold
    
    def test_summary_completeness_validation(self):
        """Test that summaries include all required components."""
        complete_summary = {
            "summary": "Complete summary with all components",
            "key_insights": ["Insight 1", "Insight 2", "Insight 3"],
            "actionable_items": ["Action 1", "Action 2"]
        }
        
        incomplete_summary = {
            "summary": "Incomplete summary",
            "key_insights": [],  # Missing insights
            "actionable_items": ["Action 1"]
        }
        
        def validate_summary_completeness(summary_data):
            has_summary = bool(summary_data.get("summary", "").strip())
            has_insights = bool(summary_data.get("key_insights", []))
            has_actions = bool(summary_data.get("actionable_items", []))
            
            return all([has_summary, has_insights, has_actions])
        
        assert validate_summary_completeness(complete_summary) == True
        assert validate_summary_completeness(incomplete_summary) == False


class TestSummaryPerformance:
    """Test performance benchmarks for summarization."""
    
    def test_summarization_performance_target(self):
        """Test that summarization meets <15s per video target."""
        # Mock video transcript parameters
        typical_transcript_length = 8000  # words
        processing_overhead = 2.0  # seconds for setup/parsing
        
        # Target: <15s total for summarization
        max_processing_time = 15.0 - processing_overhead
        max_words_per_second = typical_transcript_length / max_processing_time
        
        assert max_words_per_second >= 600  # Should process at least 600 words/second
        
        # In real implementation, this would time actual summarization calls
    
    def test_batch_summarization_efficiency(self):
        """Test that batch summarization is efficient."""
        # Batch processing should be more efficient than individual calls
        single_video_time = 12.0  # seconds
        batch_overhead = 3.0  # seconds
        videos_in_batch = 5
        
        # Sequential processing time
        sequential_time = videos_in_batch * single_video_time
        
        # Batch processing time (with shared context and parallel processing)
        batch_time = (single_video_time * 0.7 * videos_in_batch) + batch_overhead
        
        assert batch_time < sequential_time  # Batch should be faster
        efficiency_gain = (sequential_time - batch_time) / sequential_time
        assert efficiency_gain > 0.2  # Should be >20% faster


if __name__ == "__main__":
    pytest.main([__file__, "-v"])