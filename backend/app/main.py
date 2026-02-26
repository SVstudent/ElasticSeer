"""
ElasticSeer - Autonomous Remediation Platform
FastAPI application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import elasticseer_tools, agent_chat_gemini, rich_analysis, agent_chat_enhanced, incident_management, github_integration

app = FastAPI(
    title="ElasticSeer",
    description="Autonomous remediation platform with multi-agent architecture",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://*.elastic.cloud"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(elasticseer_tools.router)
app.include_router(agent_chat_gemini.router)  # Gemini + Elastic MCP = Best of both worlds!
app.include_router(rich_analysis.router)  # Rich analysis with actual data
app.include_router(agent_chat_enhanced.router)  # Enhanced chat with rich responses
app.include_router(incident_management.router)  # Incident registration and workflows
app.include_router(github_integration.router)  # GitHub file access and sync

# Import and include reasoning trace router
from app.api import agent_chat_with_reasoning
app.include_router(agent_chat_with_reasoning.router)  # Chat with reasoning trace

@app.get("/")
async def root():
    return {"message": "ElasticSeer API - Gemini Intelligence + Elastic MCP Data + Autonomous Workflows + GitHub Integration", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
