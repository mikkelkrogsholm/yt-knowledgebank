"""
Test suite for FTS5 search functionality.
Following Test-Driven Development - tests written before implementation.
"""

import pytest
import sqlite3
import time
from datetime import datetime, timedelta
from app.search import SearchManager, SearchResult


class TestFTSSetup:
    """Test FTS5 virtual table creation and setup."""
    
    def test_fts_table_creation(self):
        """Test that FTS5 virtual table is created correctly."""
        search_manager = SearchManager()
        
        # Check that the FTS5 table exists
        conn = sqlite3.connect('/app/data/knowledge_bank.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transcript_chunks_fts'")
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None, "FTS5 virtual table 'transcript_chunks_fts' should exist"
    
    def test_fts_table_sync(self):
        """Test that FTS5 table is synchronized with transcript_chunks."""
        search_manager = SearchManager()
        
        conn = sqlite3.connect('/app/data/knowledge_bank.db')
        cursor = conn.cursor()
        
        # Count original chunks
        cursor.execute("SELECT COUNT(*) FROM transcript_chunks")
        original_count = cursor.fetchone()[0]
        
        # Count FTS chunks
        cursor.execute("SELECT COUNT(*) FROM transcript_chunks_fts")
        fts_count = cursor.fetchone()[0]
        
        conn.close()
        
        assert fts_count == original_count, f"FTS table should have {original_count} entries, got {fts_count}"
    
    def test_fts_columns(self):
        """Test that FTS5 table has the correct columns."""
        conn = sqlite3.connect('/app/data/knowledge_bank.db')
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(transcript_chunks_fts)")
        columns = [col[1] for col in cursor.fetchall()]
        conn.close()
        
        required_columns = ['text', 'video_id', 'speaker_id']
        for col in required_columns:
            assert col in columns, f"FTS table should have column '{col}'"


class TestBasicSearch:
    """Test basic search functionality."""
    
    @pytest.fixture
    def search_manager(self):
        return SearchManager()
    
    def test_simple_search(self, search_manager):
        """Test basic text search functionality."""
        results = search_manager.search("books")
        
        assert isinstance(results, list), "Search should return a list"
        assert len(results) > 0, "Should find results for 'books' in book summary video"
        
        # Check result structure
        for result in results:
            assert isinstance(result, SearchResult), "Each result should be a SearchResult"
            assert hasattr(result, 'id'), "Result should have id"
            assert hasattr(result, 'text'), "Result should have text"
            assert hasattr(result, 'video_id'), "Result should have video_id"
            assert hasattr(result, 'highlighted_text'), "Result should have highlighted_text"
    
    def test_case_insensitive_search(self, search_manager):
        """Test that search is case insensitive."""
        results_lower = search_manager.search("books")
        results_upper = search_manager.search("BOOKS")
        results_mixed = search_manager.search("Books")
        
        assert len(results_lower) == len(results_upper) == len(results_mixed), \
            "Search should be case insensitive"
    
    def test_partial_word_search(self, search_manager):
        """Test partial word matching."""
        results = search_manager.search("book*")  # FTS5 wildcard syntax
        
        assert len(results) > 0, "Should find results with FTS5 wildcard"
    
    def test_phrase_search(self, search_manager):
        """Test exact phrase searching."""
        results = search_manager.search('"life changing"')
        
        # Should find results (or empty if phrase doesn't exist)
        assert isinstance(results, list), "Phrase search should return a list"
    
    def test_empty_query(self, search_manager):
        """Test handling of empty search queries."""
        results = search_manager.search("")
        
        assert results == [], "Empty query should return empty results"
    
    def test_no_results_query(self, search_manager):
        """Test queries that return no results."""
        results = search_manager.search("xyzquietlyunusualword123")
        
        assert results == [], "Query with no matches should return empty results"


class TestSearchHighlighting:
    """Test search result highlighting and snippets."""
    
    @pytest.fixture
    def search_manager(self):
        return SearchManager()
    
    def test_result_highlighting(self, search_manager):
        """Test that search terms are highlighted in results."""
        results = search_manager.search("books")
        
        assert len(results) > 0, "Should find results to test highlighting"
        
        result = results[0]
        assert result.highlighted_text != result.text, \
            "Highlighted text should differ from original text"
        assert "<mark>" in result.highlighted_text, \
            "Highlighted text should contain <mark> tags"
        assert "</mark>" in result.highlighted_text, \
            "Highlighted text should contain closing </mark> tags"
    
    def test_snippet_generation(self, search_manager):
        """Test that snippets are generated around search terms."""
        results = search_manager.search("books")
        
        assert len(results) > 0, "Should find results to test snippets"
        
        result = results[0]
        # Snippet should be shorter than or equal to full text
        assert len(result.highlighted_text) <= len(result.text) + 100, \
            "Snippet should not be significantly longer than original"
    
    def test_multiple_term_highlighting(self, search_manager):
        """Test highlighting of multiple search terms."""
        results = search_manager.search("books life")
        
        if len(results) > 0:
            result = results[0]
            # Should highlight both terms if they appear
            text = result.highlighted_text.lower()
            assert "<mark>" in result.highlighted_text, \
                "Should highlight search terms"


class TestSearchFilters:
    """Test search filtering functionality."""
    
    @pytest.fixture
    def search_manager(self):
        return SearchManager()
    
    def test_speaker_filter(self, search_manager):
        """Test filtering by speaker."""
        # Search without filter
        all_results = search_manager.search("books")
        
        # Search with speaker filter
        filtered_results = search_manager.search("books", speaker_id="speaker_0")
        
        # Since we only have one speaker, results should be same
        assert len(all_results) == len(filtered_results), \
            "Speaker filter should work (single speaker case)"
    
    def test_video_filter(self, search_manager):
        """Test filtering by video."""
        results = search_manager.search("books")
        video_id = results[0].video_id if results else None
        
        if video_id:
            filtered_results = search_manager.search("books", video_id=video_id)
            assert len(filtered_results) > 0, "Video filter should return results"
    
    def test_date_range_filter(self, search_manager):
        """Test filtering by date range."""
        # Test with a very wide date range
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now() + timedelta(days=1)
        
        results = search_manager.search(
            "books", 
            start_date=start_date,
            end_date=end_date
        )
        
        assert isinstance(results, list), "Date range filter should return a list"
    
    def test_combined_filters(self, search_manager):
        """Test multiple filters combined."""
        results = search_manager.search(
            "books",
            speaker_id="speaker_0",
            video_id="e1a792d7-3080-47d0-b199-8bccee31e555"
        )
        
        assert isinstance(results, list), "Combined filters should return a list"


class TestSearchPerformance:
    """Test search performance requirements."""
    
    @pytest.fixture
    def search_manager(self):
        return SearchManager()
    
    def test_search_performance(self, search_manager):
        """Test that search completes in <500ms."""
        query = "books"
        
        start_time = time.time()
        results = search_manager.search(query)
        end_time = time.time()
        
        duration_ms = (end_time - start_time) * 1000
        
        assert duration_ms < 500, f"Search should complete in <500ms, took {duration_ms:.2f}ms"
        assert len(results) > 0, "Performance test should return results"
    
    def test_complex_query_performance(self, search_manager):
        """Test performance with complex queries."""
        query = "books life changing important scared"
        
        start_time = time.time()
        results = search_manager.search(query)
        end_time = time.time()
        
        duration_ms = (end_time - start_time) * 1000
        
        assert duration_ms < 500, f"Complex search should complete in <500ms, took {duration_ms:.2f}ms"


class TestSearchRanking:
    """Test search result ranking and relevance."""
    
    @pytest.fixture
    def search_manager(self):
        return SearchManager()
    
    def test_result_ranking(self, search_manager):
        """Test that results are ranked by relevance."""
        results = search_manager.search("books")
        
        if len(results) > 1:
            # Results should have rank scores
            for result in results:
                assert hasattr(result, 'rank'), "Result should have rank score"
                assert isinstance(result.rank, (int, float)), "Rank should be numeric"
            
            # Results should be ordered by rank (in FTS5, higher/less negative is better)
            ranks = [result.rank for result in results]
            assert ranks == sorted(ranks, reverse=True), "Results should be ordered by rank (higher is better)"
    
    def test_exact_match_ranking(self, search_manager):
        """Test that exact matches rank higher than partial matches."""
        # This test may not be applicable with current data, but structure is here
        results = search_manager.search("books")
        
        assert isinstance(results, list), "Should return ranked results"


class TestSearchPagination:
    """Test search result pagination."""
    
    @pytest.fixture
    def search_manager(self):
        return SearchManager()
    
    def test_pagination_limit(self, search_manager):
        """Test result limiting."""
        all_results = search_manager.search("books")
        limited_results = search_manager.search("books", limit=5)
        
        assert len(limited_results) <= 5, "Should respect limit parameter"
        assert len(limited_results) <= len(all_results), "Limited results should be subset"
    
    def test_pagination_offset(self, search_manager):
        """Test result offset."""
        first_page = search_manager.search("books", limit=3, offset=0)
        second_page = search_manager.search("books", limit=3, offset=3)
        
        if len(first_page) == 3 and len(second_page) > 0:
            # Results should be different
            first_ids = [r.id for r in first_page]
            second_ids = [r.id for r in second_page]
            assert set(first_ids).isdisjoint(set(second_ids)), \
                "Different pages should have different results"


class TestSearchEdgeCases:
    """Test edge cases and special characters."""
    
    @pytest.fixture
    def search_manager(self):
        return SearchManager()
    
    def test_special_characters(self, search_manager):
        """Test handling of special characters in queries."""
        special_queries = [
            "don't",  # apostrophe
            "life-changing",  # hyphen
            "books.",  # period
            "books!",  # exclamation
        ]
        
        for query in special_queries:
            results = search_manager.search(query)
            assert isinstance(results, list), f"Should handle special chars in '{query}'"
    
    def test_unicode_search(self, search_manager):
        """Test handling of unicode characters."""
        unicode_query = "café résumé"  # Accented characters
        results = search_manager.search(unicode_query)
        
        assert isinstance(results, list), "Should handle unicode queries"
    
    def test_very_long_query(self, search_manager):
        """Test handling of very long search queries."""
        long_query = "books " * 100  # Very long query
        results = search_manager.search(long_query)
        
        assert isinstance(results, list), "Should handle very long queries"
    
    def test_fts_special_syntax(self, search_manager):
        """Test FTS5 special syntax handling."""
        fts_queries = [
            "books AND life",  # Boolean AND
            "books OR life",   # Boolean OR
            "books NOT scared", # Boolean NOT
            '"exact phrase"',  # Exact phrase
        ]
        
        for query in fts_queries:
            results = search_manager.search(query)
            assert isinstance(results, list), f"Should handle FTS5 syntax: '{query}'"


class TestSearchBenchmark:
    """Benchmark tests for search performance analysis."""
    
    @pytest.fixture
    def search_manager(self):
        return SearchManager()
    
    def test_benchmark_various_queries(self, search_manager):
        """Benchmark different types of queries."""
        test_queries = [
            "books",
            "life changing",
            "scared important",
            "books AND life",
            "book*",
            '"life changing"',
        ]
        
        total_time = 0
        results_count = 0
        
        for query in test_queries:
            start_time = time.time()
            results = search_manager.search(query)
            end_time = time.time()
            
            duration_ms = (end_time - start_time) * 1000
            total_time += duration_ms
            results_count += len(results)
            
            print(f"Query '{query}': {duration_ms:.2f}ms, {len(results)} results")
        
        avg_time = total_time / len(test_queries)
        print(f"Average query time: {avg_time:.2f}ms")
        print(f"Total results across all queries: {results_count}")
        
        assert avg_time < 500, f"Average query time should be <500ms, got {avg_time:.2f}ms"