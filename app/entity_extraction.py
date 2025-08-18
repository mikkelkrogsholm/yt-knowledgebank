"""
Entity extraction module for YouTube Knowledgebank.

This module provides entity recognition and extraction capabilities using OpenAI's
GPT models to identify people, books, concepts, companies, places, and other
entities from video transcripts.

Phase 3 Module 1: Entity Recognition System
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

from app.database import Entity, EntityMention, EntityRelationship, TranscriptChunk
from app.settings import get_openai_api_key, get_model_config


@dataclass
class ExtractedEntity:
    """Represents an entity extracted from text."""
    name: str
    type: str
    confidence: float
    context: str


class EntityExtractor:
    """
    OpenAI-based entity extractor using GPT models.
    
    Extracts entities from transcript text using structured prompts
    and returns standardized entity information.
    """
    
    def __init__(self):
        """Initialize the entity extractor."""
        self.api_key = get_openai_api_key()
        self.model_config = get_model_config()
        
        if not self.api_key:
            raise ValueError("OpenAI API key not configured. Please set it in settings.")
        
        # Set up OpenAI client
        openai.api_key = self.api_key
        
        # Entity extraction model configuration
        self.model = self.model_config["models"]["entity_extraction"]
        self.temperature = self.model_config["limits"]["temperature_extraction"]
        self.max_tokens = self.model_config["limits"]["max_tokens_extraction"]
    
    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """
        Extract entities from the given text using OpenAI.
        
        Args:
            text: The text to extract entities from
            
        Returns:
            List of ExtractedEntity objects
        """
        try:
            prompt = self._build_extraction_prompt(text)
            
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert entity extraction system. Extract meaningful entities that provide value for knowledge discovery."
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
            entity_data = json.loads(content)
            
            # Convert to ExtractedEntity objects
            entities = []
            for entity_dict in entity_data.get("entities", []):
                entity = ExtractedEntity(
                    name=entity_dict["name"],
                    type=entity_dict["type"],
                    confidence=entity_dict["confidence"],
                    context=entity_dict["context"]
                )
                entities.append(entity)
            
            return entities
            
        except Exception as e:
            print(f"Error extracting entities: {e}")
            return []
    
    def _build_extraction_prompt(self, text: str) -> str:
        """Build the entity extraction prompt."""
        return f"""Extract entities from this transcript chunk. Return JSON with:
{{
  "entities": [
    {{
      "name": "entity name",
      "type": "person|book|concept|company|place|product|technology",
      "confidence": 0.0-1.0,
      "context": "surrounding text"
    }}
  ]
}}

Focus on extracting meaningful entities that provide value for knowledge discovery.

Text to analyze:
{text}"""


class EntityManager:
    """
    Manages entity storage, deduplication, and linking.
    
    Handles entity resolution, fuzzy matching for deduplication,
    and timeline tracking across video content.
    """
    
    def __init__(self, session: Session):
        """
        Initialize the entity manager.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.similarity_threshold = 0.85  # Threshold for fuzzy matching
    
    def resolve_entity(self, entity_data: Dict[str, any]) -> Entity:
        """
        Resolve an extracted entity to an existing or new Entity record.
        
        Uses fuzzy matching to deduplicate similar entities.
        
        Args:
            entity_data: Dictionary with name, type, confidence, context
            
        Returns:
            Entity object (existing or newly created)
        """
        name = entity_data["name"]
        entity_type = entity_data["type"]
        
        # First try exact match
        existing = self.session.query(Entity).filter(
            Entity.name == name,
            Entity.type == entity_type
        ).first()
        
        if existing:
            return existing
        
        # Try fuzzy matching for similar entities of the same type
        similar_entities = self.session.query(Entity).filter(
            Entity.type == entity_type
        ).all()
        
        for existing_entity in similar_entities:
            similarity = self._calculate_similarity(name, existing_entity.name)
            if similarity >= self.similarity_threshold:
                # Update with the more complete name if needed
                if len(name) > len(existing_entity.name):
                    existing_entity.name = name
                    self.session.commit()
                return existing_entity
        
        # Create new entity
        entity_id = f"entity_{uuid.uuid4().hex[:8]}"
        new_entity = Entity(
            id=entity_id,
            name=name,
            type=entity_type,
            description=f"Extracted {entity_type}: {name}",
            created_at=datetime.now(timezone.utc)
        )
        
        self.session.add(new_entity)
        self.session.commit()
        return new_entity
    
    def add_mention(self, entity_id: str, chunk_id: int, confidence: float, context: str) -> EntityMention:
        """
        Add a mention of an entity in a specific transcript chunk.
        
        Args:
            entity_id: ID of the entity
            chunk_id: ID of the transcript chunk
            confidence: Confidence score (0.0 to 1.0)
            context: Context text around the mention
            
        Returns:
            EntityMention object
        """
        mention_id = f"mention_{uuid.uuid4().hex[:8]}"
        mention = EntityMention(
            id=mention_id,
            entity_id=entity_id,
            chunk_id=chunk_id,
            confidence=confidence,
            context=context,
            created_at=datetime.now(timezone.utc)
        )
        
        self.session.add(mention)
        self.session.commit()
        return mention
    
    def get_entity_timeline(self, entity_id: str) -> List[Dict[str, any]]:
        """
        Get timeline of mentions for an entity across videos.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            List of mention data with timestamps
        """
        mentions = self.session.query(EntityMention).join(TranscriptChunk).filter(
            EntityMention.entity_id == entity_id
        ).order_by(TranscriptChunk.start_ms).all()
        
        timeline = []
        for mention in mentions:
            timeline.append({
                "mention_id": mention.id,
                "chunk_id": mention.chunk_id,
                "video_id": mention.chunk.video_id,
                "start_ms": mention.chunk.start_ms,
                "end_ms": mention.chunk.end_ms,
                "confidence": mention.confidence,
                "context": mention.context,
                "text": mention.chunk.text
            })
        
        return timeline
    
    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two entity names.
        
        Args:
            name1: First entity name
            name2: Second entity name
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Normalize names for comparison
        norm1 = self._normalize_name(name1)
        norm2 = self._normalize_name(name2)
        
        # Use SequenceMatcher for similarity
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Boost similarity for substring matches
        if norm1 in norm2 or norm2 in norm1:
            similarity = max(similarity, 0.9)
        
        return similarity
    
    def _normalize_name(self, name: str) -> str:
        """Normalize entity name for comparison."""
        # Convert to lowercase and remove extra whitespace
        normalized = re.sub(r'\s+', ' ', name.lower().strip())
        
        # Remove common prefixes/suffixes that might vary
        patterns = [
            r'\buniversity\b',
            r'\binc\.?\b',
            r'\bcorp\.?\b',
            r'\bltd\.?\b',
            r'\bco\.?\b'
        ]
        
        for pattern in patterns:
            normalized = re.sub(pattern, '', normalized).strip()
        
        return normalized


def extract_entities_from_text(text: str) -> List[Dict[str, any]]:
    """
    Extract entities from text using OpenAI NER.
    
    This is a standalone function for entity extraction that can be used
    independently of the EntityManager class.
    
    Args:
        text: Text to extract entities from
        
    Returns:
        List of entity dictionaries with name, type, confidence, context
    """
    extractor = EntityExtractor()
    extracted_entities = extractor.extract_entities(text)
    
    # Convert to dictionaries for compatibility
    entities = []
    for entity in extracted_entities:
        entities.append({
            "name": entity.name,
            "type": entity.type,
            "confidence": entity.confidence,
            "context": entity.context
        })
    
    return entities


class EntityExtractionPipeline:
    """
    Complete entity extraction pipeline for processing transcript chunks.
    
    Orchestrates entity extraction, resolution, and storage for video transcripts.
    """
    
    def __init__(self, session: Session):
        """
        Initialize the extraction pipeline.
        
        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.extractor = EntityExtractor()
        self.manager = EntityManager(session)
    
    def process_video_entities(self, video_id: str) -> Dict[str, any]:
        """
        Process entity extraction for all transcript chunks in a video.
        
        Args:
            video_id: ID of the video to process
            
        Returns:
            Processing results with statistics
        """
        # Get all transcript chunks for the video
        chunks = self.session.query(TranscriptChunk).filter(
            TranscriptChunk.video_id == video_id
        ).order_by(TranscriptChunk.start_ms).all()
        
        if not chunks:
            return {
                "status": "error",
                "message": f"No transcript chunks found for video {video_id}"
            }
        
        stats = {
            "chunks_processed": 0,
            "entities_extracted": 0,
            "mentions_created": 0,
            "unique_entities": set()
        }
        
        for chunk in chunks:
            try:
                # Extract entities from chunk text
                extracted_entities = self.extractor.extract_entities(chunk.text)
                
                for entity_data in extracted_entities:
                    # Convert ExtractedEntity to dict for resolve_entity
                    entity_dict = {
                        "name": entity_data.name,
                        "type": entity_data.type,
                        "confidence": entity_data.confidence,
                        "context": entity_data.context
                    }
                    
                    # Resolve to existing or create new entity
                    entity = self.manager.resolve_entity(entity_dict)
                    
                    # Add mention
                    self.manager.add_mention(
                        entity.id,
                        chunk.id,
                        entity_data.confidence,
                        entity_data.context
                    )
                    
                    stats["entities_extracted"] += 1
                    stats["mentions_created"] += 1
                    stats["unique_entities"].add(entity.id)
                
                stats["chunks_processed"] += 1
                
            except Exception as e:
                print(f"Error processing chunk {chunk.id}: {e}")
                continue
        
        # Convert set to count for JSON serialization
        stats["unique_entities"] = len(stats["unique_entities"])
        
        return {
            "status": "success",
            "video_id": video_id,
            "stats": stats
        }