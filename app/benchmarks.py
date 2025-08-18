"""
Performance benchmarking suite for YouTube Knowledgebank.

This module provides comprehensive performance benchmarks to ensure the application
meets performance requirements and can handle production workloads efficiently.

Usage:
    python -m app.benchmarks
"""
import time
import sys
import sqlite3
import psutil
import os
import json
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

# Import application modules
from app.database import init_database, get_database_session, DatabaseManager
from app.database_queries import (
    get_all_videos_from_database, get_task_result_from_database,
    save_video_to_database, get_database_stats
)
from app.search import SearchManager
from app.processor import get_all_videos_from_files, get_task_result_from_files, format_duration
from app.migration import MigrationManager


class PerformanceBenchmark:
    """Performance benchmarking suite for the application."""
    
    def __init__(self):
        """Initialize benchmark suite."""
        self.results = {}
        self.db_manager = None
        self.search_manager = None
        
        # Setup test data
        self.setup_test_data()
        
    def setup_test_data(self):
        """Setup test data for benchmarking."""
        # Sample video metadata for testing
        self.sample_videos = []
        for i in range(100):  # Create 100 test videos
            video_data = {
                "id": f"benchmark-video-{i:03d}",
                "title": f"Benchmark Test Video {i}: Performance Testing with Various Keywords",
                "duration": 1800 + (i * 30),  # Varying durations
                "uploader": f"Test Channel {i % 10}",
                "view_count": 50000 + (i * 1000),
                "upload_date": "20250817",
                "url": f"https://youtu.be/test{i:03d}",
                "video_id": f"test{i:03d}",
                "processed_date": datetime.now(timezone.utc).isoformat(),
                "audio_file_path": f"/app/data/videos/benchmark-video-{i:03d}/audio.webm"
            }
            
            # Sample transcript with varying content
            transcript_data = {
                "language_code": "eng",
                "language_probability": 0.95 + (i * 0.0001),
                "text": f"This is benchmark test transcript {i} discussing performance, optimization, and scalability. " * (i % 10 + 1),
                "words": []
            }
            
            # Create word-level transcript data
            base_text = f"This is benchmark test transcript {i} discussing performance optimization scalability"
            words = base_text.split()
            for j, word in enumerate(words):
                transcript_data["words"].append({
                    "speaker_id": f"speaker_{j % 3}",
                    "start_ms": j * 500,
                    "end_ms": (j + 1) * 500,
                    "text": word
                })
            
            self.sample_videos.append((video_data, transcript_data))
    
    def measure_time(self, func, *args, **kwargs):
        """Measure execution time of a function."""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result, (end_time - start_time) * 1000  # Return time in milliseconds
    
    async def measure_time_async(self, func, *args, **kwargs):
        """Measure execution time of an async function."""
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        return result, (end_time - start_time) * 1000  # Return time in milliseconds
    
    def get_memory_usage(self):
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024  # Convert bytes to MB
    
    def benchmark_database_operations(self):
        """Benchmark database operations performance."""
        print("🔧 Running Database Operations Benchmarks...")
        
        # Initialize database
        try:
            self.db_manager = init_database()
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            return {"error": "Database initialization failed"}
        
        results = {}
        
        # Benchmark: Database Initialization
        _, init_time = self.measure_time(init_database)
        results["database_init_ms"] = init_time
        
        # Benchmark: Video Insertion (Batch)
        print("  📝 Testing batch video insertion...")
        start_memory = self.get_memory_usage()
        start_time = time.time()
        
        successful_inserts = 0
        failed_inserts = 0
        
        for video_data, transcript_data in self.sample_videos:
            try:
                success = save_video_to_database(video_data, transcript_data)
                if success:
                    successful_inserts += 1
                else:
                    failed_inserts += 1
            except Exception as e:
                failed_inserts += 1
                print(f"    ⚠️  Insert failed for {video_data['id']}: {e}")
        
        insert_time = (time.time() - start_time) * 1000
        insert_memory = self.get_memory_usage() - start_memory
        
        results["batch_insert_ms"] = insert_time
        results["batch_insert_memory_mb"] = insert_memory
        results["successful_inserts"] = successful_inserts
        results["failed_inserts"] = failed_inserts
        results["insert_rate_per_second"] = successful_inserts / (insert_time / 1000) if insert_time > 0 else 0
        
        # Benchmark: Get All Videos
        print("  📋 Testing get all videos performance...")
        _, get_all_time = self.measure_time(get_all_videos_from_database)
        results["get_all_videos_ms"] = get_all_time
        
        # Benchmark: Single Video Retrieval
        print("  🎯 Testing single video retrieval...")
        test_video_id = "benchmark-video-050"
        _, get_single_time = self.measure_time(get_task_result_from_database, test_video_id)
        results["get_single_video_ms"] = get_single_time
        
        # Benchmark: Database Stats
        print("  📊 Testing database statistics...")
        _, stats_time = self.measure_time(get_database_stats)
        results["get_stats_ms"] = stats_time
        
        # Benchmark: Connection Pool Performance
        print("  🔗 Testing database connection performance...")
        connection_times = []
        for i in range(10):
            try:
                _, conn_time = self.measure_time(get_database_session)
                connection_times.append(conn_time)
            except Exception:
                pass
        
        if connection_times:
            results["avg_connection_time_ms"] = sum(connection_times) / len(connection_times)
            results["max_connection_time_ms"] = max(connection_times)
            results["min_connection_time_ms"] = min(connection_times)
        
        return results
    
    def benchmark_search_performance(self):
        """Benchmark search operations performance."""
        print("🔍 Running Search Performance Benchmarks...")
        
        try:
            self.search_manager = SearchManager()
        except Exception as e:
            print(f"❌ Search manager initialization failed: {e}")
            return {"error": "Search manager initialization failed"}
        
        results = {}
        
        # Test queries of varying complexity
        test_queries = [
            "performance",
            "benchmark test",
            "optimization scalability performance",
            "test video performance optimization benchmark scalability",
            "a very long query with many terms that should test the full text search capabilities"
        ]
        
        for i, query in enumerate(test_queries):
            print(f"  🔎 Testing query {i+1}: '{query[:30]}{'...' if len(query) > 30 else ''}'")
            
            try:
                # Test different result set sizes
                for limit in [10, 50, 100]:
                    start_time = time.time()
                    search_result = self.search_manager.search(
                        query=query,
                        limit=limit,
                        offset=0
                    )
                    search_time = (time.time() - start_time) * 1000
                    
                    key = f"search_query_{i+1}_limit_{limit}_ms"
                    results[key] = search_time
                    results[f"search_query_{i+1}_limit_{limit}_results"] = search_result.get("total_found", 0)
                    
            except Exception as e:
                print(f"    ⚠️  Search failed for query '{query}': {e}")
                results[f"search_query_{i+1}_error"] = str(e)
        
        # Test search with filters
        print("  🎯 Testing filtered searches...")
        try:
            filtered_queries = [
                {"query": "performance", "video_id": "benchmark-video-025"},
                {"query": "optimization", "speaker_id": "speaker_0"},
                {"query": "benchmark", "video_id": "benchmark-video-050", "speaker_id": "speaker_1"}
            ]
            
            for j, query_params in enumerate(filtered_queries):
                start_time = time.time()
                search_result = self.search_manager.search(**query_params, limit=10, offset=0)
                search_time = (time.time() - start_time) * 1000
                
                results[f"filtered_search_{j+1}_ms"] = search_time
                results[f"filtered_search_{j+1}_results"] = search_result.get("total_found", 0)
                
        except Exception as e:
            print(f"    ⚠️  Filtered search failed: {e}")
            results["filtered_search_error"] = str(e)
        
        return results
    
    def benchmark_file_vs_database_performance(self):
        """Compare file-based vs database performance."""
        print("⚖️  Running File vs Database Performance Comparison...")
        
        results = {}
        
        # Create test JSON files for comparison
        test_data_dir = Path("/app/data/videos")
        test_data_dir.mkdir(exist_ok=True)
        
        # Create a subset of test videos as JSON files
        print("  📄 Setting up test JSON files...")
        test_video_ids = []
        for i in range(10):  # Create 10 test JSON files
            video_id = f"file-test-video-{i:03d}"
            video_dir = test_data_dir / video_id
            video_dir.mkdir(exist_ok=True)
            
            metadata = {
                "task_id": video_id,
                "title": f"File Test Video {i}",
                "duration": 1800,
                "uploader": "File Test Channel",
                "processed_date": datetime.now(timezone.utc).isoformat()
            }
            
            transcript = {
                "text": f"This is file test transcript {i}",
                "words": [
                    {"speaker_id": "speaker_0", "text": f"test {j}", "start_ms": j*1000, "end_ms": (j+1)*1000}
                    for j in range(10)
                ]
            }
            
            # Save JSON files
            with open(video_dir / "metadata.json", "w") as f:
                json.dump(metadata, f)
            with open(video_dir / "transcript.json", "w") as f:
                json.dump(transcript, f)
            
            test_video_ids.append(video_id)
        
        # Benchmark file-based operations
        print("  📁 Testing file-based operations...")
        _, file_get_all_time = self.measure_time(get_all_videos_from_files)
        results["file_get_all_videos_ms"] = file_get_all_time
        
        _, file_get_single_time = self.measure_time(get_task_result_from_files, test_video_ids[0])
        results["file_get_single_video_ms"] = file_get_single_time
        
        # Benchmark database operations for comparison
        print("  🗄️  Testing database operations...")
        _, db_get_all_time = self.measure_time(get_all_videos_from_database)
        results["db_get_all_videos_ms"] = db_get_all_time
        
        if test_video_ids:
            db_test_id = "benchmark-video-050"  # Use existing database video
            _, db_get_single_time = self.measure_time(get_task_result_from_database, db_test_id)
            results["db_get_single_video_ms"] = db_get_single_time
        
        # Calculate performance ratios
        if file_get_all_time > 0 and db_get_all_time > 0:
            results["get_all_speedup_ratio"] = file_get_all_time / db_get_all_time
        
        if file_get_single_time > 0 and db_get_single_time > 0:
            results["get_single_speedup_ratio"] = file_get_single_time / db_get_single_time
        
        # Cleanup test files
        print("  🧹 Cleaning up test files...")
        try:
            for video_id in test_video_ids:
                video_dir = test_data_dir / video_id
                if video_dir.exists():
                    for file in video_dir.glob("*"):
                        file.unlink()
                    video_dir.rmdir()
        except Exception as e:
            print(f"    ⚠️  Cleanup warning: {e}")
        
        return results
    
    def benchmark_memory_usage(self):
        """Benchmark memory usage patterns."""
        print("🧠 Running Memory Usage Benchmarks...")
        
        results = {}
        
        # Baseline memory
        baseline_memory = self.get_memory_usage()
        results["baseline_memory_mb"] = baseline_memory
        
        # Memory usage during database operations
        memory_samples = []
        
        print("  📊 Monitoring memory during operations...")
        for i in range(5):
            try:
                # Perform various operations and monitor memory
                get_all_videos_from_database()
                memory_samples.append(self.get_memory_usage())
                
                if i < 3:  # Don't exceed sample data
                    get_task_result_from_database(f"benchmark-video-{i:03d}")
                    memory_samples.append(self.get_memory_usage())
                
                time.sleep(0.1)  # Brief pause between operations
            except Exception:
                pass
        
        if memory_samples:
            results["avg_operation_memory_mb"] = sum(memory_samples) / len(memory_samples)
            results["peak_memory_mb"] = max(memory_samples)
            results["memory_variance_mb"] = max(memory_samples) - min(memory_samples)
        
        # Test memory growth over repeated operations
        print("  🔄 Testing memory growth over repeated operations...")
        initial_memory = self.get_memory_usage()
        
        for i in range(20):
            try:
                get_all_videos_from_database()
            except Exception:
                pass
        
        final_memory = self.get_memory_usage()
        results["memory_growth_mb"] = final_memory - initial_memory
        results["memory_growth_per_operation_mb"] = (final_memory - initial_memory) / 20
        
        return results
    
    def benchmark_concurrent_operations(self):
        """Benchmark concurrent operation performance."""
        print("🔀 Running Concurrent Operations Benchmarks...")
        
        results = {}
        
        async def concurrent_database_reads():
            """Perform concurrent database read operations."""
            tasks = []
            for i in range(10):  # 10 concurrent reads
                async def read_operation():
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, get_all_videos_from_database)
                tasks.append(read_operation())
            
            start_time = time.time()
            try:
                await asyncio.gather(*tasks)
                return (time.time() - start_time) * 1000
            except Exception as e:
                print(f"    ⚠️  Concurrent read failed: {e}")
                return None
        
        async def concurrent_search_operations():
            """Perform concurrent search operations."""
            search_queries = ["performance", "optimization", "benchmark", "test", "video"]
            tasks = []
            
            for query in search_queries:
                async def search_operation(q=query):
                    loop = asyncio.get_event_loop()
                    search_manager = SearchManager()
                    return await loop.run_in_executor(
                        None, 
                        lambda: search_manager.search(query=q, limit=10, offset=0)
                    )
                tasks.append(search_operation())
            
            start_time = time.time()
            try:
                await asyncio.gather(*tasks)
                return (time.time() - start_time) * 1000
            except Exception as e:
                print(f"    ⚠️  Concurrent search failed: {e}")
                return None
        
        # Run concurrent benchmarks
        print("  📚 Testing concurrent database reads...")
        try:
            concurrent_read_time = asyncio.run(concurrent_database_reads())
            if concurrent_read_time:
                results["concurrent_reads_ms"] = concurrent_read_time
        except Exception as e:
            print(f"    ❌ Concurrent read test failed: {e}")
        
        print("  🔍 Testing concurrent searches...")
        try:
            concurrent_search_time = asyncio.run(concurrent_search_operations())
            if concurrent_search_time:
                results["concurrent_searches_ms"] = concurrent_search_time
        except Exception as e:
            print(f"    ❌ Concurrent search test failed: {e}")
        
        return results
    
    def run_all_benchmarks(self):
        """Run all performance benchmarks."""
        print("🚀 Starting YouTube Knowledgebank Performance Benchmarks")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run individual benchmark suites
        self.results["database_operations"] = self.benchmark_database_operations()
        self.results["search_performance"] = self.benchmark_search_performance()
        self.results["file_vs_database"] = self.benchmark_file_vs_database_performance()
        self.results["memory_usage"] = self.benchmark_memory_usage()
        self.results["concurrent_operations"] = self.benchmark_concurrent_operations()
        
        # Calculate total benchmark time
        total_time = time.time() - start_time
        self.results["total_benchmark_time_seconds"] = total_time
        
        print("\n" + "=" * 60)
        print("✅ All benchmarks completed!")
        return self.results
    
    def generate_report(self) -> str:
        """Generate a comprehensive performance report."""
        if not self.results:
            return "No benchmark results available. Run benchmarks first."
        
        report = []
        report.append("📊 YOUTUBE KNOWLEDGEBANK PERFORMANCE REPORT")
        report.append("=" * 50)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total benchmark time: {self.results.get('total_benchmark_time_seconds', 0):.2f} seconds")
        report.append("")
        
        # Database Operations Report
        db_results = self.results.get("database_operations", {})
        if db_results and "error" not in db_results:
            report.append("🗄️  DATABASE OPERATIONS PERFORMANCE")
            report.append("-" * 30)
            report.append(f"Database initialization: {db_results.get('database_init_ms', 0):.2f}ms")
            report.append(f"Batch insert (100 videos): {db_results.get('batch_insert_ms', 0):.2f}ms")
            report.append(f"Insert rate: {db_results.get('insert_rate_per_second', 0):.2f} videos/second")
            report.append(f"Memory usage during insert: {db_results.get('batch_insert_memory_mb', 0):.2f}MB")
            report.append(f"Get all videos: {db_results.get('get_all_videos_ms', 0):.2f}ms")
            report.append(f"Get single video: {db_results.get('get_single_video_ms', 0):.2f}ms")
            report.append(f"Database statistics: {db_results.get('get_stats_ms', 0):.2f}ms")
            report.append(f"Avg connection time: {db_results.get('avg_connection_time_ms', 0):.2f}ms")
            report.append("")
        
        # Search Performance Report
        search_results = self.results.get("search_performance", {})
        if search_results and "error" not in search_results:
            report.append("🔍 SEARCH PERFORMANCE")
            report.append("-" * 20)
            
            # Find search query results
            for key, value in search_results.items():
                if key.endswith("_ms") and "query" in key:
                    report.append(f"{key}: {value:.2f}ms")
            report.append("")
        
        # File vs Database Comparison
        comparison_results = self.results.get("file_vs_database", {})
        if comparison_results:
            report.append("⚖️  FILE vs DATABASE PERFORMANCE")
            report.append("-" * 30)
            report.append(f"File-based get all: {comparison_results.get('file_get_all_videos_ms', 0):.2f}ms")
            report.append(f"Database get all: {comparison_results.get('db_get_all_videos_ms', 0):.2f}ms")
            report.append(f"Get all speedup: {comparison_results.get('get_all_speedup_ratio', 0):.2f}x")
            report.append(f"File-based get single: {comparison_results.get('file_get_single_video_ms', 0):.2f}ms")
            report.append(f"Database get single: {comparison_results.get('db_get_single_video_ms', 0):.2f}ms")
            report.append(f"Get single speedup: {comparison_results.get('get_single_speedup_ratio', 0):.2f}x")
            report.append("")
        
        # Memory Usage Report
        memory_results = self.results.get("memory_usage", {})
        if memory_results:
            report.append("🧠 MEMORY USAGE")
            report.append("-" * 15)
            report.append(f"Baseline memory: {memory_results.get('baseline_memory_mb', 0):.2f}MB")
            report.append(f"Peak memory: {memory_results.get('peak_memory_mb', 0):.2f}MB")
            report.append(f"Memory growth (20 ops): {memory_results.get('memory_growth_mb', 0):.2f}MB")
            report.append(f"Memory per operation: {memory_results.get('memory_growth_per_operation_mb', 0):.3f}MB")
            report.append("")
        
        # Concurrent Operations Report
        concurrent_results = self.results.get("concurrent_operations", {})
        if concurrent_results:
            report.append("🔀 CONCURRENT OPERATIONS")
            report.append("-" * 25)
            report.append(f"10 concurrent reads: {concurrent_results.get('concurrent_reads_ms', 0):.2f}ms")
            report.append(f"5 concurrent searches: {concurrent_results.get('concurrent_searches_ms', 0):.2f}ms")
            report.append("")
        
        # Performance Requirements Validation
        report.append("✅ PERFORMANCE REQUIREMENTS VALIDATION")
        report.append("-" * 40)
        
        # Check search requirement (<500ms)
        search_time = search_results.get("search_query_1_limit_10_ms", float('inf'))
        search_status = "✅ PASS" if search_time < 500 else "❌ FAIL"
        report.append(f"Search < 500ms requirement: {search_status} ({search_time:.2f}ms)")
        
        # Check database response time
        get_all_time = db_results.get("get_all_videos_ms", float('inf'))
        db_status = "✅ PASS" if get_all_time < 1000 else "❌ FAIL"
        report.append(f"Database response < 1000ms: {db_status} ({get_all_time:.2f}ms)")
        
        # Check memory efficiency
        memory_growth = memory_results.get("memory_growth_per_operation_mb", float('inf'))
        memory_status = "✅ PASS" if memory_growth < 1.0 else "❌ FAIL"
        report.append(f"Memory growth < 1MB/op: {memory_status} ({memory_growth:.3f}MB)")
        
        return "\n".join(report)
    
    def save_results(self, filepath: str = "/app/data/performance_results.json"):
        """Save benchmark results to JSON file."""
        try:
            # Add timestamp and system info to results
            self.results["timestamp"] = datetime.now().isoformat()
            self.results["system_info"] = {
                "python_version": sys.version,
                "platform": sys.platform,
                "cpu_count": os.cpu_count(),
                "memory_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024
            }
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, "w") as f:
                json.dump(self.results, f, indent=2, default=str)
            
            print(f"📄 Results saved to: {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to save results: {e}")
            return False


def main():
    """Main entry point for benchmark suite."""
    print("🎯 YouTube Knowledgebank Performance Benchmarks")
    print("This may take several minutes to complete...\n")
    
    # Create benchmark instance
    benchmark = PerformanceBenchmark()
    
    try:
        # Run all benchmarks
        results = benchmark.run_all_benchmarks()
        
        # Generate and display report
        report = benchmark.generate_report()
        print("\n" + report)
        
        # Save results
        benchmark.save_results()
        
        return 0
        
    except Exception as e:
        print(f"❌ Benchmark suite failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())