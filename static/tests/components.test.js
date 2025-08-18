/**
 * Component Tests
 * 
 * Tests for Alpine.js components and their functionality
 */

// Component testing framework
class ComponentTester {
    constructor() {
        this.tests = [];
        this.passed = 0;
        this.failed = 0;
    }
    
    test(name, testFn) {
        this.tests.push({ name, testFn });
    }
    
    async run() {
        console.log('🧪 Running Component Tests...\n');
        
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
        
        console.log(`\n📊 Component Test Results: ${this.passed} passed, ${this.failed} failed`);
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
}

const componentTest = new ComponentTester();

// Test SearchBar Component
componentTest.test('SearchBar component exists and is function', () => {
    componentTest.assertType(searchBar, 'function', 'searchBar should be a function');
});

componentTest.test('SearchBar component creates valid object', () => {
    const component = searchBar();
    componentTest.assertType(component, 'object', 'searchBar() should return an object');
    componentTest.assertExists(component.query, 'Component should have query property');
    componentTest.assertExists(component.suggestions, 'Component should have suggestions property');
    componentTest.assertExists(component.handleInput, 'Component should have handleInput method');
    componentTest.assertExists(component.handleSubmit, 'Component should have handleSubmit method');
});

componentTest.test('SearchBar component has required methods', () => {
    const component = searchBar();
    const requiredMethods = [
        'handleInput', 'handleSubmit', 'handleKeydown', 'selectSuggestion',
        'closeSuggestions', 'handleFocus', 'handleBlur', 'setSearchType',
        'getPlaceholderText', 'performSearch'
    ];
    
    requiredMethods.forEach(method => {
        componentTest.assertType(component[method], 'function', `Component should have ${method} method`);
    });
});

componentTest.test('SearchBar component initial state is correct', () => {
    const component = searchBar();
    componentTest.assertEqual(component.query, '', 'Initial query should be empty');
    componentTest.assertEqual(component.suggestions.length, 0, 'Initial suggestions should be empty');
    componentTest.assertEqual(component.isOpen, false, 'Initial isOpen should be false');
    componentTest.assertEqual(component.loading, false, 'Initial loading should be false');
    componentTest.assertEqual(component.selectedIndex, -1, 'Initial selectedIndex should be -1');
});

// Test ResultCard Component
componentTest.test('ResultCard component exists and is function', () => {
    componentTest.assertType(resultCard, 'function', 'resultCard should be a function');
});

componentTest.test('ResultCard component creates valid object', () => {
    const component = resultCard();
    componentTest.assertType(component, 'object', 'resultCard() should return an object');
    componentTest.assertExists(component.type, 'Component should have type property');
    componentTest.assertExists(component.data, 'Component should have data property');
    componentTest.assertExists(component.getTitle, 'Component should have getTitle method');
    componentTest.assertExists(component.handleClick, 'Component should have handleClick method');
});

componentTest.test('ResultCard component handles different types', () => {
    const component = resultCard();
    const types = ['video', 'entity', 'topic', 'search_result'];
    
    types.forEach(type => {
        component.type = type;
        const title = component.getTitle();
        componentTest.assertType(title, 'string', `getTitle should return string for type ${type}`);
        
        const subtitle = component.getSubtitle();
        componentTest.assertType(subtitle, 'string', `getSubtitle should return string for type ${type}`);
    });
});

componentTest.test('ResultCard component formatting methods work', () => {
    const component = resultCard();
    
    // Test duration formatting
    componentTest.assertEqual(component.formatDuration(0), '0:00', 'formatDuration(0) should return 0:00');
    componentTest.assertEqual(component.formatDuration(60), '1:00', 'formatDuration(60) should return 1:00');
    componentTest.assertEqual(component.formatDuration(3661), '1:01:01', 'formatDuration(3661) should return 1:01:01');
    
    // Test text truncation
    const longText = 'This is a very long text that should be truncated';
    const truncated = component.truncateText(longText, 20);
    componentTest.assert(truncated.length <= 23, 'Truncated text should be shorter than or equal to maxLength + "..."');
    componentTest.assert(truncated.endsWith('...'), 'Truncated text should end with "..."');
});

// Test Modal Component
componentTest.test('Modal component exists and is function', () => {
    componentTest.assertType(modal, 'function', 'modal should be a function');
});

componentTest.test('Modal component creates valid object', () => {
    const component = modal();
    componentTest.assertType(component, 'object', 'modal() should return an object');
    componentTest.assertExists(component.isOpen, 'Component should have isOpen property');
    componentTest.assertExists(component.type, 'Component should have type property');
    componentTest.assertExists(component.show, 'Component should have show method');
    componentTest.assertExists(component.hide, 'Component should have hide method');
});

componentTest.test('Modal component show/hide functionality', () => {
    const component = modal();
    
    // Initial state
    componentTest.assertEqual(component.isOpen, false, 'Modal should start closed');
    
    // Test show
    component.show({ type: 'entity', data: { name: 'Test Entity' } });
    componentTest.assertEqual(component.isOpen, true, 'Modal should be open after show()');
    componentTest.assertEqual(component.type, 'entity', 'Modal type should be set');
    componentTest.assertEqual(component.data.name, 'Test Entity', 'Modal data should be set');
    
    // Test hide
    component.hide();
    componentTest.assertEqual(component.isOpen, false, 'Modal should be closed after hide()');
});

componentTest.test('Modal component size classes', () => {
    const component = modal();
    const sizes = ['sm', 'md', 'lg', 'xl', 'full'];
    
    sizes.forEach(size => {
        component.size = size;
        const classes = component.getSizeClasses();
        componentTest.assertType(classes, 'string', `getSizeClasses should return string for size ${size}`);
        componentTest.assert(classes.length > 0, `Size classes should not be empty for size ${size}`);
    });
});

// Test LoadingSpinner Component
componentTest.test('LoadingSpinner component exists and is function', () => {
    componentTest.assertType(loadingSpinner, 'function', 'loadingSpinner should be a function');
});

componentTest.test('LoadingSpinner component creates valid object', () => {
    const component = loadingSpinner();
    componentTest.assertType(component, 'object', 'loadingSpinner() should return an object');
    componentTest.assertExists(component.type, 'Component should have type property');
    componentTest.assertExists(component.isVisible, 'Component should have isVisible property');
    componentTest.assertExists(component.show, 'Component should have show method');
    componentTest.assertExists(component.hide, 'Component should have hide method');
});

componentTest.test('LoadingSpinner component show/hide functionality', () => {
    const component = loadingSpinner();
    
    // Initial state
    componentTest.assertEqual(component.isVisible, false, 'Spinner should start hidden');
    
    // Test show
    component.show({ type: 'progress', message: 'Loading...' });
    componentTest.assertEqual(component.isVisible, true, 'Spinner should be visible after show()');
    componentTest.assertEqual(component.type, 'progress', 'Spinner type should be set');
    componentTest.assertEqual(component.message, 'Loading...', 'Spinner message should be set');
    
    // Test hide
    component.hide();
    componentTest.assertEqual(component.isVisible, false, 'Spinner should be hidden after hide()');
});

componentTest.test('LoadingSpinner component progress functionality', () => {
    const component = loadingSpinner();
    
    // Test progress setting
    component.setProgress(50, 'Half way there...');
    componentTest.assertEqual(component.progress, 50, 'Progress should be set to 50');
    componentTest.assertEqual(component.message, 'Half way there...', 'Message should be updated');
    
    // Test progress bounds
    component.setProgress(-10);
    componentTest.assertEqual(component.progress, 0, 'Progress should be clamped to 0 minimum');
    
    component.setProgress(150);
    componentTest.assertEqual(component.progress, 100, 'Progress should be clamped to 100 maximum');
});

// Test ErrorBoundary Component
componentTest.test('ErrorBoundary component exists and is function', () => {
    componentTest.assertType(errorBoundary, 'function', 'errorBoundary should be a function');
});

componentTest.test('ErrorBoundary component creates valid object', () => {
    const component = errorBoundary();
    componentTest.assertType(component, 'object', 'errorBoundary() should return an object');
    componentTest.assertExists(component.hasError, 'Component should have hasError property');
    componentTest.assertExists(component.error, 'Component should have error property');
    componentTest.assertExists(component.handleError, 'Component should have handleError method');
    componentTest.assertExists(component.clearError, 'Component should have clearError method');
});

componentTest.test('ErrorBoundary component error handling', () => {
    const component = errorBoundary();
    
    // Initial state
    componentTest.assertEqual(component.hasError, false, 'Should start with no error');
    componentTest.assertEqual(component.error, null, 'Initial error should be null');
    
    // Test error handling
    const testError = new Error('Test error message');
    component.handleError(testError, 'Test context');
    
    componentTest.assertEqual(component.hasError, true, 'Should have error after handleError');
    componentTest.assertEqual(component.error, testError, 'Error should be stored');
    componentTest.assertEqual(component.errorContext, 'Test context', 'Context should be stored');
    
    // Test error clearing
    component.clearError();
    componentTest.assertEqual(component.hasError, false, 'Should have no error after clearError');
    componentTest.assertEqual(component.error, null, 'Error should be null after clearError');
});

componentTest.test('ErrorBoundary component user-friendly messages', () => {
    const component = errorBoundary();
    
    const testCases = [
        { error: new Error('Network error'), expected: 'Network connection error' },
        { error: new Error('404 Not Found'), expected: 'The requested resource was not found' },
        { error: new Error('500 Internal Server Error'), expected: 'Server error' },
        { error: new Error('API key invalid'), expected: 'API key error' },
        { error: new Error('Timeout occurred'), expected: 'Request timed out' }
    ];
    
    testCases.forEach(({ error, expected }) => {
        component.handleError(error, 'Test');
        const message = component.getUserFriendlyMessage();
        componentTest.assert(
            message.toLowerCase().includes(expected.toLowerCase().split(' ')[0]),
            `Message should contain "${expected.split(' ')[0]}" for error: ${error.message}`
        );
    });
});

// Test DarkModeToggle Component
componentTest.test('DarkModeToggle component exists and is function', () => {
    componentTest.assertType(darkModeToggle, 'function', 'darkModeToggle should be a function');
});

componentTest.test('DarkModeToggle component creates valid object', () => {
    const component = darkModeToggle();
    componentTest.assertType(component, 'object', 'darkModeToggle() should return an object');
    componentTest.assertExists(component.isDark, 'Component should have isDark property');
    componentTest.assertExists(component.toggle, 'Component should have toggle method');
    componentTest.assertExists(component.setLight, 'Component should have setLight method');
    componentTest.assertExists(component.setDark, 'Component should have setDark method');
});

componentTest.test('DarkModeToggle component toggle functionality', () => {
    const component = darkModeToggle();
    
    // Mock darkModeManager
    component.darkModeManager = {
        toggle: () => 'dark',
        setTheme: () => {},
        followSystem: () => {},
        getPreference: () => ({
            current: 'light',
            system: 'light',
            followingSystem: false
        })
    };
    
    componentTest.assertType(component.toggle, 'function', 'toggle should be a function');
    componentTest.assertType(component.getToggleIcon, 'function', 'getToggleIcon should be a function');
    componentTest.assertType(component.getToggleText, 'function', 'getToggleText should be a function');
});

// Test SkeletonLoader Component
componentTest.test('SkeletonLoader component exists and is function', () => {
    componentTest.assertType(skeletonLoader, 'function', 'skeletonLoader should be a function');
});

componentTest.test('SkeletonLoader component creates valid object', () => {
    const component = skeletonLoader();
    componentTest.assertType(component, 'object', 'skeletonLoader() should return an object');
    componentTest.assertExists(component.type, 'Component should have type property');
    componentTest.assertExists(component.count, 'Component should have count property');
    componentTest.assertExists(component.getContent, 'Component should have getContent method');
});

componentTest.test('SkeletonLoader component content generation', () => {
    const component = skeletonLoader();
    const types = ['card', 'list', 'text', 'image'];
    
    types.forEach(type => {
        component.type = type;
        const content = component.getContent();
        componentTest.assertType(content, 'string', `getContent should return string for type ${type}`);
        componentTest.assert(content.length > 0, `Content should not be empty for type ${type}`);
    });
});

// Integration tests with global event system
componentTest.test('Components integrate with event system', () => {
    componentTest.assertExists(eventSystem, 'Global eventSystem should exist');
    componentTest.assertType(eventSystem.on, 'function', 'eventSystem should have on method');
    componentTest.assertType(eventSystem.emit, 'function', 'eventSystem should have emit method');
    
    // Test event subscription and emission
    let eventReceived = false;
    const unsubscribe = eventSystem.on('test-component-event', () => {
        eventReceived = true;
    });
    
    eventSystem.emit('test-component-event');
    componentTest.assert(eventReceived, 'Event should be received');
    
    unsubscribe();
});

componentTest.test('Components can communicate through events', () => {
    const searchBarComponent = searchBar();
    const modalComponent = modal();
    
    // Mock API for searchBar
    searchBarComponent.api = {
        search: async () => ({ results: [], total_found: 0, has_more: false, query_time_ms: 1 })
    };
    
    let modalShown = false;
    const originalShow = modalComponent.show;
    modalComponent.show = (data) => {
        modalShown = true;
        originalShow.call(modalComponent, data);
    };
    
    // Listen for showModal event
    eventSystem.on('showModal', (data) => {
        modalComponent.show(data);
    });
    
    // Emit event that should trigger modal
    eventSystem.emit('showModal', { type: 'entity', data: { name: 'Test' } });
    
    componentTest.assert(modalShown, 'Modal should be shown when event is emitted');
});

// Run component tests if executed directly
if (typeof window !== 'undefined') {
    window.componentTest = componentTest;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = componentTest;
}