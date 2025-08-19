/**
 * Phase B: Knowledge Dashboard Tests
 * 
 * Test-Driven Development for Knowledge Dashboard features
 * Testing Ask Anything Interface, Insight Cards, and Activity Dashboard
 */

class PhaseBTester {
    constructor() {
        this.tests = [];
        this.passed = 0;
        this.failed = 0;
    }
    
    test(name, testFn) {
        this.tests.push({ name, testFn });
    }
    
    async run() {
        console.log('🧪 Running Phase B: Knowledge Dashboard Tests...\n');
        
        for (const { name, testFn } of this.tests) {
            try {
                await testFn();
                console.log(`✅ ${name}`);
                this.passed++;
            } catch (error) {
                console.error(`❌ ${name}: ${error.message}`);
                this.failed++;
            }
        }
        
        console.log(`\n📊 Phase B Test Results: ${this.passed} passed, ${this.failed} failed`);
        return this.failed === 0;
    }
    
    assert(condition, message) {
        if (!condition) {
            throw new Error(message || 'Assertion failed');
        }
    }
    
    assertEqual(actual, expected, message) {
        this.assert(actual === expected, message || `Expected ${expected}, got ${actual}`);
    }
    
    assertExists(value, message) {
        this.assert(value !== null && value !== undefined, message || 'Value should exist');
    }
    
    async wait(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

const phaseBTest = new PhaseBTester();

// Ask Anything Interface Tests
phaseBTest.test('askAnythingBar component exists and initializes', () => {
    phaseBTest.assert(typeof askAnythingBar === 'function', 'askAnythingBar should be a function');
    
    const component = askAnythingBar();
    phaseBTest.assertExists(component, 'Component should be created');
    phaseBTest.assertEqual(component.query, '', 'Query should start empty');
    phaseBTest.assertEqual(component.isLoading, false, 'Should not be loading initially');
    phaseBTest.assertEqual(component.searchType, 'question', 'Should default to question type');
});

phaseBTest.test('askAnythingBar handles search type toggle', () => {
    const component = askAnythingBar();
    
    component.setSearchType('search');
    phaseBTest.assertEqual(component.searchType, 'search', 'Should change to search type');
    
    component.setSearchType('browse');
    phaseBTest.assertEqual(component.searchType, 'browse', 'Should change to browse type');
    
    component.setSearchType('question');
    phaseBTest.assertEqual(component.searchType, 'question', 'Should change back to question type');
});

phaseBTest.test('askAnythingBar performs question asking', async () => {
    const component = askAnythingBar();
    
    // Mock API
    component.api = {
        ask: async (question) => ({
            question,
            answer: `Answer to: ${question}`,
            sources: [],
            confidence_score: 0.95,
            response_time_ms: 1500,
            session_id: 'test-session'
        })
    };
    
    component.query = 'What is the meaning of life?';
    await component.handleSubmit();
    
    phaseBTest.assertExists(component.lastResponse, 'Should have response');
    phaseBTest.assertEqual(component.lastResponse.answer, 'Answer to: What is the meaning of life?', 'Should get correct answer');
    phaseBTest.assertExists(component.lastResponse.session_id, 'Should have session ID');
});

phaseBTest.test('askAnythingBar handles suggestion chips', () => {
    const component = askAnythingBar();
    
    // Mock suggestions based on available content
    component.suggestions = [
        'What topics are discussed in my videos?',
        'Who are the main speakers?',
        'What books are mentioned?',
        'Show me recent summaries'
    ];
    
    phaseBTest.assertEqual(component.suggestions.length, 4, 'Should have 4 suggestion chips');
    
    component.selectSuggestion('What topics are discussed in my videos?');
    phaseBTest.assertEqual(component.query, 'What topics are discussed in my videos?', 'Should set query from suggestion');
});

phaseBTest.test('askAnythingBar shows typing indicator during response', async () => {
    const component = askAnythingBar();
    
    // Mock API with delay
    component.api = {
        ask: async (question) => {
            await component.wait(100);
            return { answer: 'Response', sources: [], confidence_score: 0.8 };
        }
    };
    
    component.query = 'test question';
    const submitPromise = component.handleSubmit();
    
    phaseBTest.assert(component.isLoading, 'Should show loading during request');
    
    await submitPromise;
    
    phaseBTest.assert(!component.isLoading, 'Should hide loading after response');
});

// Insight Cards System Tests
phaseBTest.test('recentSummariesCard component exists and loads data', async () => {
    phaseBTest.assert(typeof recentSummariesCard === 'function', 'recentSummariesCard should be a function');
    
    const component = recentSummariesCard();
    
    // Mock API
    component.api = {
        getSummaries: async () => ({
            summaries: [
                { id: 1, title: 'Video Summary 1', created_at: '2024-01-01T10:00:00Z' },
                { id: 2, title: 'Video Summary 2', created_at: '2024-01-02T10:00:00Z' }
            ],
            total_count: 2
        })
    };
    
    await component.loadData();
    
    phaseBTest.assertEqual(component.summaries.length, 2, 'Should load 2 summaries');
    phaseBTest.assertEqual(component.summaries[0].title, 'Video Summary 1', 'Should have correct title');
});

phaseBTest.test('topicTrendsCard component shows popular topics', async () => {
    phaseBTest.assert(typeof topicTrendsCard === 'function', 'topicTrendsCard should be a function');
    
    const component = topicTrendsCard();
    
    // Mock API
    component.api = {
        getTopicTrends: async () => ({
            topics: [
                { name: 'Productivity', frequency: 25, trend: 'up' },
                { name: 'Learning', frequency: 18, trend: 'stable' },
                { name: 'Technology', frequency: 15, trend: 'down' }
            ]
        })
    };
    
    await component.loadData();
    
    phaseBTest.assertEqual(component.topics.length, 3, 'Should load 3 trending topics');
    phaseBTest.assertEqual(component.topics[0].name, 'Productivity', 'Should have correct topic name');
    phaseBTest.assertEqual(component.topics[0].trend, 'up', 'Should show trend direction');
});

phaseBTest.test('entityHighlightsCard component displays key entities', async () => {
    phaseBTest.assert(typeof entityHighlightsCard === 'function', 'entityHighlightsCard should be a function');
    
    const component = entityHighlightsCard();
    
    // Mock API
    component.api = {
        getEntityHighlights: async () => ({
            entities: [
                { name: 'Tim Ferriss', type: 'person', mentions: 12 },
                { name: 'Atomic Habits', type: 'book', mentions: 8 },
                { name: 'Google', type: 'company', mentions: 6 }
            ]
        })
    };
    
    await component.loadData();
    
    phaseBTest.assertEqual(component.entities.length, 3, 'Should load 3 highlighted entities');
    phaseBTest.assertEqual(component.entities[0].type, 'person', 'Should categorize entity types');
    phaseBTest.assertEqual(component.entities[0].mentions, 12, 'Should show mention count');
});

phaseBTest.test('processingStatusCard component shows video processing status', async () => {
    phaseBTest.assert(typeof processingStatusCard === 'function', 'processingStatusCard should be a function');
    
    const component = processingStatusCard();
    
    // Mock API
    component.api = {
        getProcessingStatus: async () => ({
            queue_length: 2,
            in_progress: 1,
            completed_today: 5,
            failed_today: 0,
            current_job: {
                video_id: 'abc123',
                title: 'Learning JavaScript',
                stage: 'transcribing',
                progress: 65
            }
        })
    };
    
    await component.loadData();
    
    phaseBTest.assertEqual(component.status.queue_length, 2, 'Should show queue length');
    phaseBTest.assertEqual(component.status.current_job.stage, 'transcribing', 'Should show current processing stage');
    phaseBTest.assertEqual(component.status.current_job.progress, 65, 'Should show progress percentage');
});

phaseBTest.test('quickStatsCard component displays knowledge metrics', async () => {
    phaseBTest.assert(typeof quickStatsCard === 'function', 'quickStatsCard should be a function');
    
    const component = quickStatsCard();
    
    // Mock API
    component.api = {
        getKnowledgeStats: async () => ({
            total_videos: 42,
            total_hours: 125.5,
            entities_discovered: 387,
            topics_identified: 156,
            qa_sessions: 23
        })
    };
    
    await component.loadData();
    
    phaseBTest.assertEqual(component.stats.total_videos, 42, 'Should show total videos');
    phaseBTest.assertEqual(component.stats.total_hours, 125.5, 'Should show total hours');
    phaseBTest.assertEqual(component.stats.entities_discovered, 387, 'Should show entities count');
});

// Activity Dashboard Tests
phaseBTest.test('activityDashboard component tracks recent conversations', async () => {
    phaseBTest.assert(typeof activityDashboard === 'function', 'activityDashboard should be a function');
    
    const component = activityDashboard();
    
    // Mock API
    component.api = {
        getRecentQA: async () => ({
            conversations: [
                {
                    session_id: 'session1',
                    last_question: 'What is productivity?',
                    last_answer: 'Productivity is...',
                    timestamp: '2024-01-01T10:00:00Z',
                    exchange_count: 5
                }
            ]
        })
    };
    
    await component.loadRecentQA();
    
    phaseBTest.assertEqual(component.recentConversations.length, 1, 'Should load recent conversations');
    phaseBTest.assertEqual(component.recentConversations[0].exchange_count, 5, 'Should show exchange count');
});

phaseBTest.test('activityDashboard component shows latest processed videos', async () => {
    const component = activityDashboard();
    
    // Mock API
    component.api = {
        getRecentVideos: async () => ({
            videos: [
                {
                    id: 'vid1',
                    title: 'Latest Video',
                    processed_at: '2024-01-01T12:00:00Z',
                    entities_extracted: 15,
                    topics_assigned: 8
                }
            ]
        })
    };
    
    await component.loadRecentVideos();
    
    phaseBTest.assertEqual(component.recentVideos.length, 1, 'Should load recent videos');
    phaseBTest.assertEqual(component.recentVideos[0].entities_extracted, 15, 'Should show extraction metrics');
});

phaseBTest.test('activityDashboard component manages search history', () => {
    const component = activityDashboard();
    
    component.searchHistory = [
        { query: 'productivity tips', timestamp: '2024-01-01T10:00:00Z', results_count: 12 },
        { query: 'learning methods', timestamp: '2024-01-01T09:00:00Z', results_count: 8 }
    ];
    
    phaseBTest.assertEqual(component.searchHistory.length, 2, 'Should track search history');
    
    component.rerunSearch('productivity tips');
    phaseBTest.assertEqual(component.activeQuery, 'productivity tips', 'Should re-run previous search');
});

phaseBTest.test('activityDashboard component handles bookmarks', () => {
    const component = activityDashboard();
    
    component.addBookmark({
        type: 'video',
        id: 'vid123',
        title: 'Important Video',
        timestamp: 10000
    });
    
    phaseBTest.assertEqual(component.bookmarks.length, 1, 'Should add bookmark');
    phaseBTest.assertEqual(component.bookmarks[0].type, 'video', 'Should store bookmark type');
    
    component.removeBookmark('vid123');
    phaseBTest.assertEqual(component.bookmarks.length, 0, 'Should remove bookmark');
});

// Interactive Elements Tests
phaseBTest.test('dashboard auto-refresh system works', async () => {
    phaseBTest.assert(typeof dashboardAutoRefresh === 'function', 'dashboardAutoRefresh should be a function');
    
    const refresher = dashboardAutoRefresh();
    let refreshCount = 0;
    
    refresher.onRefresh = () => { refreshCount++; };
    refresher.interval = 100; // Fast interval for testing
    
    refresher.start();
    await refresher.wait(250);
    refresher.stop();
    
    phaseBTest.assert(refreshCount >= 2, 'Should have refreshed at least twice');
});

phaseBTest.test('drag-and-drop URL processing works', async () => {
    phaseBTest.assert(typeof dragDropProcessor === 'function', 'dragDropProcessor should be a function');
    
    const processor = dragDropProcessor();
    let processedUrl = null;
    
    processor.onProcess = (url) => { processedUrl = url; };
    
    // Simulate drop event
    const mockEvent = {
        preventDefault: () => {},
        dataTransfer: {
            getData: () => 'https://youtube.com/watch?v=abc123'
        }
    };
    
    await processor.handleDrop(mockEvent);
    
    phaseBTest.assertEqual(processedUrl, 'https://youtube.com/watch?v=abc123', 'Should process dropped URL');
});

phaseBTest.test('keyboard shortcuts for dashboard actions work', () => {
    phaseBTest.assert(typeof dashboardShortcuts === 'function', 'dashboardShortcuts should be a function');
    
    const shortcuts = dashboardShortcuts();
    let actionTriggered = null;
    
    shortcuts.onAction = (action) => { actionTriggered = action; };
    shortcuts.init();
    
    // Simulate keyboard shortcut
    const event = new KeyboardEvent('keydown', { key: 'n', ctrlKey: true });
    shortcuts.handleKeydown(event);
    
    phaseBTest.assertEqual(actionTriggered, 'new-question', 'Should trigger new question action');
});

phaseBTest.test('export functionality works for dashboard insights', async () => {
    phaseBTest.assert(typeof dashboardExporter === 'function', 'dashboardExporter should be a function');
    
    const exporter = dashboardExporter();
    
    const mockData = {
        insights: ['Insight 1', 'Insight 2'],
        stats: { videos: 10, entities: 50 },
        recentQA: [{ question: 'Test?', answer: 'Response' }]
    };
    
    const exported = await exporter.exportToJSON(mockData);
    
    phaseBTest.assertExists(exported, 'Should export data');
    phaseBTest.assert(exported.includes('Insight 1'), 'Should include insights in export');
});

// Integration Tests for Phase B
phaseBTest.test('dashboard integrates with existing navigation', () => {
    // Test that dashboard doesn't break existing navigation
    phaseBTest.assert(typeof searchBar === 'function', 'SearchBar should still be available');
    phaseBTest.assert(typeof modal === 'function', 'Modal should still be available');
    phaseBTest.assert(typeof darkModeToggle === 'function', 'Dark mode should still be available');
});

phaseBTest.test('dashboard components communicate through event system', async () => {
    let eventReceived = false;
    
    eventSystem.on('dashboard:refresh', () => {
        eventReceived = true;
    });
    
    eventSystem.emit('dashboard:refresh');
    await phaseBTest.wait(10);
    
    phaseBTest.assert(eventReceived, 'Dashboard components should communicate via events');
});

phaseBTest.test('dashboard maintains responsive design', () => {
    // Test that dashboard components work on different screen sizes
    const component = askAnythingBar();
    
    phaseBTest.assertExists(component.getResponsiveClasses, 'Components should handle responsive design');
    
    const mobileClasses = component.getResponsiveClasses('mobile');
    const desktopClasses = component.getResponsiveClasses('desktop');
    
    phaseBTest.assert(mobileClasses !== desktopClasses, 'Should have different classes for different screen sizes');
});

// Export for test runner
if (typeof window !== 'undefined') {
    window.phaseBTest = phaseBTest;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = phaseBTest;
}