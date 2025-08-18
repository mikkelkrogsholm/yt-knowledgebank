/**
 * Integration Tests
 * 
 * End-to-end tests for complete functionality and component interactions
 */

class IntegrationTester {
    constructor() {
        this.tests = [];
        this.passed = 0;
        this.failed = 0;
    }
    
    test(name, testFn) {
        this.tests.push({ name, testFn });
    }
    
    async run() {
        console.log('🧪 Running Integration Tests...\n');
        
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
        
        console.log(`\n📊 Integration Test Results: ${this.passed} passed, ${this.failed} failed`);
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
    
    assertType(value, expectedType, message) {
        this.assert(typeof value === expectedType, message || `Expected type ${expectedType}, got ${typeof value}`);
    }
    
    assertExists(value, message) {
        this.assert(value !== null && value !== undefined, message || 'Value should exist');
    }
    
    async wait(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

const integrationTest = new IntegrationTester();

// Test framework initialization
integrationTest.test('All core dependencies are loaded', () => {
    integrationTest.assertExists(window.Alpine, 'Alpine.js should be loaded');
    integrationTest.assertExists(window.KnowledgeAPI, 'KnowledgeAPI should be loaded');
    integrationTest.assertExists(window.EventSystem, 'EventSystem should be loaded');
    integrationTest.assertExists(window.DarkModeManager, 'DarkModeManager should be loaded');
    integrationTest.assertExists(window.eventSystem, 'Global eventSystem should be initialized');
    integrationTest.assertExists(window.globalDarkMode, 'Global dark mode should be initialized');
});

integrationTest.test('CSS files are properly loaded', () => {
    const links = Array.from(document.querySelectorAll('link[rel="stylesheet"]'));
    const hasComponentCSS = links.some(link => link.href.includes('components.css'));
    const hasIconCSS = links.some(link => link.href.includes('icons.css'));
    
    integrationTest.assert(hasComponentCSS, 'components.css should be loaded');
    integrationTest.assert(hasIconCSS, 'icons.css should be loaded');
});

integrationTest.test('JavaScript files are properly loaded', () => {
    const scripts = Array.from(document.querySelectorAll('script[src]'));
    const requiredScripts = [
        'event-system.js',
        'knowledge-api.js',
        'dark-mode.js'
    ];
    
    requiredScripts.forEach(scriptName => {
        const hasScript = scripts.some(script => script.src.includes(scriptName));
        integrationTest.assert(hasScript, `${scriptName} should be loaded`);
    });
});

// Test event system integration
integrationTest.test('Event system handles global events', async () => {
    let eventReceived = false;
    let eventData = null;
    
    const unsubscribe = eventSystem.on('integration-test-event', (data) => {
        eventReceived = true;
        eventData = data;
    });
    
    const testData = { message: 'test integration' };
    eventSystem.emit('integration-test-event', testData);
    
    // Give event time to propagate
    await integrationTest.wait(10);
    
    integrationTest.assert(eventReceived, 'Event should be received');
    integrationTest.assertEqual(eventData.message, 'test integration', 'Event data should be preserved');
    
    unsubscribe();
});

integrationTest.test('Event system handles keyboard shortcuts', async () => {
    let shortcutTriggered = false;
    
    eventSystem.registerShortcut('ctrl+t', () => {
        shortcutTriggered = true;
    });
    
    // Simulate keyboard event
    const event = new KeyboardEvent('keydown', {
        key: 't',
        ctrlKey: true,
        bubbles: true
    });
    
    document.dispatchEvent(event);
    
    // Give event time to process
    await integrationTest.wait(10);
    
    integrationTest.assert(shortcutTriggered, 'Keyboard shortcut should be triggered');
});

// Test KnowledgeAPI integration
integrationTest.test('KnowledgeAPI can be instantiated and configured', () => {
    const api = new KnowledgeAPI('http://test.local');
    
    integrationTest.assertEqual(api.baseURL, 'http://test.local', 'Base URL should be set');
    integrationTest.assertExists(api.loadingStates, 'Loading states should be initialized');
    integrationTest.assertType(api.search, 'function', 'search method should exist');
    integrationTest.assertType(api.ask, 'function', 'ask method should exist');
});

integrationTest.test('KnowledgeAPI loading states work correctly', async () => {
    const api = new KnowledgeAPI();
    
    // Mock fetch to control timing
    api.fetch = async () => {
        await integrationTest.wait(100);
        return {
            ok: true,
            json: async () => ({ results: [], total_found: 0 })
        };
    };
    
    integrationTest.assert(!api.isLoading('search'), 'Should not be loading initially');
    
    const searchPromise = api.search('test');
    integrationTest.assert(api.isLoading('search'), 'Should be loading during request');
    
    await searchPromise;
    integrationTest.assert(!api.isLoading('search'), 'Should not be loading after request');
});

// Test dark mode integration
integrationTest.test('Dark mode manager integrates with DOM', () => {
    const darkMode = new DarkModeManager();
    
    // Test light mode
    darkMode.setTheme('light');
    integrationTest.assert(!document.documentElement.classList.contains('dark'), 'Light mode should remove dark class');
    
    // Test dark mode
    darkMode.setTheme('dark');
    integrationTest.assert(document.documentElement.classList.contains('dark'), 'Dark mode should add dark class');
    
    // Reset to light for other tests
    darkMode.setTheme('light');
});

integrationTest.test('Dark mode persists preferences', () => {
    const darkMode = new DarkModeManager();
    
    // Set dark mode
    darkMode.setTheme('dark');
    
    // Create new instance (should load from localStorage)
    const darkMode2 = new DarkModeManager();
    integrationTest.assertEqual(darkMode2.getCurrentTheme(), 'dark', 'Dark mode preference should persist');
    
    // Reset to light
    darkMode.setTheme('light');
});

// Test component integration
integrationTest.test('SearchBar component integrates with KnowledgeAPI', async () => {
    const searchComponent = searchBar();
    
    // Mock API
    searchComponent.api = {
        search: async (query) => ({
            results: [
                {
                    id: 1,
                    text: `Result for ${query}`,
                    highlighted_text: `<mark>Result</mark> for ${query}`,
                    video_id: 'test-video',
                    start_ms: 10000,
                    rank: 0.8
                }
            ],
            total_found: 1,
            has_more: false,
            query_time_ms: 1.5
        })
    };
    
    searchComponent.query = 'test query';
    await searchComponent.performSearch();
    
    integrationTest.assertEqual(searchComponent.suggestions.length, 1, 'Should have one suggestion');
    integrationTest.assertEqual(searchComponent.suggestions[0].text, '<mark>Result</mark> for test query', 'Suggestion should have highlighted text');
    integrationTest.assert(searchComponent.isOpen, 'Suggestions should be open');
});

integrationTest.test('Modal component integrates with event system', async () => {
    const modalComponent = modal();
    
    // Initialize the component
    modalComponent.init();
    
    integrationTest.assert(!modalComponent.isOpen, 'Modal should start closed');
    
    // Emit showModal event
    eventSystem.emit('showModal', {
        type: 'entity',
        data: { name: 'Test Entity', type: 'person' }
    });
    
    // Give event time to process
    await integrationTest.wait(10);
    
    integrationTest.assert(modalComponent.isOpen, 'Modal should open from event');
    integrationTest.assertEqual(modalComponent.type, 'entity', 'Modal type should be set from event');
    integrationTest.assertEqual(modalComponent.data.name, 'Test Entity', 'Modal data should be set from event');
    
    // Test closing with escape
    eventSystem.emit('escape');
    await integrationTest.wait(10);
    
    integrationTest.assert(!modalComponent.isOpen, 'Modal should close from escape event');
});

integrationTest.test('ErrorBoundary component integrates with event system', async () => {
    const errorComponent = errorBoundary();
    
    // Initialize the component
    errorComponent.init();
    
    integrationTest.assert(!errorComponent.hasError, 'Should start with no error');
    
    // Emit error event
    const testError = new Error('Integration test error');
    eventSystem.emit('error', { error: testError, context: 'Integration test' });
    
    // Give event time to process
    await integrationTest.wait(10);
    
    integrationTest.assert(errorComponent.hasError, 'Should have error after event');
    integrationTest.assertEqual(errorComponent.error, testError, 'Error should be set from event');
    integrationTest.assertEqual(errorComponent.errorContext, 'Integration test', 'Context should be set from event');
});

integrationTest.test('LoadingSpinner component responds to API loading states', async () => {
    const spinnerComponent = loadingSpinner();
    spinnerComponent.operation = 'search'; // Listen for search operations
    
    // Initialize the component
    spinnerComponent.init();
    
    integrationTest.assert(!spinnerComponent.isVisible, 'Spinner should start hidden');
    
    // Emit loading change event
    eventSystem.emit('knowledgeAPI:loadingChange', {
        detail: { operation: 'search', loading: true }
    });
    
    // Give event time to process
    await integrationTest.wait(10);
    
    integrationTest.assert(spinnerComponent.isVisible, 'Spinner should be visible during loading');
    
    // Emit loading complete event
    eventSystem.emit('knowledgeAPI:loadingChange', {
        detail: { operation: 'search', loading: false }
    });
    
    await integrationTest.wait(10);
    
    integrationTest.assert(!spinnerComponent.isVisible, 'Spinner should be hidden after loading');
});

// Test responsive design
integrationTest.test('Responsive design classes work correctly', () => {
    // Test mobile breakpoint detection
    const mobileQuery = window.matchMedia('(max-width: 640px)');
    const tabletQuery = window.matchMedia('(max-width: 768px)');
    
    integrationTest.assertType(mobileQuery.matches, 'boolean', 'Mobile media query should return boolean');
    integrationTest.assertType(tabletQuery.matches, 'boolean', 'Tablet media query should return boolean');
});

// Test accessibility features
integrationTest.test('Accessibility features are present', () => {
    // Test ARIA attributes in components
    const component = modal();
    const title = component.getTitle();
    integrationTest.assertType(title, 'string', 'Modal should provide accessible title');
    
    // Test keyboard navigation support
    integrationTest.assertType(eventSystem.registerShortcut, 'function', 'Keyboard shortcuts should be supported');
    integrationTest.assertType(eventSystem.isInputElement, 'function', 'Input element detection should be available');
});

// Test performance considerations
integrationTest.test('Components handle performance optimizations', async () => {
    // Test debouncing
    const debouncedFn = eventSystem.debounce(() => {}, 100);
    integrationTest.assertType(debouncedFn, 'function', 'Debounced function should be returned');
    
    // Test throttling
    const throttledFn = eventSystem.throttle(() => {}, 100);
    integrationTest.assertType(throttledFn, 'function', 'Throttled function should be returned');
    
    // Test API retry logic
    const api = new KnowledgeAPI();
    integrationTest.assertEqual(api.defaultRetryAttempts, 3, 'API should have retry attempts configured');
    integrationTest.assertEqual(api.requestTimeout, 30000, 'API should have timeout configured');
});

// Test error handling integration
integrationTest.test('Error handling works across components', async () => {
    let globalErrorCaught = false;
    
    // Set up global error handler
    eventSystem.onError((error, context) => {
        globalErrorCaught = true;
    });
    
    // Trigger an error through the system
    eventSystem.handleError(new Error('Test error'), 'Integration test');
    
    // Give error time to propagate
    await integrationTest.wait(10);
    
    integrationTest.assert(globalErrorCaught, 'Global error handler should catch errors');
});

// Test component cleanup and memory management
integrationTest.test('Components clean up properly', () => {
    // Test event subscription cleanup
    let eventReceived = false;
    const unsubscribe = eventSystem.on('cleanup-test', () => {
        eventReceived = true;
    });
    
    // Unsubscribe
    unsubscribe();
    
    // Emit event
    eventSystem.emit('cleanup-test');
    
    integrationTest.assert(!eventReceived, 'Event should not be received after unsubscribe');
});

// Test cross-browser compatibility basics
integrationTest.test('Modern browser features are available', () => {
    integrationTest.assertExists(window.fetch, 'Fetch API should be available');
    integrationTest.assertExists(window.Promise, 'Promises should be available');
    integrationTest.assertExists(window.localStorage, 'localStorage should be available');
    integrationTest.assertExists(window.matchMedia, 'matchMedia should be available');
    integrationTest.assertExists(document.querySelector, 'querySelector should be available');
    integrationTest.assertExists(document.addEventListener, 'addEventListener should be available');
});

// Export for test runner
if (typeof window !== 'undefined') {
    window.integrationTest = integrationTest;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = integrationTest;
}