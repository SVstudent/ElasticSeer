"""
Enhanced Agent Chat - Intelligent file handling + Real AI agent
Only handles file detection/fetching, everything else goes to real AI
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import httpx
import re
import base64
import logging
from datetime import datetime
from github import Github
from elasticsearch import Elasticsearch
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent-enhanced"])


class ChatMessage(BaseModel):
    message: str
    conversation_history: List[Dict[str, Any]] = []


def get_github_client():
    """Get GitHub client"""
    if not settings.github_token:
        raise HTTPException(status_code=503, detail="GitHub not configured")
    return Github(settings.github_token)


@router.post("/chat_enhanced")
async def chat_enhanced(request: ChatMessage):
    """
    Enhanced chat with intelligent file handling
    - Detects file references in user messages
    - Fetches missing files from GitHub automatically
    - Delegates all other logic to the real AI agent
    """
    message = request.message.lower()
    original_message = request.message
    
    # ONLY handle file intelligence here
    # Detect if user is asking about a specific file
    file_keywords = {
        'readme': ['README.md'],
        'documentation': ['README.md', 'docs/README.md'],
        'config': ['config.py', 'config.json', 'settings.py'],
        'main': ['main.py', 'app.py', 'index.js'],
        'auth': ['auth.py', 'authentication.py'],
        'payment': ['payment.py', 'payment_service.py'],
    }
    
    detected_files = []
    for keyword, possible_files in file_keywords.items():
        if keyword in message:
            detected_files.extend(possible_files)
    
    # Check for explicit file paths
    file_pattern = r'([a-zA-Z0-9_/-]+\.(py|js|ts|md|json|yaml|yml|txt))'
    explicit_files = re.findall(file_pattern, original_message)
    if explicit_files:
        detected_files.extend([f[0] for f in explicit_files])
    
    # If files detected and user wants to work with them, check if we have them
    is_work_request = any(keyword in message for keyword in [
        'fix', 'improve', 'update', 'change', 'show', 'view', 'analyze', 'check'
    ])
    
    if detected_files and is_work_request:
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                # Check if file exists in Elasticsearch
                for file_path in detected_files[:1]:  # Check first detected file
                    search_response = await client.get(
                        f"http://localhost:8001/api/github/search_code?query={file_path}&limit=1"
                    )
                    
                    if search_response.status_code == 200:
                        search_data = search_response.json()
                        
                        if search_data['total'] > 0:
                            # File exists, let AI agent handle it
                            break
                        
                        # File not found - fetch it from GitHub
                        try:
                            github = get_github_client()
                            repo = github.get_repo(f"{settings.github_owner}/{settings.github_repo}")
                            file_content = repo.get_contents(file_path)
                            
                            # Decode and index
                            if file_content.encoding == "base64":
                                content = base64.b64decode(file_content.content).decode('utf-8')
                            else:
                                content = file_content.content
                            
                            es = Elasticsearch(
                                hosts=[settings.elasticsearch_url],
                                api_key=settings.elasticsearch_api_key,
                                verify_certs=True
                            )
                            
                            extension = file_path.split('.')[-1] if '.' in file_path else 'unknown'
                            language_map = {
                                'py': 'python', 'js': 'javascript', 'ts': 'typescript',
                                'md': 'markdown', 'json': 'json', 'yaml': 'yaml'
                            }
                            
                            doc = {
                                "file_path": file_path,
                                "file_name": file_content.name,
                                "content": content,
                                "language": language_map.get(extension, extension),
                                "service": file_path.split('/')[0] if '/' in file_path else 'general',
                                "repository": f"{settings.github_owner}/{settings.github_repo}",
                                "size": file_content.size,
                                "sha": file_content.sha,
                                "github_url": file_content.html_url,
                                "synced_at": datetime.utcnow().isoformat()
                            }
                            
                            es.index(index='code-repository', document=doc)
                            es.indices.refresh(index='code-repository')
                            
                            # File fetched, now let AI handle the request
                            break
                            
                        except Exception as e:
                            # Couldn't fetch file, let AI handle it
                            pass
                            
            except Exception as e:
                pass
    
    # Delegate EVERYTHING to the real AI agent
    # This makes responses truly adaptive and intelligent
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(
                "http://localhost:8001/api/agent/chat_with_reasoning",
                json=request.dict()
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Agent chat error: {response.status_code} - {response.text}")
                return {
                    "response": f"I encountered an issue processing your request (HTTP {response.status_code}). The backend may have completed some actions - please check the logs.",
                    "type": "error",
                    "status_code": response.status_code
                }
        except httpx.TimeoutException:
            logger.error("Agent chat timeout")
            return {
                "response": "The request timed out, but actions may have been completed. Please check if your PR was created or Slack messages were sent.",
                "type": "timeout"
            }
        except Exception as e:
            logger.error(f"Agent chat exception: {e}", exc_info=True)
            return {
                "response": f"Error communicating with agent: {str(e)}. Some actions may have completed successfully - please verify.",
                "type": "error"
            }
