#!/bin/bash

echo "Testing ElasticSeer Agent with Real Data"
echo "=========================================="
echo ""

# Test 1: Check for anomalies
echo "Test 1: Checking for anomalies in api-gateway..."
curl -s -X POST http://localhost:8001/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Check for anomalies in the api-gateway service",
    "conversation_history": []
  }' | python -m json.tool

echo ""
echo ""

# Test 2: Show recent incidents
echo "Test 2: Show recent incidents..."
curl -s -X POST http://localhost:8001/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me recent incidents",
    "conversation_history": []
  }' | python -m json.tool

echo ""
echo ""

# Test 3: Analyze metrics
echo "Test 3: Analyze metrics for payment-service..."
curl -s -X POST http://localhost:8001/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Analyze metrics for payment-service in the last 24 hours",
    "conversation_history": []
  }' | python -m json.tool
