#!/bin/bash

# test_fibocli.sh
# Test script for fibocli CLI commands
# Run from /mnt/c/Users/HP/Documents/METS/forest-v4/fibocli/
# Usage: bash test_fibocli.sh

set -e  # Exit on any error

echo "Starting fibocli CLI tests..."

# Initialize database with overwrite
echo "Testing: fibocli init --overwrite"
fibocli init --overwrite
if [ $? -eq 0 ]; then
    echo "PASS: Database initialized successfully"
else
    echo "FAIL: Database initialization failed"
    exit 1
fi

# Test signup
echo "Testing: fibocli signup"
fibocli signup "John Doe" "johndoe" "john.doe@example.com" "password123"
if [ $? -eq 0 ]; then
    echo "PASS: User signup successful"
else
    echo "FAIL: User signup failed"
    exit 1
fi

# Test login
echo "Testing: fibocli login"
fibocli login "johndoe" "password123"
if [ $? -eq 0 ]; then
    echo "PASS: Login successful"
else
    echo "FAIL: Login failed"
    exit 1
fi

# Test create-ecology
echo "Testing: fibocli create-ecology"
fibocli create-ecology "Ecology 1"
if [ $? -eq 0 ]; then
    echo "PASS: Ecology creation successful"
else
    echo "FAIL: Ecology creation failed"
    exit 1
fi

# Test create-forest with valid ecology_id
echo "Testing: fibocli create-forest with valid ecology_id"
fibocli create-forest 1 "Forest 1"
if [ $? -eq 0 ]; then
    echo "PASS: Forest creation successful"
else
    echo "FAIL: Forest creation failed"
    exit 1
fi

# Test create-forest with invalid ecology_id
echo "Testing: fibocli create-forest with invalid ecology_id"
fibocli create-forest 999 "Forest 2" 2>&1 | grep -q "Invalid or deleted ecology_id"
if [ $? -eq 0 ]; then
    echo "PASS: Invalid ecology_id correctly rejected"
else
    echo "FAIL: Invalid ecology_id test failed"
    exit 1
fi

# Test create-tree
echo "Testing: fibocli create-tree"
fibocli create-tree 1 "Tree 1"
if [ $? -eq 0 ]; then
    echo "PASS: Tree creation successful"
else
    echo "FAIL: Tree creation failed"
    exit 1
fi

# Test plant-wave
echo "Testing: fibocli plant-wave"
fibocli plant-wave forest 1 5
if [ $? -eq 0 ]; then
    echo "PASS: Wave planting successful"
else
    echo "FAIL: Wave planting failed"
    exit 1
fi

# Test print-tree
echo "Testing: fibocli print-tree"
fibocli print-tree 1 | grep -q "Tree 1"
if [ $? -eq 0 ]; then
    echo "PASS: Print tree successful"
else
    echo "FAIL: Print tree failed"
    exit 1
fi

# Test user settings
echo "Testing: fibocli get-settings"
fibocli get-settings | grep -q "k_u"
if [ $? -eq 0 ]; then
    echo "PASS: Get settings successful"
else
    echo "FAIL: Get settings failed"
    exit 1
fi

echo "All fibocli CLI tests completed successfully!
