#!/bin/bash

# ElasticSeer Chat UI - Quick Start Script
# This script starts both the backend and frontend servers

set -e

echo "🚀 Starting ElasticSeer Chat UI..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backend .env exists
if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}⚠️  Warning: backend/.env not found${NC}"
    echo "Please create backend/.env with your Elasticsearch and Kibana credentials"
    echo "See backend/.env.example for reference"
    exit 1
fi

# Check if node_modules exists in frontend
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${BLUE}📦 Installing frontend dependencies...${NC}"
    cd frontend
    npm install
    cd ..
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
    echo ""
fi

# Check if Python virtual environment exists or is already activated
if [ -z "$VIRTUAL_ENV" ] && [ ! -d "backend/venv" ]; then
    echo -e "${YELLOW}⚠️  Python virtual environment not found${NC}"
    echo "Please create a virtual environment and install dependencies:"
    echo "  cd backend"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Stopping servers...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo -e "${BLUE}🔧 Starting FastAPI backend...${NC}"
cd backend
# Only activate venv if not already in one
if [ -z "$VIRTUAL_ENV" ]; then
    source venv/bin/activate
fi
python -m uvicorn app.main:app --reload --port 8001 > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..
echo -e "${GREEN}✓ Backend started on http://localhost:8001${NC}"
echo ""

# Wait for backend to be ready
echo -e "${BLUE}⏳ Waiting for backend to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${YELLOW}⚠️  Backend took too long to start. Check backend.log for errors${NC}"
        exit 1
    fi
    sleep 1
done
echo ""

# Start frontend
echo -e "${BLUE}🎨 Starting React frontend...${NC}"
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo -e "${GREEN}✓ Frontend started on http://localhost:5173${NC}"
echo ""

# Wait for frontend to be ready
echo -e "${BLUE}⏳ Waiting for frontend to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:5173 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Frontend is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${YELLOW}⚠️  Frontend took too long to start. Check frontend.log for errors${NC}"
        exit 1
    fi
    sleep 1
done
echo ""

# Success message
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✨ ElasticSeer Chat UI is running!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}🌐 Frontend:${NC} http://localhost:5173"
echo -e "${BLUE}🔧 Backend:${NC}  http://localhost:8001"
echo -e "${BLUE}📚 API Docs:${NC} http://localhost:8001/docs"
echo ""
echo -e "${YELLOW}💡 Try these prompts:${NC}"
echo "   • Show me recent incidents"
echo "   • What are the current anomalies?"
echo "   • Create a PR for INC-002"
echo "   • Search for authentication code"
echo ""
echo -e "${YELLOW}📋 Logs:${NC}"
echo "   • Backend:  tail -f backend.log"
echo "   • Frontend: tail -f frontend.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all servers${NC}"
echo ""

# Keep script running
wait
