"""
Context Assembler for RAG Pipeline.

This module handles the assembly of search results into coherent context
for answer generation, including deduplication, ranking, and token management.

Phase 4 Module 2: Context Assembly
"""
import re
from typing import List, Dict, Set, Any
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class ContextChunk:
    """Represents a processed context chunk with metadata."""
    text: str
    video_id: str
    chunk_id: int
    start_ms: int
    end_ms: int
    relevance_score: float
    token_count: int


class ContextAssembler:
    """
    Assembles search results into optimized context for answer generation.
    
    Handles deduplication, ranking, token limits, and context formatting
    to provide the most relevant information for question answering.
    """
    
    def __init__(self):
        """Initialize the context assembler."""
        self.similarity_threshold = 0.85  # Threshold for duplicate detection
        self.max_chunk_tokens = 300  # Maximum tokens per chunk
        self.context_separator = "\n\n"
        self.source_template = "[Source: Video {video_id}, {start_time}]\n{text}"
    
    def assemble_context(self, search_results, max_tokens: int = 2000) -> str:
        """
        Assemble search results into coherent context.
        
        Args:
            search_results: List of search result objects
            max_tokens: Maximum tokens for assembled context
            
        Returns:
            Assembled context string
        """
        if not search_results:
            return ""
        
        # Step 1: Convert search results to context chunks
        chunks = self._convert_to_chunks(search_results)
        
        # Step 2: Remove duplicates
        chunks = self._deduplicate_chunks(chunks)
        
        # Step 3: Rank and select best chunks within token limit
        selected_chunks = self._select_chunks_by_tokens(chunks, max_tokens)
        
        # Step 4: Format into coherent context
        context = self._format_context(selected_chunks)
        
        return context
    
    def _convert_to_chunks(self, search_results) -> List[ContextChunk]:
        """Convert search results to ContextChunk objects."""
        chunks = []
        
        for result in search_results:
            # Estimate token count (rough approximation: 1 token ≈ 0.75 words)
            word_count = len(result.text.split())
            token_count = int(word_count * 1.3)  # Conservative estimate
            
            chunk = ContextChunk(
                text=result.text,
                video_id=result.video_id,
                chunk_id=result.id,
                start_ms=result.start_ms,
                end_ms=result.end_ms,
                relevance_score=float(result.rank),
                token_count=token_count
            )
            chunks.append(chunk)
        
        return chunks
    
    def _deduplicate_chunks(self, chunks: List[ContextChunk]) -> List[ContextChunk]:
        """Remove duplicate or highly similar chunks."""
        deduplicated = []
        seen_texts = set()
        
        # Sort by relevance score (descending) to keep best versions
        chunks.sort(key=lambda x: x.relevance_score, reverse=True)
        
        for chunk in chunks:
            # Check for exact duplicates
            text_normalized = self._normalize_text(chunk.text)
            if text_normalized in seen_texts:
                continue
            
            # Check for high similarity
            is_duplicate = False
            for existing_chunk in deduplicated:
                similarity = self._calculate_text_similarity(
                    chunk.text, existing_chunk.text
                )
                if similarity >= self.similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated.append(chunk)
                seen_texts.add(text_normalized)
        
        return deduplicated
    
    def _select_chunks_by_tokens(self, chunks: List[ContextChunk], 
                                max_tokens: int) -> List[ContextChunk]:
        """Select chunks that fit within token limit."""
        # Sort by relevance score (descending)
        chunks.sort(key=lambda x: x.relevance_score, reverse=True)
        
        selected = []
        current_tokens = 0
        
        for chunk in chunks:
            # Add some overhead for formatting
            chunk_tokens_with_overhead = chunk.token_count + 20
            
            if current_tokens + chunk_tokens_with_overhead <= max_tokens:
                selected.append(chunk)
                current_tokens += chunk_tokens_with_overhead
            else:
                # Check if we can fit a truncated version
                remaining_tokens = max_tokens - current_tokens - 20
                if remaining_tokens >= 50:  # Minimum useful chunk size
                    truncated_chunk = self._truncate_chunk(chunk, remaining_tokens)
                    if truncated_chunk:
                        selected.append(truncated_chunk)
                break
        
        return selected
    
    def _format_context(self, chunks: List[ContextChunk]) -> str:
        """Format chunks into coherent context string."""
        if not chunks:
            return ""
        
        # Sort by video and timestamp for logical flow
        chunks.sort(key=lambda x: (x.video_id, x.start_ms))
        
        formatted_chunks = []
        current_video = None
        
        for chunk in chunks:
            # Add video separator if needed
            if current_video != chunk.video_id:
                if current_video is not None:
                    formatted_chunks.append("")  # Add blank line between videos
                current_video = chunk.video_id
            
            # Format chunk with source information
            start_time = self._format_timestamp(chunk.start_ms)
            formatted_text = self.source_template.format(
                video_id=chunk.video_id,
                start_time=start_time,
                text=chunk.text
            )
            
            formatted_chunks.append(formatted_text)
        
        return self.context_separator.join(formatted_chunks)
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for duplicate detection."""
        # Convert to lowercase, remove extra whitespace
        normalized = re.sub(r'\s+', ' ', text.lower().strip())
        
        # Remove common punctuation variations
        normalized = re.sub(r'[.,!?;:]', '', normalized)
        
        return normalized
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text chunks."""
        # Normalize texts
        norm1 = self._normalize_text(text1)
        norm2 = self._normalize_text(text2)
        
        # Use SequenceMatcher for similarity
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Boost similarity for substring matches
        if norm1 in norm2 or norm2 in norm1:
            similarity = max(similarity, 0.9)
        
        return similarity
    
    def _truncate_chunk(self, chunk: ContextChunk, max_tokens: int) -> ContextChunk:
        """Truncate chunk to fit within token limit."""
        if chunk.token_count <= max_tokens:
            return chunk
        
        # Estimate how many words to keep
        words = chunk.text.split()
        target_words = int(max_tokens / 1.3)  # Reverse of token estimation
        
        if target_words < 10:  # Too small to be useful
            return None
        
        # Keep first part of text and add ellipsis
        truncated_words = words[:target_words]
        truncated_text = " ".join(truncated_words) + "..."
        
        # Recalculate token count
        new_token_count = int(len(truncated_words) * 1.3)
        
        return ContextChunk(
            text=truncated_text,
            video_id=chunk.video_id,
            chunk_id=chunk.chunk_id,
            start_ms=chunk.start_ms,
            end_ms=chunk.end_ms,
            relevance_score=chunk.relevance_score * 0.9,  # Slight penalty for truncation
            token_count=new_token_count
        )
    
    def _format_timestamp(self, ms: int) -> str:
        """Format milliseconds as readable timestamp."""
        seconds = ms // 1000
        minutes = seconds // 60
        hours = minutes // 60
        
        seconds = seconds % 60
        minutes = minutes % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    def get_context_stats(self, context: str) -> Dict[str, Any]:
        """Get statistics about assembled context."""
        if not context:
            return {
                "total_tokens": 0,
                "total_chunks": 0,
                "total_videos": 0,
                "average_chunk_length": 0
            }
        
        # Count chunks (separated by double newlines)
        chunks = context.split(self.context_separator)
        chunks = [c.strip() for c in chunks if c.strip()]
        
        # Count unique videos
        video_ids = set()
        for chunk in chunks:
            if "Video " in chunk:
                # Extract video ID from source line
                match = re.search(r'Video (\w+)', chunk)
                if match:
                    video_ids.add(match.group(1))
        
        # Estimate total tokens
        total_words = len(context.split())
        total_tokens = int(total_words * 1.3)
        
        # Calculate average chunk length
        if chunks:
            chunk_lengths = [len(chunk.split()) for chunk in chunks]
            avg_chunk_length = sum(chunk_lengths) / len(chunk_lengths)
        else:
            avg_chunk_length = 0
        
        return {
            "total_tokens": total_tokens,
            "total_chunks": len(chunks),
            "total_videos": len(video_ids),
            "average_chunk_length": round(avg_chunk_length, 1),
            "video_ids": list(video_ids)
        }