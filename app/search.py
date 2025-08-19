"""
FTS5 search implementation for YouTube Knowledgebank.
Provides high-performance full-text search with highlighting and filtering.
"""

import sqlite3
import re
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class SearchResult:
    """Represents a search result with highlighting and metadata."""
    id: int
    video_id: str
    speaker_id: str
    start_ms: int
    end_ms: int
    text: str
    highlighted_text: str
    rank: float
    word_count: int
    video_title: Optional[str] = None


class SearchManager:
    """Manages FTS5 full-text search operations."""
    
    def __init__(self, db_path: str = '/app/data/knowledge_bank.db'):
        self.db_path = db_path
        self._setup_fts()
    
    def _setup_fts(self):
        """Set up FTS5 virtual table and triggers."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Create FTS5 virtual table
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS transcript_chunks_fts USING fts5(
                    text,
                    video_id UNINDEXED,
                    speaker_id UNINDEXED,
                    content='transcript_chunks',
                    content_rowid='id'
                )
            """)
            
            # Create triggers to keep FTS5 in sync
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS transcript_chunks_ai AFTER INSERT ON transcript_chunks BEGIN
                    INSERT INTO transcript_chunks_fts(rowid, text, video_id, speaker_id)
                    VALUES (new.id, new.text, new.video_id, new.speaker_id);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS transcript_chunks_ad AFTER DELETE ON transcript_chunks BEGIN
                    INSERT INTO transcript_chunks_fts(transcript_chunks_fts, rowid, text, video_id, speaker_id)
                    VALUES ('delete', old.id, old.text, old.video_id, old.speaker_id);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS transcript_chunks_au AFTER UPDATE ON transcript_chunks BEGIN
                    INSERT INTO transcript_chunks_fts(transcript_chunks_fts, rowid, text, video_id, speaker_id)
                    VALUES ('delete', old.id, old.text, old.video_id, old.speaker_id);
                    INSERT INTO transcript_chunks_fts(rowid, text, video_id, speaker_id)
                    VALUES (new.id, new.text, new.video_id, new.speaker_id);
                END
            """)
            
            # Check if FTS table needs initial population
            cursor.execute("SELECT COUNT(*) FROM transcript_chunks_fts")
            fts_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM transcript_chunks")
            original_count = cursor.fetchone()[0]
            
            if fts_count != original_count:
                # Populate FTS table with existing data
                cursor.execute("DELETE FROM transcript_chunks_fts")
                cursor.execute("""
                    INSERT INTO transcript_chunks_fts(rowid, text, video_id, speaker_id)
                    SELECT id, text, video_id, speaker_id FROM transcript_chunks
                """)
                # Rebuild the FTS index for optimal performance
                cursor.execute("INSERT INTO transcript_chunks_fts(transcript_chunks_fts) VALUES('rebuild')")
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def search(self, 
               query: str,
               video_id: Optional[str] = None,
               speaker_id: Optional[str] = None,
               start_date: Optional[datetime] = None,
               end_date: Optional[datetime] = None,
               min_duration: Optional[int] = None,
               max_duration: Optional[int] = None,
               uploader: Optional[str] = None,
               sort_by: str = "relevance",
               sort_order: str = "desc",
               limit: int = 50,
               offset: int = 0) -> List[SearchResult]:
        """
        Perform full-text search with optional filters and sorting.
        
        Args:
            query: Search query (supports FTS5 syntax)
            video_id: Filter by specific video
            speaker_id: Filter by specific speaker
            start_date: Filter by videos processed after this date
            end_date: Filter by videos processed before this date
            min_duration: Filter by minimum video duration in seconds
            max_duration: Filter by maximum video duration in seconds
            uploader: Filter by channel/uploader name (partial match)
            sort_by: Sort criteria - "relevance", "date", "duration", "alphabetical"
            sort_order: Sort order - "desc" or "asc"
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of SearchResult objects
        """
        if not query or not query.strip():
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Build the base FTS query
            fts_query = self._build_fts_query(query)
            
            # Build the full SQL with filters and sorting
            sql, params = self._build_search_sql(
                fts_query, video_id, speaker_id, start_date, end_date, 
                min_duration, max_duration, uploader, sort_by, sort_order, limit, offset
            )
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Convert to SearchResult objects
            results = []
            for row in rows:
                highlighted_text = self._highlight_text(row[5], query)
                
                result = SearchResult(
                    id=row[0],
                    video_id=row[1],
                    speaker_id=row[2],
                    start_ms=row[3],
                    end_ms=row[4],
                    text=row[5],
                    highlighted_text=highlighted_text,
                    rank=row[6],
                    word_count=row[7],
                    video_title=row[8] if len(row) > 8 else None
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            raise e
        finally:
            conn.close()
    
    def _build_fts_query(self, query: str) -> str:
        """Build FTS5 query string with proper escaping."""
        # Clean and escape the query
        query = query.strip()
        
        # If it's already a phrase query, return as-is
        if query.startswith('"') and query.endswith('"'):
            return query
        
        # Check for FTS5 operators
        has_fts_operators = any(op in query.upper() for op in [' AND ', ' OR ', ' NOT '])
        
        if has_fts_operators:
            return query
        
        # For queries with special characters, always use phrase search
        has_special_chars = any(char in query for char in ["'", "-", ".", "!", "?", ","])
        
        if has_special_chars:
            return f'"{query}"'
        
        # For simple queries, split into terms and create an OR query
        terms = query.split()
        if len(terms) == 1:
            return terms[0]
        
        # Create OR query for multiple terms
        escaped_terms = [f'"{term}"' if ' ' in term else term for term in terms]
        return ' OR '.join(escaped_terms)
    
    def _build_search_sql(self, 
                         fts_query: str,
                         video_id: Optional[str],
                         speaker_id: Optional[str],
                         start_date: Optional[datetime],
                         end_date: Optional[datetime],
                         min_duration: Optional[int],
                         max_duration: Optional[int],
                         uploader: Optional[str],
                         sort_by: str,
                         sort_order: str,
                         limit: int,
                         offset: int) -> tuple:
        """Build the complete search SQL with filters and sorting."""
        
        sql = """
            SELECT 
                tc.id,
                tc.video_id,
                tc.speaker_id,
                tc.start_ms,
                tc.end_ms,
                tc.text,
                rank,
                tc.word_count,
                v.title as video_title,
                v.duration,
                v.uploader,
                v.processed_date
            FROM transcript_chunks_fts
            JOIN transcript_chunks tc ON tc.id = transcript_chunks_fts.rowid
            JOIN videos v ON v.id = tc.video_id
        """
        
        # Build WHERE clause
        where_conditions = ["transcript_chunks_fts MATCH ?"]
        params = [fts_query]
        
        if video_id:
            where_conditions.append("tc.video_id = ?")
            params.append(video_id)
        
        if speaker_id:
            where_conditions.append("tc.speaker_id = ?")
            params.append(speaker_id)
        
        if start_date:
            where_conditions.append("v.processed_date >= ?")
            params.append(start_date.isoformat())
        
        if end_date:
            where_conditions.append("v.processed_date <= ?")
            params.append(end_date.isoformat())
        
        if min_duration:
            where_conditions.append("v.duration >= ?")
            params.append(min_duration)
        
        if max_duration:
            where_conditions.append("v.duration <= ?")
            params.append(max_duration)
        
        if uploader:
            where_conditions.append("v.uploader LIKE ?")
            params.append(f"%{uploader}%")
        
        if where_conditions:
            sql += " WHERE " + " AND ".join(where_conditions)
        
        # Build ORDER BY clause
        order_clause = self._build_order_clause(sort_by, sort_order)
        sql += f" ORDER BY {order_clause}"
        
        # Add pagination
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        return sql, params
    
    def _build_order_clause(self, sort_by: str, sort_order: str) -> str:
        """Build ORDER BY clause based on sort criteria."""
        direction = "DESC" if sort_order.upper() == "DESC" else "ASC"
        
        sort_mapping = {
            "relevance": "rank DESC",  # FTS5 rank (higher/less negative is better)
            "date": f"v.processed_date {direction}",
            "duration": f"v.duration {direction}",
            "alphabetical": f"v.title {direction}"
        }
        
        return sort_mapping.get(sort_by, "rank DESC")
    
    def _highlight_text(self, text: str, query: str) -> str:
        """
        Add highlighting to search terms in text.
        
        Args:
            text: Original text
            query: Search query
            
        Returns:
            Text with <mark> tags around matching terms
        """
        if not query or not text:
            return text
        
        # Extract search terms from query
        terms = self._extract_search_terms(query)
        
        if not terms:
            return text
        
        # Sort terms by length (longest first) to avoid partial replacements
        terms.sort(key=len, reverse=True)
        
        highlighted = text
        for term in terms:
            # Case-insensitive replacement with word boundaries
            pattern = r'\b' + re.escape(term) + r'\b'
            highlighted = re.sub(
                pattern, 
                f'<mark>\\g<0></mark>', 
                highlighted, 
                flags=re.IGNORECASE
            )
        
        return highlighted
    
    def _extract_search_terms(self, query: str) -> List[str]:
        """Extract individual search terms from query."""
        terms = []
        
        # Handle phrase queries
        phrase_pattern = r'"([^"]+)"'
        phrases = re.findall(phrase_pattern, query)
        for phrase in phrases:
            terms.append(phrase)
            query = query.replace(f'"{phrase}"', '')
        
        # Handle individual words (remove FTS5 operators)
        words = query.split()
        for word in words:
            word = word.strip()
            if word and word.upper() not in ['AND', 'OR', 'NOT']:
                # Remove wildcards and other FTS5 syntax
                word = word.rstrip('*').strip()
                if word:
                    terms.append(word)
        
        return terms
    
    def benchmark_search(self, iterations: int = 10) -> Dict[str, Any]:
        """
        Benchmark search performance with various queries.
        
        Args:
            iterations: Number of iterations per query
            
        Returns:
            Performance statistics
        """
        test_queries = [
            "books",
            "life changing",
            "scared important",
            "books AND life",
            "book*",
            '"life changing"',
        ]
        
        results = {}
        total_time = 0
        total_results = 0
        
        for query in test_queries:
            query_times = []
            query_results = 0
            
            for _ in range(iterations):
                start_time = time.time()
                search_results = self.search(query)
                end_time = time.time()
                
                duration_ms = (end_time - start_time) * 1000
                query_times.append(duration_ms)
                query_results = len(search_results)
            
            avg_time = sum(query_times) / len(query_times)
            min_time = min(query_times)
            max_time = max(query_times)
            
            results[query] = {
                'avg_time_ms': avg_time,
                'min_time_ms': min_time,
                'max_time_ms': max_time,
                'results_count': query_results
            }
            
            total_time += avg_time
            total_results += query_results
        
        results['summary'] = {
            'total_queries': len(test_queries),
            'avg_time_per_query_ms': total_time / len(test_queries),
            'total_results': total_results,
            'all_under_500ms': all(r['max_time_ms'] < 500 for r in results.values() 
                                 if isinstance(r, dict) and 'max_time_ms' in r)
        }
        
        return results
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get search index statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get FTS table stats
            cursor.execute("SELECT COUNT(*) FROM transcript_chunks_fts")
            fts_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM transcript_chunks")
            original_count = cursor.fetchone()[0]
            
            # Get total word count
            cursor.execute("SELECT SUM(word_count) FROM transcript_chunks")
            total_words = cursor.fetchone()[0] or 0
            
            # Get video count
            cursor.execute("SELECT COUNT(DISTINCT video_id) FROM transcript_chunks")
            video_count = cursor.fetchone()[0]
            
            # Get speaker count
            cursor.execute("SELECT COUNT(DISTINCT speaker_id) FROM transcript_chunks")
            speaker_count = cursor.fetchone()[0]
            
            return {
                'fts_entries': fts_count,
                'original_entries': original_count,
                'sync_status': 'synced' if fts_count == original_count else 'out_of_sync',
                'total_words': total_words,
                'video_count': video_count,
                'speaker_count': speaker_count
            }
            
        finally:
            conn.close()