/**
 * Test Suite for KnowledgeAPI Client
 * 
 * Tests all API client functionality with comprehensive error handling,
 * retry logic, and loading state management.
 */

// Simple test framework
class TestFramework {
    constructor() {
        this.tests = [];
        this.passed = 0;
        this.failed = 0;
    }
    
    test(name, testFn) {
        this.tests.push({ name, testFn });
    }
    
    async run() {
        console.log('🧪 Running KnowledgeAPI Tests...\n');
        
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
        
        console.log(`\n📊 Test Results: ${this.passed} passed, ${this.failed} failed`);
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
    
    assertThrows(fn, message) {
        let threw = false;
        try {
            fn();
        } catch (e) {
            threw = true;
        }
        this.assert(threw, message || 'Expected function to throw');
    }
}

// Global test framework instance
const test = new TestFramework();

// Mock fetch for testing
class MockFetch {
    constructor() {
        this.responses = new Map();
        this.requests = [];
        this.networkDelay = 0;
        this.shouldFail = false;
        this.failureCount = 0;
    }
    
    setResponse(url, response) {
        this.responses.set(url, response);
    }
    
    setNetworkDelay(ms) {
        this.networkDelay = ms;
    }
    
    setShouldFail(shouldFail, count = 1) {
        this.shouldFail = shouldFail;
        this.failureCount = count;
    }
    
    async fetch(url, options) {
        this.requests.push({ url, options });
        
        // Simulate network delay
        if (this.networkDelay > 0) {
            await new Promise(resolve => setTimeout(resolve, this.networkDelay));
        }
        
        // Simulate network failure
        if (this.shouldFail && this.failureCount > 0) {
            this.failureCount--;
            throw new Error('Network error');
        }
        
        const response = this.responses.get(url) || { status: 404, json: async () => ({ error: 'Not found' }) };
        return {
            ok: response.status >= 200 && response.status < 300,
            status: response.status,
            json: async () => response.json
        };
    }
    
    getRequests() {
        return this.requests;
    }
    
    reset() {
        this.requests = [];
        this.responses.clear();
        this.shouldFail = false;
        this.failureCount = 0;
        this.networkDelay = 0;
    }
}

const mockFetch = new MockFetch();

// Test KnowledgeAPI class existence and initialization
test.test('KnowledgeAPI class can be instantiated', () => {
    test.assert(typeof KnowledgeAPI === 'function', 'KnowledgeAPI should be a constructor function');
    
    const api = new KnowledgeAPI();
    test.assert(api instanceof KnowledgeAPI, 'Should create KnowledgeAPI instance');
    test.assertEqual(api.baseURL, '', 'Should have empty baseURL by default');
    test.assert(api.loadingStates instanceof Map, 'Should have loadingStates Map');
});

// Test initialization with custom base URL
test.test('KnowledgeAPI accepts custom base URL', () => {
    const api = new KnowledgeAPI('http://localhost:8765');
    test.assertEqual(api.baseURL, 'http://localhost:8765', 'Should accept custom baseURL');
});

// Test search functionality
test.test('search method handles successful response', async () => {
    const api = new KnowledgeAPI();
    api.fetch = mockFetch.fetch.bind(mockFetch);
    
    const mockResponse = {
        status: 200,
        json: {
            query: 'test query',
            results: [],
            total_found: 0,
            has_more: false,
            query_time_ms: 1.5
        }
    };
    
    mockFetch.setResponse('/api/search?query=test+query&limit=50&offset=0', mockResponse);
    
    const result = await api.search('test query');
    test.assertEqual(result.query, 'test query', 'Should return search results');
    
    mockFetch.reset();
});

// Test search with advanced options
test.test('search method handles advanced options', async () => {
    const api = new KnowledgeAPI();
    api.fetch = mockFetch.fetch.bind(mockFetch);
    
    const options = {
        video_id: '123',
        speaker_id: 'speaker1',
        start_date: '2024-01-01T00:00:00Z',
        end_date: '2024-12-31T23:59:59Z',
        limit: 25,
        offset: 10
    };
    
    const expectedUrl = '/api/search?query=test&video_id=123&speaker_id=speaker1&start_date=2024-01-01T00%3A00%3A00Z&end_date=2024-12-31T23%3A59%3A59Z&limit=25&offset=10';
    
    mockFetch.setResponse(expectedUrl, {
        status: 200,
        json: { query: 'test', results: [], total_found: 0, has_more: false, query_time_ms: 1.0 }
    });
    
    await api.search('test', options);
    
    const requests = mockFetch.getRequests();
    test.assertEqual(requests.length, 1, 'Should make one request');
    test.assert(requests[0].url.includes('video_id=123'), 'Should include video_id in URL');
    
    mockFetch.reset();
});

// Test ask functionality
test.test('ask method handles successful response', async () => {
    const api = new KnowledgeAPI();
    api.fetch = mockFetch.fetch.bind(mockFetch);
    
    const mockResponse = {
        status: 200,
        json: {
            question: 'What is the meaning of life?',
            answer: '42',
            sources: [],
            confidence_score: 0.95,
            response_time_ms: 1500,
            session_id: 'session123'
        }
    };
    
    mockFetch.setResponse('/api/ask', mockResponse);
    
    const result = await api.ask('What is the meaning of life?');
    test.assertEqual(result.answer, '42', 'Should return AI-generated answer');
    test.assertEqual(result.session_id, 'session123', 'Should return session ID');
    
    mockFetch.reset();
});

// Test ask with session ID
test.test('ask method handles session ID parameter', async () => {
    const api = new KnowledgeAPI();
    api.fetch = mockFetch.fetch.bind(mockFetch);
    
    mockFetch.setResponse('/api/ask', {
        status: 200,
        json: { question: 'test', answer: 'response', sources: [], confidence_score: 0.8, response_time_ms: 1000, session_id: 'existing123' }
    });
    
    await api.ask('test question', 'existing123');
    
    const requests = mockFetch.getRequests();
    test.assertEqual(requests.length, 1, 'Should make one request');
    test.assertEqual(requests[0].options.method, 'POST', 'Should use POST method');
    
    const body = JSON.parse(requests[0].options.body);
    test.assertEqual(body.session_id, 'existing123', 'Should include session_id in request body');
    
    mockFetch.reset();
});

// Test QA history
test.test('getQAHistory method handles successful response', async () => {
    const api = new KnowledgeAPI();
    api.fetch = mockFetch.fetch.bind(mockFetch);
    
    const mockResponse = {
        status: 200,
        json: {
            session_id: 'session123',
            exchanges: [],
            total_count: 0,
            has_more: false
        }
    };
    
    mockFetch.setResponse('/api/qa/history?session_id=session123&limit=20&offset=0', mockResponse);
    
    const result = await api.getQAHistory('session123');
    test.assertEqual(result.session_id, 'session123', 'Should return history for session');
    
    mockFetch.reset();
});

// Test QA sessions
test.test('getQASessions method handles successful response', async () => {
    const api = new KnowledgeAPI();
    api.fetch = mockFetch.fetch.bind(mockFetch);
    
    const mockResponse = {
        status: 200,
        json: {
            sessions: [],
            total_count: 0
        }
    };
    
    mockFetch.setResponse('/api/qa/sessions?limit=20&offset=0', mockResponse);
    
    const result = await api.getQASessions();
    test.assertEqual(result.total_count, 0, 'Should return sessions list');
    
    mockFetch.reset();
});

// Test error handling
test.test('API methods handle network errors', async () => {
    const api = new KnowledgeAPI();
    api.fetch = mockFetch.fetch.bind(mockFetch);
    
    mockFetch.setShouldFail(true);
    
    try {
        await api.search('test');
        test.assert(false, 'Should have thrown an error');
    } catch (error) {
        test.assert(error.message.includes('Network error'), 'Should throw network error');
    }
    
    mockFetch.reset();
});

// Test retry logic
test.test('API methods retry on failure', async () => {
    const api = new KnowledgeAPI();
    api.fetch = mockFetch.fetch.bind(mockFetch);
    
    // Fail first 2 attempts, succeed on 3rd
    mockFetch.setShouldFail(true, 2);
    mockFetch.setResponse('/api/search?query=test&limit=50&offset=0', {
        status: 200,
        json: { query: 'test', results: [], total_found: 0, has_more: false, query_time_ms: 1.0 }
    });
    
    const result = await api.search('test');
    test.assertEqual(result.query, 'test', 'Should succeed after retries');
    
    const requests = mockFetch.getRequests();
    test.assertEqual(requests.length, 3, 'Should make 3 attempts (1 initial + 2 retries)');
    
    mockFetch.reset();
});

// Test loading state management
test.test('API methods manage loading states', async () => {
    const api = new KnowledgeAPI();
    api.fetch = mockFetch.fetch.bind(mockFetch);
    
    mockFetch.setNetworkDelay(100); // Add delay to test loading state
    mockFetch.setResponse('/api/search?query=test&limit=50&offset=0', {
        status: 200,
        json: { query: 'test', results: [], total_found: 0, has_more: false, query_time_ms: 1.0 }
    });
    
    // Start search but don't await yet
    const searchPromise = api.search('test');
    
    // Check loading state is set
    test.assert(api.isLoading('search'), 'Should indicate loading state');
    
    // Wait for completion
    await searchPromise;
    
    // Check loading state is cleared
    test.assert(!api.isLoading('search'), 'Should clear loading state after completion');
    
    mockFetch.reset();
});

// Test HTTP error handling
test.test('API methods handle HTTP errors properly', async () => {
    const api = new KnowledgeAPI();
    api.fetch = mockFetch.fetch.bind(mockFetch);
    
    mockFetch.setResponse('/api/search?query=test&limit=50&offset=0', {
        status: 500,
        json: { error: 'Internal server error' }
    });
    
    try {
        await api.search('test');
        test.assert(false, 'Should have thrown an error');
    } catch (error) {
        test.assert(error.message.includes('500'), 'Should include status code in error');
    }
    
    mockFetch.reset();
});

// Test submission of feedback
test.test('submitFeedback method handles successful response', async () => {
    const api = new KnowledgeAPI();
    api.fetch = mockFetch.fetch.bind(mockFetch);
    
    mockFetch.setResponse('/api/qa/feedback', {
        status: 200,
        json: {
            success: true,
            feedback_id: 'feedback123',
            message: 'Feedback submitted successfully'
        }
    });
    
    const result = await api.submitFeedback('exchange123', 5, 'Great answer!');
    test.assertEqual(result.success, true, 'Should submit feedback successfully');
    test.assertEqual(result.feedback_id, 'feedback123', 'Should return feedback ID');
    
    mockFetch.reset();
});

// Run all tests when the page loads
if (typeof window !== 'undefined') {
    window.addEventListener('load', async () => {
        try {
            await test.run();
        } catch (error) {
            console.error('Test runner failed:', error);
        }
    });
}

// Export for Node.js if available
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { test, mockFetch };
}