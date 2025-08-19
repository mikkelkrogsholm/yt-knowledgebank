"""
Topic modeling module for YouTube Knowledgebank.

This module provides topic modeling and organization capabilities using OpenAI's
GPT models to identify and organize content topics with hierarchical structures
and relevance scoring.

Phase 3 Module 2: Topic Modeling
"""
import json
import uuid
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher

import openai
from sqlalchemy.orm import Session

from app.database import Topic, VideoTopic, Video, TranscriptChunk
from app.settings import get_openai_api_key, get_model_config, get_ai_prompts


@dataclass
class ExtractedTopic:
    """Represents a topic extracted from text."""
    name: str
    description: str
    relevance: float
    keywords: List[str]


class TopicExtractor:
    """
    OpenAI-based topic extractor using GPT models.
    
    Extracts topics from transcript text using structured prompts
    and returns standardized topic information.
    """
    
    def __init__(self):
        """Initialize the topic extractor."""
        self.api_key = get_openai_api_key()
        self.model_config = get_model_config()
        
        if not self.api_key:
            raise ValueError("OpenAI API key not configured. Please set it in settings.")
        
        # Set up OpenAI client
        openai.api_key = self.api_key
        
        # Topic modeling configuration
        self.model = self.model_config["models"]["topic_modeling"]
        self.temperature = self.model_config["limits"]["temperature_extraction"]
        self.max_tokens = self.model_config["limits"]["max_tokens_extraction"]
    
    def extract_topics(self, text: str) -> List[ExtractedTopic]:
        """
        Extract topics from the given text using OpenAI.
        
        Args:
            text: The text to extract topics from
            
        Returns:
            List of ExtractedTopic objects
        """
        try:
            prompt = self._build_topic_prompt(text)
            
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert topic modeling system. Identify 1-3 main topics that provide meaningful organization for knowledge discovery."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Parse the JSON response
            content = response.choices[0].message.content
            topic_data = json.loads(content)
            
            # Convert to ExtractedTopic objects
            topics = []
            for topic_dict in topic_data.get("topics", []):
                topic = ExtractedTopic(
                    name=topic_dict["name"],
                    description=topic_dict["description"],
                    relevance=topic_dict["relevance"],
                    keywords=topic_dict["keywords"]
                )
                topics.append(topic)
            
            return topics
            
        except Exception as e:
            print(f"Error extracting topics: {e}")
            return []
    
    def _build_topic_prompt(self, text: str) -> str:
        """Build the topic extraction prompt using customizable prompts."""
        try:
            # Get custom prompts from settings
            prompts = get_ai_prompts()
            template = prompts.get("topic_modeling", "")
            
            if template:
                return f"{template}\n\nText to analyze:\n{text}"
            else:
                # Use default if no custom prompt
                return self._build_default_topic_prompt(text)
                
        except Exception as e:
            # Fallback to default behavior if settings fail
            print(f"Error getting custom topic prompt, using default: {e}")
            return self._build_default_topic_prompt(text)
    
    def _build_default_topic_prompt(self, text: str) -> str:
        """Fallback method with default topic extraction prompt."""
        return f"""Identify 1-3 main topics discussed in this transcript chunk. Return JSON with:
{{
  "topics": [
    {{
      "name": "topic name",
      "description": "brief description",
      "relevance": 0.0-1.0,
      "keywords": ["keyword1", "keyword2"]
    }}
  ]
}}

Focus on meaningful topics that help organize and discover knowledge.

Text to analyze:
{text}"""


class TopicManager:
    """
    Manages topic storage, hierarchies, and video associations.
    
    Handles topic resolution, similarity matching, hierarchical organization,
    and video-topic assignments with relevance scoring.
    """
    
    def __init__(self, session: Session):
        """
        Initialize the topic manager.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.similarity_threshold = 0.8  # Threshold for topic similarity
    
    def resolve_topic(self, topic_data: Dict[str, any]) -> Topic:
        """
        Resolve an extracted topic to an existing or new Topic record.
        
        Uses similarity matching to merge similar topics and handles
        hierarchical relationships.
        
        Args:
            topic_data: Dictionary with name, description, keywords, optional parent_name
            
        Returns:
            Topic object (existing or newly created)
        """
        name = topic_data["name"]
        description = topic_data.get("description", "")
        keywords = topic_data.get("keywords", [])
        parent_name = topic_data.get("parent_name")
        
        # First try exact match
        existing = self.session.query(Topic).filter(Topic.name == name).first()
        if existing:
            return existing
        
        # Try similarity matching
        all_topics = self.session.query(Topic).all()
        for existing_topic in all_topics:
            similarity = self._calculate_topic_similarity(name, existing_topic.name, keywords)
            if similarity >= self.similarity_threshold:
                # Update with more descriptive name if needed
                if len(name) > len(existing_topic.name):
                    existing_topic.name = name
                if description and not existing_topic.description:
                    existing_topic.description = description
                self.session.commit()
                return existing_topic
        
        # Handle parent topic
        parent_topic_id = None
        if parent_name:
            parent_topic = self.session.query(Topic).filter(Topic.name == parent_name).first()
            if parent_topic:
                parent_topic_id = parent_topic.id
        
        # Create new topic
        topic_id = f"topic_{uuid.uuid4().hex[:8]}"
        new_topic = Topic(
            id=topic_id,
            name=name,
            description=description,
            parent_topic_id=parent_topic_id,
            created_at=datetime.now(timezone.utc)
        )
        
        self.session.add(new_topic)
        self.session.commit()
        return new_topic
    
    def assign_topic_to_video(self, video_id: str, topic_id: str, relevance_score: float) -> VideoTopic:
        """
        Assign a topic to a video with relevance score.
        
        Args:
            video_id: ID of the video
            topic_id: ID of the topic
            relevance_score: Relevance score (0.0 to 1.0)
            
        Returns:
            VideoTopic object
        """
        # Check if assignment already exists
        existing = self.session.query(VideoTopic).filter(
            VideoTopic.video_id == video_id,
            VideoTopic.topic_id == topic_id
        ).first()
        
        if existing:
            # Update relevance score if new one is higher
            if relevance_score > existing.relevance_score:
                existing.relevance_score = relevance_score
                self.session.commit()
            return existing
        
        # Create new assignment
        assignment = VideoTopic(
            video_id=video_id,
            topic_id=topic_id,
            relevance_score=relevance_score,
            created_at=datetime.now(timezone.utc)
        )
        
        self.session.add(assignment)
        self.session.commit()
        return assignment
    
    def get_topic_evolution(self, topic_id: str) -> List[Dict[str, any]]:
        """
        Get evolution of a topic across videos over time.
        
        Args:
            topic_id: ID of the topic
            
        Returns:
            List of video assignments ordered by video processing date
        """
        assignments = self.session.query(VideoTopic).join(Video).filter(
            VideoTopic.topic_id == topic_id
        ).order_by(Video.processed_date).all()
        
        evolution = []
        for assignment in assignments:
            evolution.append({
                "video_id": assignment.video_id,
                "video_title": assignment.video.title,
                "processed_date": assignment.video.processed_date,
                "relevance_score": assignment.relevance_score,
                "video_duration": assignment.video.duration
            })
        
        return evolution
    
    def get_topic_hierarchy(self, topic_id: str) -> Dict[str, any]:
        """
        Get the hierarchical structure for a topic.
        
        Args:
            topic_id: ID of the topic
            
        Returns:
            Dictionary with parent and children information
        """
        topic = self.session.query(Topic).filter(Topic.id == topic_id).first()
        if not topic:
            return {}
        
        # Get parent chain
        parent_chain = []
        current = topic
        while current.parent_topic_id:
            current = self.session.query(Topic).filter(Topic.id == current.parent_topic_id).first()
            if current:
                parent_chain.insert(0, {
                    "id": current.id,
                    "name": current.name,
                    "description": current.description
                })
        
        # Get direct children
        children = self.session.query(Topic).filter(Topic.parent_topic_id == topic_id).all()
        children_data = [
            {
                "id": child.id,
                "name": child.name,
                "description": child.description,
                "video_count": len(child.video_topics)
            }
            for child in children
        ]
        
        return {
            "topic": {
                "id": topic.id,
                "name": topic.name,
                "description": topic.description
            },
            "parent_chain": parent_chain,
            "children": children_data,
            "video_count": len(topic.video_topics)
        }
    
    def _calculate_topic_similarity(self, name1: str, name2: str, keywords1: List[str] = None) -> float:
        """
        Calculate similarity between two topic names.
        
        Args:
            name1: First topic name
            name2: Second topic name
            keywords1: Optional keywords for first topic
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Normalize names
        norm1 = self._normalize_topic_name(name1)
        norm2 = self._normalize_topic_name(name2)
        
        # Basic string similarity
        name_similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Boost for substring matches
        if norm1 in norm2 or norm2 in norm1:
            name_similarity = max(name_similarity, 0.85)
        
        # If keywords available, check for overlap
        if keywords1:
            norm_keywords = [self._normalize_topic_name(kw) for kw in keywords1]
            if any(kw in norm2 for kw in norm_keywords):
                name_similarity = max(name_similarity, 0.8)
        
        return name_similarity
    
    def _normalize_topic_name(self, name: str) -> str:
        """Normalize topic name for comparison."""
        # Convert to lowercase and remove extra whitespace
        normalized = re.sub(r'\s+', ' ', name.lower().strip())
        
        # Remove common topic words that might vary
        patterns = [
            r'\btips?\b',
            r'\badvice\b',
            r'\bstrategies?\b',
            r'\btechniques?\b',
            r'\bmethods?\b'
        ]
        
        for pattern in patterns:
            normalized = re.sub(pattern, '', normalized).strip()
        
        return normalized


def extract_topics_from_text(text: str) -> List[Dict[str, any]]:
    """
    Extract topics from text using OpenAI topic modeling.
    
    This is a standalone function for topic extraction that can be used
    independently of the TopicManager class.
    
    Args:
        text: Text to extract topics from
        
    Returns:
        List of topic dictionaries with name, description, relevance, keywords
    """
    extractor = TopicExtractor()
    extracted_topics = extractor.extract_topics(text)
    
    # Convert to dictionaries for compatibility
    topics = []
    for topic in extracted_topics:
        topics.append({
            "name": topic.name,
            "description": topic.description,
            "relevance": topic.relevance,
            "keywords": topic.keywords
        })
    
    return topics


class TopicModelingPipeline:
    """
    Complete topic modeling pipeline for processing video content.
    
    Orchestrates topic extraction, organization, and video assignment
    for building coherent content organization.
    """
    
    def __init__(self, session: Session):
        """
        Initialize the topic modeling pipeline.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.extractor = TopicExtractor()
        self.manager = TopicManager(session)
    
    def process_video_topics(self, video_id: str) -> Dict[str, any]:
        """
        Process topic modeling for a video.
        
        Args:
            video_id: ID of the video to process
            
        Returns:
            Processing results with statistics
        """
        # Get video
        video = self.session.query(Video).filter(Video.id == video_id).first()
        if not video:
            return {
                "status": "error",
                "message": f"Video {video_id} not found"
            }
        
        # Get all transcript chunks for the video
        chunks = self.session.query(TranscriptChunk).filter(
            TranscriptChunk.video_id == video_id
        ).order_by(TranscriptChunk.start_ms).all()
        
        if not chunks:
            return {
                "status": "error",
                "message": f"No transcript chunks found for video {video_id}"
            }
        
        # Combine chunks into larger segments for topic analysis
        combined_text = " ".join([chunk.text for chunk in chunks])
        
        stats = {
            "topics_extracted": 0,
            "assignments_created": 0,
            "unique_topics": set()
        }
        
        try:
            # Extract topics from combined text
            extracted_topics = self.extractor.extract_topics(combined_text)
            
            for topic_data in extracted_topics:
                # Convert ExtractedTopic to dict for resolve_topic
                topic_dict = {
                    "name": topic_data.name,
                    "description": topic_data.description,
                    "keywords": topic_data.keywords
                }
                
                # Resolve to existing or create new topic
                topic = self.manager.resolve_topic(topic_dict)
                
                # Assign to video with relevance score
                assignment = self.manager.assign_topic_to_video(
                    video_id,
                    topic.id,
                    topic_data.relevance
                )
                
                stats["topics_extracted"] += 1
                stats["assignments_created"] += 1
                stats["unique_topics"].add(topic.id)
            
            # Convert set to count for JSON serialization
            stats["unique_topics"] = len(stats["unique_topics"])
            
            return {
                "status": "success",
                "video_id": video_id,
                "stats": stats
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing topics: {str(e)}",
                "video_id": video_id
            }