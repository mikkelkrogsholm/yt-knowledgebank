#!/bin/bash

# Troubleshooting Guide - Solution Verification Script
# This script tests that common troubleshooting solutions work correctly

echo "🔧 YouTube Knowledgebank - Troubleshooting Solution Tests"
echo "=========================================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
PASSED=0
FAILED=0

test_result() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $1"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: $1"
        FAILED=$((FAILED + 1))
    fi
}

echo
echo "🐳 Docker Environment Tests"
echo "----------------------------"

# Test 1: Docker is running
docker --version > /dev/null 2>&1
test_result "Docker is installed and running"

# Test 2: Docker Compose is available
docker compose version > /dev/null 2>&1
test_result "Docker Compose is available"

# Test 3: Application container can be started (check if it's running)
docker compose ps | grep -q "web" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ PASS${NC}: Application container is running"
    PASSED=$((PASSED + 1))
    CONTAINER_RUNNING=true
else
    echo -e "${YELLOW}⚠️  SKIP${NC}: Application container not running (start with 'docker compose up')"
    CONTAINER_RUNNING=false
fi

echo
echo "🌐 Application Health Tests"
echo "----------------------------"

if [ "$CONTAINER_RUNNING" = true ]; then
    # Test 4: Application responds on port 8765
    curl -s -f http://localhost:8765/ > /dev/null 2>&1
    test_result "Application responds on http://localhost:8765"
    
    # Test 5: API endpoints are accessible
    curl -s -I http://localhost:8765/api/migration/status | grep -q "200 OK" 2>/dev/null
    test_result "Migration API endpoint is accessible"
    
    # Test 6: Settings page is accessible
    curl -s -I http://localhost:8765/settings | grep -q "200 OK" 2>/dev/null
    test_result "Settings page is accessible"
    
    # Test 7: Static files are served
    curl -s -I http://localhost:8765/static/js/components/ | grep -q "200 OK" 2>/dev/null
    test_result "Static JavaScript files are accessible"
else
    echo "⚠️  Skipping application health tests - container not running"
fi

echo
echo "🗄️ Database Tests"
echo "-------------------"

if [ "$CONTAINER_RUNNING" = true ]; then
    # Test 8: Database file exists
    docker compose exec -T web test -f /app/data/knowledge_bank.db 2>/dev/null
    test_result "Database file exists"
    
    # Test 9: Database is accessible
    docker compose exec -T web sqlite3 /app/data/knowledge_bank.db "SELECT 1;" > /dev/null 2>&1
    test_result "Database is accessible and responsive"
    
    # Test 10: Check database integrity
    docker compose exec -T web sqlite3 /app/data/knowledge_bank.db "PRAGMA integrity_check;" 2>/dev/null | grep -q "ok"
    test_result "Database integrity check passes"
else
    echo "⚠️  Skipping database tests - container not running"
fi

echo
echo "📁 File System Tests"
echo "---------------------"

# Test 11: Data directory exists and is writable
if [ -d "./data" ] && [ -w "./data" ]; then
    echo -e "${GREEN}✅ PASS${NC}: Data directory exists and is writable"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}❌ FAIL${NC}: Data directory missing or not writable"
    FAILED=$((FAILED + 1))
fi

# Test 12: Required directories exist
if [ -d "./docs" ] && [ -d "./app" ] && [ -d "./templates" ]; then
    echo -e "${GREEN}✅ PASS${NC}: Project directory structure is correct"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}❌ FAIL${NC}: Project directory structure is incomplete"
    FAILED=$((FAILED + 1))
fi

echo
echo "🔧 System Resource Tests"
echo "-------------------------"

# Test 13: Check available disk space (should have at least 1GB free)
AVAILABLE_SPACE=$(df . | awk 'NR==2 {print $4}')
if [ "$AVAILABLE_SPACE" -gt 1048576 ]; then
    echo -e "${GREEN}✅ PASS${NC}: Sufficient disk space available ($(($AVAILABLE_SPACE/1024/1024))GB free)"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠️  WARN${NC}: Low disk space ($(($AVAILABLE_SPACE/1024/1024))GB free, recommend >1GB)"
fi

# Test 14: Check if port 8765 is available or in use by our app
PORT_CHECK=$(lsof -i :8765 2>/dev/null | wc -l)
if [ "$PORT_CHECK" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  INFO${NC}: Port 8765 is available (application not running)"
elif [ "$PORT_CHECK" -gt 0 ]; then
    if [ "$CONTAINER_RUNNING" = true ]; then
        echo -e "${GREEN}✅ PASS${NC}: Port 8765 is in use by the application"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: Port 8765 is in use by another process"
        FAILED=$((FAILED + 1))
    fi
fi

echo
echo "📋 Test Summary"
echo "==============="
echo -e "Tests Passed: ${GREEN}$PASSED${NC}"
echo -e "Tests Failed: ${RED}$FAILED${NC}"
echo -e "Total Tests: $(($PASSED + $FAILED))"

if [ $FAILED -eq 0 ]; then
    echo
    echo -e "${GREEN}🎉 All tests passed! Your environment is healthy.${NC}"
    exit 0
else
    echo
    echo -e "${RED}⚠️  Some tests failed. Check the troubleshooting guide for solutions:${NC}"
    echo "   docs/troubleshooting-guide.md"
    exit 1
fi