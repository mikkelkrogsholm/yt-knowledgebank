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
    Index
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