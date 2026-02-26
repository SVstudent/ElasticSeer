#!/bin/bash

echo "Testing Rich Analysis API"
echo "=========================="
echo ""

# Start backend if not running
if ! lsof -ti:8001 > /dev/null 2>&1; then
    echo "Starting backend..."
    cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 &
    sleep 5
fi

echo "Test 1: Analyze api-gateway metrics"
curl -s -X POST http://localhost:8001/api/analysis/service_metrics \
  -H "Content-Type: application/json" \
  -d '{"service": "api-gateway", "hours": 24}' | python -m json.tool

echo ""
echo ""
echo "Test 2: Compare service health"
curl -s -X GET http://localhost:8001/api/analysis/service_health | python -m json.tool

echo ""
echo ""
echo "Test 3: Get active anomalies"
curl -s -X GET http://localhost:8001/api/analysis/active_anomalies | python -m json.tool | head -50

echo ""
echo ""
echo "Test 4: Get incident statistics"
curl -s -X GET http://localhost:8001/api/analysis/incident_stats | python -m json.tool
