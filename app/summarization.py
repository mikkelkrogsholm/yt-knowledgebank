"""
Summarization module for YouTube Knowledgebank.

This module provides AI-powered summarization capabilities using OpenAI's
GPT models to generate different types of summaries: video-level summaries,
entity-focused summaries, topic-focused summaries, and actionable items.

Phase 3 Module 3: Summary Generation
"""
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from openai import OpenAI
from sqlalchemy.orm import Session

from app.database import Summary, Video, Entity, Topic, TranscriptChunk
from app.settings import get_openai_api_key, get_model_config, get_ai_prompts


@dataclass
class GeneratedSummary:
    """Represents a generated summary with structured content."""
    summary: str
    key_insights: List[str]
    actionable_items: List[str]


class SummaryGenerator:
    """
    OpenAI-based summary generator using GPT models.
    
    Generates structured summaries from transcript text with different
    focus areas and summary types.
    """
    
    def __init__(self):
        """Initialize the summary generator."""
        try:
            self.api_key = get_openai_api_key()
            self.model_config = get_model_config()
            
            if not self.api_key:
                raise ValueError("OpenAI API key not configured. Please set it in settings.")
            
            # Set up OpenAI client (new v1.0+ pattern)
            self.client = OpenAI(api_key=self.api_key)
        except ImportError as e:
            raise ImportError(f"Failed to import OpenAI library: {e}")
        except Exception as e:
            raise ValueError(f"Failed to initialize SummaryGenerator: {e}")
        
        # Summarization model configuration
        self.model = self.model_config["models"]["summarization"]
        self.temperature = self.model_config["limits"]["temperature_extraction"]
        self.max_tokens = self.model_config["limits"]["max_tokens_extraction"]
    
    def generate_summary(self, text: str, summary_type: str, focus: str = None) -> GeneratedSummary:
        """
        Generate a summary from the given text.
        
        Args:
            text: The text to summarize
            summary_type: Type of summary (video, entity, topic, actionable)
            focus: Optional focus area for entity/topic summaries
            
        Returns:
            GeneratedSummary object with structured content
        """
        try:
            prompt = self._build_summary_prompt(text, summary_type, focus)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert summarization system. Create concise, actionable summaries that capture key insights and provide practical value."
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
            summary_data = json.loads(content)
            
            # Convert to GeneratedSummary object
            return GeneratedSummary(
                summary=summary_data["summary"],
                key_insights=summary_data["key_insights"],
                actionable_items=summary_data["actionable_items"]
            )
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            # Return empty summary on error
            return GeneratedSummary(
                summary="Error generating summary",
                key_insights=[],
                actionable_items=[]
            )
    
    def _build_summary_prompt(self, text: str, summary_type: str, focus: str = None) -> str:
        """Build the summarization prompt based on type and focus using customizable prompts."""
        try:
            # Get custom prompts from settings
            prompts = get_ai_prompts()
            
            if summary_type == "video":
                template = prompts.get("summarization", {}).get("video", "")
            elif summary_type == "actionable":
                template = prompts.get("summarization", {}).get("actionable", "")
            elif summary_type == "entity":
                template = prompts.get("summarization", {}).get("entity", "")
            elif summary_type == "topic":
                template = prompts.get("summarization", {}).get("topic", "")
            else:
                template = "Create a comprehensive summary of this transcript content."
            
            # Replace focus placeholder if present
            if focus and "{focus}" in template:
                template = template.replace("{focus}", focus)
            
            # Append the text to analyze
            return f"{template}\n\nText to summarize:\n{text}"
            
        except Exception as e:
            # Fallback to default behavior if settings fail
            print(f"Error getting custom prompts, using defaults: {e}")
            return self._build_default_prompt(text, summary_type, focus)
    
    def _build_default_prompt(self, text: str, summary_type: str, focus: str = None) -> str:
        """Fallback method with default prompts."""
        base_format = """Return JSON with:
{
  "summary": "concise summary text",
  "key_insights": ["insight1", "insight2"],
  "actionable_items": ["action1", "action2"]
}"""
        
        if summary_type == "video":
            instruction = "Create a concise summary of the key insights from this transcript. Focus on main ideas, concepts, important facts, and novel perspectives."
        elif summary_type == "entity" and focus:
            instruction = f"Create a summary focused specifically on what was said about '{focus}'. Include any mentions, discussions, quotes, or references to this entity."
        elif summary_type == "topic" and focus:
            instruction = f"Create a summary focused specifically on the topic of '{focus}'. Extract all relevant information, strategies, and insights related to this topic."
        elif summary_type == "actionable":
            instruction = "Extract concrete, actionable advice and recommendations from this transcript. Focus on specific steps, strategies, and practical recommendations that viewers can implement."
        else:
            instruction = "Create a comprehensive summary of this transcript content."
        
        return f"""{instruction}

{base_format}

Text to summarize:
{text}"""


class SummaryManager:
    """
    Manages summary storage, caching, and retrieval.
    
    Handles summary creation, updates, invalidation, and efficient
    retrieval with caching mechanisms.
    """
    
    def __init__(self, session: Session):
        """
        Initialize the summary manager.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.generator = SummaryGenerator()
    
    def create_or_update_summary(self, video_id: str, summary_type: str, 
                                content: Dict[str, Any], entity_id: str = None, 
                                topic_id: str = None) -> Summary:
        """
        Create a new summary or update an existing one.
        
        Args:
            video_id: ID of the video
            summary_type: Type of summary (video, entity, topic, actionable)
            content: Summary content dictionary
            entity_id: Optional entity ID for entity-focused summaries
            topic_id: Optional topic ID for topic-focused summaries
            
        Returns:
            Summary object
        """
        # Check if summary already exists
        existing = self.session.query(Summary).filter(
            Summary.video_id == video_id,
            Summary.summary_type == summary_type,
            Summary.entity_id == entity_id,
            Summary.topic_id == topic_id
        ).first()
        
        # Serialize content to JSON string
        content_json = json.dumps(content, indent=2)
        
        if existing:
            # Update existing summary
            existing.content = content_json
            existing.generated_at = datetime.now(timezone.utc)
            self.session.commit()
            return existing
        else:
            # Create new summary
            summary_id = f"summary_{uuid.uuid4().hex[:8]}"
            new_summary = Summary(
                id=summary_id,
                video_id=video_id,
                entity_id=entity_id,
                topic_id=topic_id,
                summary_type=summary_type,
                content=content_json,
                generated_at=datetime.now(timezone.utc)
            )
            
            self.session.add(new_summary)
            self.session.commit()
            return new_summary
    
    def get_summary(self, video_id: str, summary_type: str, 
                   entity_id: str = None, topic_id: str = None) -> Optional[Summary]:
        """
        Retrieve a summary from the database.
        
        Args:
            video_id: ID of the video
            summary_type: Type of summary
            entity_id: Optional entity ID
            topic_id: Optional topic ID
            
        Returns:
            Summary object or None if not found
        """
        return self.session.query(Summary).filter(
            Summary.video_id == video_id,
            Summary.summary_type == summary_type,
            Summary.entity_id == entity_id,
            Summary.topic_id == topic_id
        ).first()
    
    def get_all_summaries_for_video(self, video_id: str) -> List[Summary]:
        """
        Get all summaries for a specific video.
        
        Args:
            video_id: ID of the video
            
        Returns:
            List of Summary objects
        """
        return self.session.query(Summary).filter(
            Summary.video_id == video_id
        ).all()
    
    def invalidate_summaries(self, video_id: str):
        """
        Invalidate (delete) all summaries for a video.
        
        Used when video content changes and summaries need regeneration.
        
        Args:
            video_id: ID of the video
        """
        self.session.query(Summary).filter(
            Summary.video_id == video_id
        ).delete()
        self.session.commit()
    
    def generate_and_store_summary(self, video_id: str, summary_type: str,
                                  entity_id: str = None, topic_id: str = None,
                                  focus: str = None) -> Summary:
        """
        Generate a new summary and store it in the database.
        
        Args:
            video_id: ID of the video
            summary_type: Type of summary to generate
            entity_id: Optional entity ID for entity-focused summaries
            topic_id: Optional topic ID for topic-focused summaries
            focus: Optional focus name for entity/topic summaries
            
        Returns:
            Summary object
        """
        # Get video transcript
        transcript_text = self._get_video_transcript(video_id)
        if not transcript_text:
            raise ValueError(f"No transcript found for video {video_id}")
        
        # Generate summary
        generated = self.generator.generate_summary(transcript_text, summary_type, focus)
        
        # Convert to content dictionary
        content = {
            "summary": generated.summary,
            "key_insights": generated.key_insights,
            "actionable_items": generated.actionable_items
        }
        
        # Store in database
        return self.create_or_update_summary(
            video_id=video_id,
            summary_type=summary_type,
            content=content,
            entity_id=entity_id,
            topic_id=topic_id
        )
    
    def _get_video_transcript(self, video_id: str) -> str:
        """
        Get the full transcript text for a video.
        
        Args:
            video_id: ID of the video
            
        Returns:
            Combined transcript text
        """
        chunks = self.session.query(TranscriptChunk).filter(
            TranscriptChunk.video_id == video_id
        ).order_by(TranscriptChunk.start_ms).all()
        
        if not chunks:
            return ""
        
        return " ".join([chunk.text for chunk in chunks])


def generate_summary_from_text(text: str, summary_type: str, focus: str = None) -> Dict[str, Any]:
    """
    Generate a summary from text using OpenAI summarization.
    
    This is a standalone function for summary generation that can be used
    independently of the SummaryManager class.
    
    Args:
        text: Text to summarize
        summary_type: Type of summary (video, entity, topic, actionable)
        focus: Optional focus area for entity/topic summaries
        
    Returns:
        Dictionary with summary, key_insights, and actionable_items
    """
    generator = SummaryGenerator()
    generated_summary = generator.generate_summary(text, summary_type, focus)
    
    return {
        "summary": generated_summary.summary,
        "key_insights": generated_summary.key_insights,
        "actionable_items": generated_summary.actionable_items
    }


class SummarizationPipeline:
    """
    Complete summarization pipeline for processing video content.
    
    Orchestrates the generation of multiple summary types for comprehensive
    knowledge extraction from video transcripts.
    """
    
    def __init__(self, session: Session):
        """
        Initialize the summarization pipeline.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.manager = SummaryManager(session)
    
    def process_video_summaries(self, video_id: str) -> Dict[str, Any]:
        """
        Process comprehensive summarization for a video.
        
        Generates video-level summary and actionable items summary.
        Entity and topic summaries are generated separately based on
        extracted entities and topics.
        
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
        
        stats = {
            "summaries_generated": 0,
            "summary_types": []
        }
        
        try:
            # Generate video-level summary
            video_summary = self.manager.generate_and_store_summary(
                video_id=video_id,
                summary_type="video"
            )
            stats["summaries_generated"] += 1
            stats["summary_types"].append("video")
            
            # Generate actionable items summary
            actionable_summary = self.manager.generate_and_store_summary(
                video_id=video_id,
                summary_type="actionable"
            )
            stats["summaries_generated"] += 1
            stats["summary_types"].append("actionable")
            
            return {
                "status": "success",
                "video_id": video_id,
                "stats": stats
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing summaries: {str(e)}",
                "video_id": video_id
            }
    
    def process_entity_summaries(self, video_id: str) -> Dict[str, Any]:
        """
        Process entity-focused summaries for a video.
        
        Generates summaries focused on specific entities mentioned in the video.
        
        Args:
            video_id: ID of the video to process
            
        Returns:
            Processing results with statistics
        """
        from app.database import EntityMention
        
        # Get entities mentioned in this video
        entity_mentions = self.session.query(EntityMention).join(TranscriptChunk).filter(
            TranscriptChunk.video_id == video_id
        ).all()
        
        # Get unique entities
        unique_entities = {}
        for mention in entity_mentions:
            if mention.entity_id not in unique_entities:
                unique_entities[mention.entity_id] = mention.entity
        
        stats = {
            "entity_summaries_generated": 0,
            "entities_processed": []
        }
        
        try:
            for entity_id, entity in unique_entities.items():
                # Generate entity-focused summary
                entity_summary = self.manager.generate_and_store_summary(
                    video_id=video_id,
                    summary_type="entity",
                    entity_id=entity_id,
                    focus=entity.name
                )
                
                stats["entity_summaries_generated"] += 1
                stats["entities_processed"].append({
                    "entity_id": entity_id,
                    "entity_name": entity.name,
                    "entity_type": entity.type
                })
            
            return {
                "status": "success",
                "video_id": video_id,
                "stats": stats
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing entity summaries: {str(e)}",
                "video_id": video_id
            }
    
    def process_topic_summaries(self, video_id: str) -> Dict[str, Any]:
        """
        Process topic-focused summaries for a video.
        
        Generates summaries focused on specific topics covered in the video.
        
        Args:
            video_id: ID of the video to process
            
        Returns:
            Processing results with statistics
        """
        from app.database import VideoTopic
        
        # Get topics associated with this video
        video_topics = self.session.query(VideoTopic).filter(
            VideoTopic.video_id == video_id
        ).all()
        
        stats = {
            "topic_summaries_generated": 0,
            "topics_processed": []
        }
        
        try:
            for video_topic in video_topics:
                # Generate topic-focused summary
                topic_summary = self.manager.generate_and_store_summary(
                    video_id=video_id,
                    summary_type="topic",
                    topic_id=video_topic.topic_id,
                    focus=video_topic.topic.name
                )
                
                stats["topic_summaries_generated"] += 1
                stats["topics_processed"].append({
                    "topic_id": video_topic.topic_id,
                    "topic_name": video_topic.topic.name,
                    "relevance_score": video_topic.relevance_score
                })
            
            return {
                "status": "success",
                "video_id": video_id,
                "stats": stats
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing topic summaries: {str(e)}",
                "video_id": video_id
            }