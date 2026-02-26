#!/bin/bash

echo "Testing Enhanced Chat API"
echo "=========================="
echo ""

echo "Test 1: Analyze metrics for api-gateway"
echo "----------------------------------------"
curl -s -X POST http://localhost:8001/api/agent/chat_enhanced \
  -H "Content-Type: application/json" \
  -d '{"message": "Analyze metrics for api-gateway"}' | python -c "import sys, json; data=json.load(sys.stdin); print(data['response'])"

echo ""
echo ""
echo "Test 2: Compare service health"
echo "-------------------------------"
curl -s -X POST http://localhost:8001/api/agent/chat_enhanced \
  -H "Content-Type: application/json" \
  -d '{"message": "Compare service health"}' | python -c "import sys, json; data=json.load(sys.stdin); print(data['response'])"

echo ""
echo ""
echo "Test 3: Show active anomalies"
echo "------------------------------"
curl -s -X POST http://localhost:8001/api/agent/chat_enhanced \
  -H "Content-Type: application/json" \
  -d '{"message": "Show active anomalies"}' | python -c "import sys, json; data=json.load(sys.stdin); print(data['response'])"

echo ""
echo ""
echo "Test 4: Show incident statistics"
echo "---------------------------------"
curl -s -X POST http://localhost:8001/api/agent/chat_enhanced \
  -H "Content-Type: application/json" \
  -d '{"message": "Show incident statistics"}' | python -c "import sys, json; data=json.load(sys.stdin); print(data['response'])"
