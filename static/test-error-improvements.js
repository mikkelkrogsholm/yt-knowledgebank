/**
 * Test script to verify error handling improvements for issue #11
 * 
 * This script tests null/undefined error handling to ensure no cascade failures
 */

// Test results storage
const testResults = {
    passed: 0,
    failed: 0,
    tests: []
};

// Helper function to run a test
function runTest(testName, testFn) {
    try {
        const result = testFn();
        if (result) {
            testResults.passed++;
            testResults.tests.push({ name: testName, status: 'PASSED' });
            console.log(`✅ ${testName}: PASSED`);
        } else {
            testResults.failed++;
            testResults.tests.push({ name: testName, status: 'FAILED', error: 'Test returned false' });
            console.log(`❌ ${testName}: FAILED - Test returned false`);
        }
    } catch (error) {
        testResults.failed++;
        testResults.tests.push({ name: testName, status: 'FAILED', error: error.message });
        console.log(`❌ ${testName}: FAILED - ${error.message}`);
    }
}

// Test null error handling
function testNullErrorHandling() {
    console.log('\n🧪 Testing null/undefined error handling...\n');
    
    // Test ErrorBoundary null handling
    runTest('ErrorBoundary handles null errors', () => {
        const component = errorBoundary();
        const initialErrorState = component.hasError;
        component.handleError(null, 'Test null');
        return component.hasError === initialErrorState; // Should not change error state
    });
    
    runTest('ErrorBoundary handles undefined errors', () => {
        const component = errorBoundary();
        const initialErrorState = component.hasError;
        component.handleError(undefined, 'Test undefined');
        return component.hasError === initialErrorState; // Should not change error state
    });
    
    runTest('ErrorBoundary handles empty string errors', () => {
        const component = errorBoundary();
        const initialErrorState = component.hasError;
        component.handleError('', 'Test empty string');
        return component.hasError === initialErrorState; // Should not change error state
    });
    
    runTest('ErrorBoundary getSafeErrorMessage with null', () => {
        const component = errorBoundary();
        component.error = null;
        component.errorMessage = null;
        const message = component.getSafeErrorMessage();
        return message === ''; // Should return empty string
    });
    
    runTest('ErrorBoundary getErrorMessage utility with null', () => {
        const component = errorBoundary();
        const message = component.getErrorMessage(null);
        return message === ''; // Should return empty string
    });
    
    runTest('ErrorBoundary safeStringify with null', () => {
        const component = errorBoundary();
        const stringified = component.safeStringify(null);
        return stringified === 'null'; // Should return 'null' string
    });
    
    // Test EventSystem null handling
    runTest('EventSystem handles null errors', () => {
        let errorEventEmitted = false;
        const unsubscribe = eventSystem.on('error', () => {
            errorEventEmitted = true;
        });
        
        eventSystem.handleError(null, 'Test null');
        unsubscribe();
        
        return !errorEventEmitted; // Should not emit error event
    });
    
    runTest('EventSystem handles undefined errors', () => {
        let errorEventEmitted = false;
        const unsubscribe = eventSystem.on('error', () => {
            errorEventEmitted = true;
        });
        
        eventSystem.handleError(undefined, 'Test undefined');
        unsubscribe();
        
        return !errorEventEmitted; // Should not emit error event
    });
    
    runTest('EventSystem getErrorMessage with null', () => {
        const message = eventSystem.getErrorMessage(null);
        return message === ''; // Should return empty string
    });
    
    runTest('EventSystem safeStringify with null', () => {
        const stringified = eventSystem.safeStringify(null);
        return stringified === 'null'; // Should return 'null' string
    });
}

// Test error object conversion safety
function testErrorObjectSafety() {
    console.log('\n🧪 Testing error object conversion safety...\n');
    
    runTest('ErrorBoundary handles object errors safely', () => {
        const component = errorBoundary();
        component.handleError({ someProperty: 'value' }, 'Test object error');
        return component.hasError && component.error instanceof Error;
    });
    
    runTest('ErrorBoundary handles array errors safely', () => {
        const component = errorBoundary();
        component.handleError(['error', 'array'], 'Test array error');
        return component.hasError && component.error instanceof Error;
    });
    
    runTest('EventSystem handles object errors safely', () => {
        let capturedError = null;
        const unsubscribe = eventSystem.on('error', (data) => {
            capturedError = data.error;
        });
        
        eventSystem.handleError({ someProperty: 'value' }, 'Test object error');
        unsubscribe();
        
        return capturedError instanceof Error;
    });
}

// Test cascade prevention
function testCascadePrevention() {
    console.log('\n🧪 Testing error cascade prevention...\n');
    
    runTest('No cascading errors from null handling', () => {
        let errorCount = 0;
        const unsubscribe = eventSystem.on('error', () => {
            errorCount++;
        });
        
        // Try to trigger cascade by handling multiple null errors
        eventSystem.handleError(null, 'Test 1');
        eventSystem.handleError(undefined, 'Test 2');
        eventSystem.handleError('', 'Test 3');
        
        const component = errorBoundary();
        component.handleError(null, 'Test 4');
        component.handleError(undefined, 'Test 5');
        component.handleError('', 'Test 6');
        
        unsubscribe();
        
        return errorCount === 0; // No error events should be emitted
    });
    
    runTest('Error handling methods dont throw on null state', () => {
        const component = errorBoundary();
        // Ensure clean state
        component.error = null;
        component.errorMessage = null;
        
        // These should not throw
        const friendlyMessage = component.getUserFriendlyMessage();
        const canRetry = component.canRetry();
        const actions = component.getSuggestedActions();
        const icon = component.getErrorIcon();
        
        return typeof friendlyMessage === 'string' && 
               typeof canRetry === 'boolean' &&
               Array.isArray(actions) &&
               typeof icon === 'string';
    });
}

// Main test runner
function runAllTests() {
    console.log('🚀 Starting Error Handling Improvement Tests (Issue #11)\n');
    console.log('='*60);
    
    testNullErrorHandling();
    testErrorObjectSafety();
    testCascadePrevention();
    
    console.log('\n' + '='*60);
    console.log('📊 Test Summary:');
    console.log(`✅ Passed: ${testResults.passed}`);
    console.log(`❌ Failed: ${testResults.failed}`);
    console.log(`📈 Pass Rate: ${Math.round((testResults.passed / (testResults.passed + testResults.failed)) * 100)}%`);
    
    if (testResults.failed === 0) {
        console.log('\n🎉 All error handling improvements working correctly!');
        console.log('✅ Issue #11 has been successfully fixed!');
        return true;
    } else {
        console.log('\n⚠️  Some tests failed. Please check the implementation.');
        console.log('\n Failed tests:');
        testResults.tests.filter(t => t.status === 'FAILED').forEach(test => {
            console.log(`   • ${test.name}: ${test.error || 'Unknown error'}`);
        });
        return false;
    }
}

// Check if we're in a browser environment and can run the tests
if (typeof window !== 'undefined' && 
    typeof errorBoundary === 'function' && 
    typeof eventSystem === 'object') {
    
    // Run tests when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', runAllTests);
    } else {
        runAllTests();
    }
} else {
    console.error('❌ Test environment not ready. Required components not available.');
    console.log('   Make sure errorBoundary function and eventSystem object are loaded.');
}