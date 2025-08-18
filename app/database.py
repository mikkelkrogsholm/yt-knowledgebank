"""
Database infrastructure for YouTube Knowledgebank.
Uses SQLAlchemy 2.0+ with SQLite and FTS5 extension support.
"""
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    create_engine, 
    Column, 
    String, 
    Integer, 
    DateTime, 
    Text, 
    ForeignKey,
    Index,
    Float
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool

# SQLAlchemy Base class
Base = declarative_base()


class Video(Base):
    """
    Video model representing processed YouTube videos.
    """
    __tablename__ = 'videos'
    
    # Primary key - using task_id from existing system
    id = Column(String, primary_key=True, nullable=False)
    
    # Video metadata
    title = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)  # Duration in seconds
    uploader = Column(String, nullable=False)
    url = Column(String, nullable=False)
    video_id = Column(String, nullable=False)  # YouTube video ID
    processed_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    transcript_chunks = relationship(
        "TranscriptChunk", 
        back_populates="video", 
        cascade="all, delete-orphan"
    )
    speakers = relationship(
        "Speaker", 
        back_populates="video", 
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Video(id='{self.id}', title='{self.title}')>"


class TranscriptChunk(Base):
    """
    Transcript chunk model representing timed segments of transcribed text.
    """
    __tablename__ = 'transcript_chunks'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to video
    video_id = Column(String, ForeignKey('videos.id'), nullable=False)
    
    # Timing information (in milliseconds)
    start_ms = Column(Integer, nullable=False)
    end_ms = Column(Integer, nullable=False)
    
    # Speaker information
    speaker_id = Column(String, nullable=True)  # Can be null for unidentified speakers
    
    # Transcript text and metadata
    text = Column(Text, nullable=False)
    word_count = Column(Integer, nullable=False, default=0)
    
    # Relationship back to video
    video = relationship("Video", back_populates="transcript_chunks")
    
    # Index for efficient querying by video and timestamp
    __table_args__ = (
        Index('idx_video_timestamp', 'video_id', 'start_ms'),
        Index('idx_video_speaker', 'video_id', 'speaker_id'),
    )
    
    def __repr__(self):
        return f"<TranscriptChunk(id={self.id}, video_id='{self.video_id}', start_ms={self.start_ms})>"


class Speaker(Base):
    """
    Speaker model representing identified speakers in videos.
    """
    __tablename__ = 'speakers'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to video
    video_id = Column(String, ForeignKey('videos.id'), nullable=False)
    
    # Speaker identification
    speaker_id = Column(String, nullable=False)  # e.g., "speaker_0", "speaker_1"
    name = Column(String, nullable=True)  # Human-readable name if available
    
    # Relationship back to video
    video = relationship("Video", back_populates="speakers")
    
    # Unique constraint: one speaker_id per video
    __table_args__ = (
        Index('idx_unique_speaker_per_video', 'video_id', 'speaker_id', unique=True),
    )
    
    def __repr__(self):
        return f"<Speaker(id={self.id}, video_id='{self.video_id}', speaker_id='{self.speaker_id}')>"


class Entity(Base):
    """
    Entity model representing extracted entities from transcripts.
    
    Entities can be people, books, concepts, companies, places, products, etc.
    that are mentioned in the video transcripts.
    """
    __tablename__ = 'entities'
    
    # Primary key
    id = Column(String, primary_key=True, nullable=False)
    
    # Entity information
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # person, book, concept, company, place, product, technology
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationship to entity mentions
    mentions = relationship(
        "EntityMention", 
        back_populates="entity", 
        cascade="all, delete-orphan"
    )
    
    # Index for efficient querying by type and name
    __table_args__ = (
        Index('idx_entity_type', 'type'),
        Index('idx_entity_name', 'name'),
        Index('idx_entity_type_name', 'type', 'name'),
    )
    
    def __repr__(self):
        return f"<Entity(id='{self.id}', name='{self.name}', type='{self.type}')>"


class EntityMention(Base):
    """
    EntityMention model representing specific mentions of entities in transcript chunks.
    
    Links entities to specific locations in transcripts with confidence scores and context.
    """
    __tablename__ = 'entity_mentions'
    
    # Primary key
    id = Column(String, primary_key=True, nullable=False)
    
    # Foreign keys
    entity_id = Column(String, ForeignKey('entities.id'), nullable=False)
    chunk_id = Column(Integer, ForeignKey('transcript_chunks.id'), nullable=False)
    
    # Mention metadata
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    context = Column(Text, nullable=True)  # Surrounding text that provides context
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    entity = relationship("Entity", back_populates="mentions")
    chunk = relationship("TranscriptChunk")
    
    # Index for efficient querying
    __table_args__ = (
        Index('idx_mention_entity', 'entity_id'),
        Index('idx_mention_chunk', 'chunk_id'),
        Index('idx_mention_confidence', 'confidence'),
        Index('idx_mention_entity_chunk', 'entity_id', 'chunk_id'),
    )
    
    def __repr__(self):
        return f"<EntityMention(id='{self.id}', entity_id='{self.entity_id}', chunk_id={self.chunk_id})>"


class EntityRelationship(Base):
    """
    EntityRelationship model representing relationships between entities.
    
    Used for building the knowledge graph by tracking how entities are connected
    through co-occurrence, influences, recommendations, etc.
    """
    __tablename__ = 'entity_relationships'
    
    # Primary key
    id = Column(String, primary_key=True, nullable=False)
    
    # Foreign keys to entities
    entity1_id = Column(String, ForeignKey('entities.id'), nullable=False)
    entity2_id = Column(String, ForeignKey('entities.id'), nullable=False)
    
    # Relationship metadata
    relationship_type = Column(String, nullable=False)  # mentions_together, influences, recommends, discusses
    strength = Column(Float, nullable=False)  # 0.0 to 1.0
    evidence = Column(Text, nullable=True)  # Context supporting the relationship
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    entity1 = relationship("Entity", foreign_keys=[entity1_id])
    entity2 = relationship("Entity", foreign_keys=[entity2_id])
    
    # Index for efficient querying
    __table_args__ = (
        Index('idx_relationship_entity1', 'entity1_id'),
        Index('idx_relationship_entity2', 'entity2_id'),
        Index('idx_relationship_type', 'relationship_type'),
        Index('idx_relationship_strength', 'strength'),
        Index('idx_relationship_entities', 'entity1_id', 'entity2_id'),
    )
    
    def __repr__(self):
        return f"<EntityRelationship(id='{self.id}', entity1_id='{self.entity1_id}', entity2_id='{self.entity2_id}', type='{self.relationship_type}')>"


class Topic(Base):
    """
    Topic model representing content topics with hierarchical structure.
    
    Topics organize video content into coherent categories and can have
    parent-child relationships for hierarchical organization.
    """
    __tablename__ = 'topics'
    
    # Primary key
    id = Column(String, primary_key=True, nullable=False)
    
    # Topic information
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    parent_topic_id = Column(String, ForeignKey('topics.id'), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Self-referential relationship for hierarchy
    parent_topic = relationship("Topic", remote_side=[id], back_populates="child_topics")
    child_topics = relationship("Topic", back_populates="parent_topic")
    
    # Relationship to video topics
    video_topics = relationship(
        "VideoTopic",
        back_populates="topic",
        cascade="all, delete-orphan"
    )
    
    # Index for efficient querying
    __table_args__ = (
        Index('idx_topic_name', 'name'),
        Index('idx_topic_parent', 'parent_topic_id'),
    )
    
    def __repr__(self):
        return f"<Topic(id='{self.id}', name='{self.name}', parent_id='{self.parent_topic_id}')>"


class VideoTopic(Base):
    """
    VideoTopic model representing the association between videos and topics.
    
    Links videos to topics with relevance scores indicating how well
    the topic represents the video content.
    """
    __tablename__ = 'video_topics'
    
    # Composite primary key
    video_id = Column(String, ForeignKey('videos.id'), primary_key=True)
    topic_id = Column(String, ForeignKey('topics.id'), primary_key=True)
    
    # Association metadata
    relevance_score = Column(Float, nullable=False)  # 0.0 to 1.0
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    video = relationship("Video")
    topic = relationship("Topic", back_populates="video_topics")
    
    # Index for efficient querying
    __table_args__ = (
        Index('idx_video_topic_video', 'video_id'),
        Index('idx_video_topic_topic', 'topic_id'),
        Index('idx_video_topic_relevance', 'relevance_score'),
    )
    
    def __repr__(self):
        return f"<VideoTopic(video_id='{self.video_id}', topic_id='{self.topic_id}', relevance={self.relevance_score})>"


class Summary(Base):
    """
    Summary model representing AI-generated summaries of video content.
    
    Supports multiple summary types: video-level, entity-focused, topic-focused,
    and actionable items extraction.
    """
    __tablename__ = 'summaries'
    
    # Primary key
    id = Column(String, primary_key=True, nullable=False)
    
    # Foreign keys
    video_id = Column(String, ForeignKey('videos.id'), nullable=False)
    entity_id = Column(String, ForeignKey('entities.id'), nullable=True)
    topic_id = Column(String, ForeignKey('topics.id'), nullable=True)
    
    # Summary metadata
    summary_type = Column(String, nullable=False)  # video, topic, entity, actionable
    content = Column(Text, nullable=False)
    generated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    video = relationship("Video")
    entity = relationship("Entity")
    topic = relationship("Topic")
    
    # Index for efficient querying
    __table_args__ = (
        Index('idx_summary_video', 'video_id'),
        Index('idx_summary_type', 'summary_type'),
        Index('idx_summary_entity', 'entity_id'),
        Index('idx_summary_topic', 'topic_id'),
        Index('idx_summary_video_type', 'video_id', 'summary_type'),
    )
    
    def __repr__(self):
        return f"<Summary(id='{self.id}', video_id='{self.video_id}', type='{self.summary_type}')>"


class DatabaseManager:
    """
    Database connection and session management.
    """
    
    def __init__(self, database_url: str):
        """
        Initialize database manager with connection pooling.
        
        Args:
            database_url: SQLAlchemy database URL (e.g., "sqlite:///data/knowledge_bank.db")
        """
        self.database_url = database_url
        
        # Configure engine with proper pooling for SQLite
        if database_url.startswith('sqlite'):
            # SQLite-specific configuration
            self.engine = create_engine(
                database_url,
                poolclass=StaticPool,
                connect_args={
                    "check_same_thread": False,
                    "timeout": 20
                },
                echo=False  # Set to True for SQL debugging
            )
        else:
            # Generic configuration for other databases
            self.engine = create_engine(
                database_url,
                pool_size=10,
                max_overflow=20,
                echo=False
            )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def get_session(self) -> Session:
        """
        Get a new database session.
        
        Returns:
            SQLAlchemy Session instance
        """
        return self.SessionLocal()
    
    def create_tables(self):
        """
        Create all database tables.
        """
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """
        Drop all database tables. Use with caution!
        """
        Base.metadata.drop_all(bind=self.engine)


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def init_database(database_url: str = "sqlite:////app/data/knowledge_bank.db") -> DatabaseManager:
    """
    Initialize the database with tables and return the database manager.
    
    Args:
        database_url: SQLAlchemy database URL
        
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    
    _db_manager = DatabaseManager(database_url)
    _db_manager.create_tables()
    
    return _db_manager


def get_database_session() -> Session:
    """
    Get a database session from the global database manager.
    
    Returns:
        SQLAlchemy Session instance
        
    Raises:
        RuntimeError: If database has not been initialized
    """
    global _db_manager
    
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    return _db_manager.get_session()


def get_database_manager() -> DatabaseManager:
    """
    Get the global database manager instance.
    
    Returns:
        DatabaseManager instance
        
    Raises:
        RuntimeError: If database has not been initialized
    """
    global _db_manager
    
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    return _db_manager