"""
Enhanced Agent Chat - Detects analysis requests and provides rich responses
Supports incident registration and autonomous workflows
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import httpx
import re
import base64
from datetime import datetime
from github import Github
from elasticsearch import Elasticsearch
from app.core.config import settings

router = APIRouter(prefix="/api/agent", tags=["agent-enhanced"])


class ChatMessage(BaseModel):
    message: str
    conversation_history: List[Dict[str, str]] = []


def get_github_client():
    """Get GitHub client"""
    if not settings.github_token:
        raise HTTPException(status_code=503, detail="GitHub not configured")
    return Github(settings.github_token)


@router.post("/chat_enhanced")
async def chat_enhanced(request: ChatMessage):
    """
    Enhanced chat that detects analysis requests and provides rich responses
    Supports: metrics analysis, incident registration, autonomous workflows, intelligent file handling
    """
    message = request.message.lower()
    original_message = request.message
    
    # PRIORITY: Check for simple confirmations first (yes, proceed, etc.)
    if message.strip() in ['yes', 'proceed', 'yes proceed', 'go ahead', 'do it', 'ok', 'okay', 'sure']:
        # User confirmed - sync the configured repository
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    "http://localhost:8001/api/github/sync_to_elasticsearch",
                    json={"force": True}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    result_lines = [f"✅ Synced {data['synced_count']} files from {data.get('repository', 'repository')}!"]
                    result_lines.append("\nWhat would you like to do now?")
                    
                    return {
                        "response": "\n".join(result_lines),
                        "type": "sync_complete",
                        "synced_count": data['synced_count']
                    }
                else:
                    return {
                        "response": f"❌ Sync failed: {response.text}",
                        "type": "error"
                    }
            except Exception as e:
                return {
                    "response": f"❌ Failed to sync: {str(e)}",
                    "type": "error"
                }
    
    # Intelligent file detection and handling
    # Extract potential file references from the message
    file_keywords = {
        'readme': ['README.md', 'readme.md', 'README'],
        'documentation': ['README.md', 'DOCUMENTATION.md', 'docs/README.md'],
        'config': ['config.py', 'config.json', 'config.yaml', 'settings.py'],
        'main': ['main.py', 'app.py', 'index.js', 'index.ts'],
        'auth': ['auth.py', 'authentication.py', 'auth_service.py'],
        'payment': ['payment.py', 'payment_service.py', 'payments.py'],
    }
    
    # Check if user is asking about a specific file or service
    detected_files = []
    for keyword, possible_files in file_keywords.items():
        if keyword in message:
            detected_files.extend(possible_files)
    
    # Also check for explicit file mentions (e.g., "src/main.py")
    import re
    file_pattern = r'([a-zA-Z0-9_/-]+\.(py|js|ts|md|json|yaml|yml|txt|java|go|rs))'
    explicit_files = re.findall(file_pattern, original_message)
    if explicit_files:
        detected_files.extend([f[0] for f in explicit_files])
    
    # Check for incident/fix/improve requests
    is_incident_request = any(keyword in message for keyword in [
        'fix', 'improve', 'update', 'change', 'issue', 'problem', 'incident', 'bug'
    ])
    
    if is_incident_request and detected_files:
        # User wants to fix something - check if we have the file
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Search for the file in Elasticsearch
                for file_path in detected_files:
                    search_response = await client.get(
                        f"http://localhost:8001/api/github/search_code?query={file_path}&limit=5"
                    )
                    
                    if search_response.status_code == 200:
                        search_data = search_response.json()
                        
                        if search_data['total'] > 0:
                            # Found the file - create incident
                            found_file = search_data['files'][0]
                            
                            # Register incident
                            incident_response = await client.post(
                                "http://localhost:8001/api/incidents/register",
                                json={
                                    "title": original_message[:100],
                                    "service": found_file.get('service', 'general'),
                                    "severity": "Sev-3",
                                    "description": original_message,
                                    "target_file": found_file['file_path']
                                }
                            )
                            
                            if incident_response.status_code == 200:
                                incident_data = incident_response.json()
                                return {
                                    "response": f"""✅ Incident created: {incident_data['incident_id']}

Target: {found_file['file_path']}
Issue: {original_message}

Want me to generate a fix? Say "fix it" or "create PR" """,
                                    "type": "incident_created",
                                    "incident_id": incident_data['incident_id']
                                }
                
                # File not found - fetch it from GitHub
                github = get_github_client()
                repo = github.get_repo(f"{settings.github_owner}/{settings.github_repo}")
                
                # Try to find the file in GitHub
                for file_path in detected_files:
                    try:
                        file_content = repo.get_contents(file_path)
                        
                        # Found it! Download and index this specific file
                        if file_content.encoding == "base64":
                            import base64
                            content = base64.b64decode(file_content.content).decode('utf-8')
                        else:
                            content = file_content.content
                        
                        # Index in Elasticsearch
                        from elasticsearch import Elasticsearch
                        from datetime import datetime
                        
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
                        language = language_map.get(extension, extension)
                        
                        doc = {
                            "file_path": file_path,
                            "file_name": file_content.name,
                            "content": content,
                            "language": language,
                            "service": file_path.split('/')[0] if '/' in file_path else 'general',
                            "repository": f"{settings.github_owner}/{settings.github_repo}",
                            "size": file_content.size,
                            "sha": file_content.sha,
                            "github_url": file_content.html_url,
                            "synced_at": datetime.utcnow().isoformat()
                        }
                        
                        es.index(index='code-repository', document=doc)
                        es.indices.refresh(index='code-repository')
                        
                        # Now create the incident
                        incident_response = await client.post(
                            "http://localhost:8001/api/incidents/register",
                            json={
                                "title": original_message[:100],
                                "service": doc['service'],
                                "severity": "Sev-3",
                                "description": original_message,
                                "target_file": file_path
                            }
                        )
                        
                        if incident_response.status_code == 200:
                            incident_data = incident_response.json()
                            return {
                                "response": f"""✅ Found and indexed {file_path}!
✅ Incident created: {incident_data['incident_id']}

Issue: {original_message}

Want me to generate a fix? Say "fix it" """,
                                "type": "incident_created",
                                "incident_id": incident_data['incident_id']
                            }
                        
                    except Exception as e:
                        continue
                
                # Couldn't find the file anywhere
                return {
                    "response": f"""I couldn't find the file you're referring to in the repository.

What I tried: {', '.join(detected_files[:3])}

Can you specify the exact file path? Or say "sync repository" to download all files.""",
                    "type": "file_not_found"
                }
                
            except Exception as e:
                return {
                    "response": f"Error: {str(e)}",
                    "type": "error"
                }
    
    # Check for sync requests
    if any(keyword in message for keyword in ['sync', 'download', 'fetch']) and any(keyword in message for keyword in ['repository', 'repo', 'github', 'code']):
        # Just sync the configured repository
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    "http://localhost:8001/api/github/sync_to_elasticsearch",
                    json={"force": True}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    result_lines = [f"✅ Synced {data['synced_count']} files!"]
                    result_lines.append("\nWhat would you like to do?")
                    
                    return {
                        "response": "\n".join(result_lines),
                        "type": "sync_complete"
                    }
            except Exception as e:
                return {
                    "response": f"❌ Failed to sync: {str(e)}",
                    "type": "error"
                }
            
            # If search failed, ask for clarification
            return {
                "response": """# 📝 I'd be happy to help improve the README!

To get started, I need to understand what you'd like to change:

**Option 1: Let me investigate first**
- I can view the current README and suggest improvements
- Just say: "Show me the README first"

**Option 2: Tell me what to improve**
- Describe the specific changes you want (e.g., "Add a better introduction section")
- I'll create an incident and fix it automatically

**Option 3: Quick fix**
- Say "Fix the README" and I'll analyze it and make improvements

Which approach would you prefer?""",
                "type": "clarification"
            }
        
        # For other types of incidents, try to extract details intelligently
        services = ['api-gateway', 'auth-service', 'payment-service', 'user-service', 
                   'order-service', 'inventory-service', 'notification-service',
                   'database', 'cache', 'frontend']
        
        service = None
        for svc in services:
            if svc in message or svc.replace('-', ' ') in message:
                service = svc
                break
        
        # Extract severity
        severity = 'Sev-3'  # Default
        if 'sev-1' in message or 'critical' in message or 'severe' in message or 'urgent' in message:
            severity = 'Sev-1'
        elif 'sev-2' in message or 'high' in message or 'important' in message:
            severity = 'Sev-2'
        
        # If we have a service, ask for confirmation
        if service:
            return {
                "response": f"""# 🔍 I understand you want to address an issue with **{service}**

**What I detected:**
- Service: {service}
- Severity: {severity}
- Description: {message[:200]}

**Next steps:**
1. I can create an incident to track this
2. Search the codebase for relevant files
3. Generate an AI-powered fix
4. Create a GitHub PR
5. Notify the team on Slack

**Should I proceed with creating the incident and starting the autonomous fix workflow?**

Reply with:
- "Yes, proceed" - I'll handle everything automatically
- "Just create the incident" - I'll register it for later
- "Show me the code first" - I'll search for relevant files""",
                "type": "confirmation",
                "context": {
                    "service": service,
                    "severity": severity,
                    "description": message
                }
            }
        
        # Not enough information, ask for details
        return {
            "response": """# 🤔 I'd like to help, but I need a bit more information

**What I need to know:**
1. Which service or component is affected? (e.g., api-gateway, payment-service, README)
2. What's the issue or improvement you want?
3. How urgent is it? (Critical/High/Medium)

**Example:**
"The payment-service has high latency and needs optimization"

Or just describe the issue naturally, and I'll figure out the details!""",
            "type": "clarification"
        }
    
    # Check for "show me" requests
    if any(keyword in message for keyword in ['show me', 'view', 'display', 'let me see']):
        if 'readme' in message or 'documentation' in message:
            # User wants to see README first
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    # First, search in Elasticsearch
                    search_response = await client.get(
                        "http://localhost:8001/api/github/search_code?query=README&limit=5"
                    )
                    
                    readme_file = None
                    
                    if search_response.status_code == 200:
                        search_data = search_response.json()
                        
                        if search_data['total'] > 0:
                            readme_file = next((f['file_path'] for f in search_data['files'] if 'readme.md' in f['file_path'].lower()), None)
                    
                    # If not found in Elasticsearch, offer to sync from GitHub
                    if not readme_file:
                        return {
                            "response": """# 🔍 The README hasn't been uploaded to our database yet

**No worries!** I have access to your GitHub repositories and can fetch it right now.

**Shall I sync the repository from GitHub?**

This will:
- Download all code files from the repository
- Upload them to our Elasticsearch database
- Make them searchable and ready for analysis
- Take about 10-30 seconds

**Just say "yes" or "proceed" and I'll handle it automatically!**

Or if you prefer, tell me which specific repository to sync (I have access to all your public repos).""",
                            "type": "sync_offer",
                            "context": {
                                "action": "sync_github",
                                "reason": "readme_not_found"
                            }
                        }
                    
                    # Found in Elasticsearch, view it
                    if readme_file:
                        view_response = await client.post(
                            "http://localhost:8001/api/github/view_file",
                            json={"file_path": readme_file}
                        )
                        
                        if view_response.status_code == 200:
                            view_data = view_response.json()
                            
                            lines = [f"# 📄 Current README: {readme_file}\n"]
                            lines.append(f"**Size**: {view_data['size']} bytes")
                            lines.append(f"**URL**: {view_data['url']}\n")
                            lines.append("## Content\n")
                            lines.append("```markdown")
                            lines.append(view_data['content'][:2000])  # First 2000 chars
                            if len(view_data['content']) > 2000:
                                lines.append("\n... (truncated)")
                            lines.append("```\n")
                            lines.append("**What would you like me to improve?**")
                            lines.append("- Add a better introduction?")
                            lines.append("- Improve the structure?")
                            lines.append("- Add more examples?")
                            lines.append("\nJust tell me what to change, and I'll create a fix!")
                            
                            return {
                                "response": "\n".join(lines),
                                "type": "file_preview",
                                "file_path": readme_file
                            }
                except Exception as e:
                    pass
    
    # Check for sync requests
    if any(keyword in message for keyword in ['sync', 'download', 'fetch']) and any(keyword in message for keyword in ['repository', 'repo', 'github', 'code']):
        # Just sync the configured repository
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    "http://localhost:8001/api/github/sync_to_elasticsearch",
                    json={"force": True}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    result_lines = [f"# ✅ Synced {data['synced_count']} files!\n"]
                    
                    if data['synced_count'] > 0:
                        for file in data['synced_files'][:5]:
                            result_lines.append(f"- {file['file_path']}")
                    
                    result_lines.append("\n**All set!** What would you like to do?")
                    
                    return {
                        "response": "\n".join(result_lines),
                        "type": "sync_complete"
                    }
            except Exception as e:
                return {
                    "response": f"❌ Failed to sync: {str(e)}",
                    "type": "error"
                }
    
    # Check for GitHub file operations
    if any(keyword in message for keyword in ['view file', 'show file', 'get file', 'read file', 'file content']):
        # Extract file path
        import re
        
        # Try to extract file path (look for common patterns)
        file_match = re.search(r'["\']([^"\']+\.(py|js|ts|tsx|jsx|md|txt|json|yaml|yml|sh|sql|html|css))["\']', message)
        if not file_match:
            file_match = re.search(r'(\S+\.(py|js|ts|tsx|jsx|md|txt|json|yaml|yml|sh|sql|html|css))', message)
        
        if file_match:
            file_path = file_match.group(1)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.post(
                        "http://localhost:8001/api/github/view_file",
                        json={"file_path": file_path}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        lines = [f"# 📄 File: {file_path}\n"]
                        lines.append(f"**Size**: {data['size']} bytes")
                        lines.append(f"**Branch**: {data['branch']}")
                        lines.append(f"**URL**: {data['url']}\n")
                        lines.append("## Content\n")
                        lines.append(f"```{file_path.split('.')[-1]}")
                        lines.append(data['content'])
                        lines.append("```")
                        
                        return {
                            "response": "\n".join(lines),
                            "type": "file_content",
                            "file_path": file_path
                        }
                except Exception as e:
                    return {
                        "response": f"❌ Failed to view file: {str(e)}",
                        "type": "error"
                    }
        else:
            return {
                "response": "Please specify a file path. Example: `View file README.md`",
                "type": "error"
            }
    
    # Check for GitHub sync operations
    if any(keyword in message for keyword in ['sync github', 'sync files', 'download github', 'sync code', 'sync repository']):
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    "http://localhost:8001/api/github/sync_to_elasticsearch",
                    json={"force": 'force' in message or 'refresh' in message}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    lines = [f"# ✅ GitHub Sync Complete\n"]
                    lines.append(f"**Synced**: {data['synced_count']} files")
                    lines.append(f"**Errors**: {data['error_count']}")
                    lines.append(f"**Time**: {data['synced_at']}\n")
                    
                    if data['synced_count'] > 0:
                        lines.append("## Sample Files")
                        for file in data['synced_files'][:10]:
                            lines.append(f"- `{file['file_path']}` ({file['language']}, {file['size']} bytes)")
                    
                    if data['error_count'] > 0:
                        lines.append("\n## Errors")
                        for error in data['errors'][:5]:
                            lines.append(f"- `{error['file_path']}`: {error['error']}")
                    
                    return {
                        "response": "\n".join(lines),
                        "type": "github_sync",
                        "synced_count": data['synced_count']
                    }
            except Exception as e:
                return {
                    "response": f"❌ Failed to sync GitHub: {str(e)}",
                    "type": "error"
                }
    
    # Check for code search
    if any(keyword in message for keyword in ['search code', 'find code', 'search for', 'find in code']):
        # Extract search query
        query = message
        for keyword in ['search code', 'find code', 'search for', 'find in code', 'in github', 'in repository']:
            query = query.replace(keyword, '').strip()
        
        if query:
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.get(
                        f"http://localhost:8001/api/github/search_code?query={query}&limit=10"
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        lines = [f"# 🔍 Code Search Results: \"{query}\"\n"]
                        lines.append(f"**Total**: {data['total']} matches")
                        lines.append(f"**Showing**: {data['count']} files\n")
                        
                        for i, file in enumerate(data['files'], 1):
                            lines.append(f"{i}. **{file['file_path']}** ({file['language']})")
                            lines.append(f"   Score: {file['score']:.2f}")
                            if file['highlights']:
                                lines.append(f"   Preview: ...{file['highlights'][0]}...")
                            lines.append("")
                        
                        return {
                            "response": "\n".join(lines),
                            "type": "code_search",
                            "total": data['total']
                        }
                except Exception as e:
                    return {
                        "response": f"❌ Failed to search code: {str(e)}",
                        "type": "error"
                    }
    
    # Check for incident registration
    if any(keyword in message for keyword in ['register incident', 'create incident', 'new incident', 'report incident', 'create an incident']):
        # Try to extract incident details from natural language
        import re
        
        # Extract service name
        services = ['api-gateway', 'auth-service', 'payment-service', 'user-service', 
                   'order-service', 'inventory-service', 'notification-service',
                   'database', 'cache', 'frontend', 'readme', 'documentation']
        
        service = None
        for svc in services:
            if svc in message or svc.replace('-', ' ') in message:
                service = svc
                break
        
        # Extract severity
        severity = 'Sev-3'  # Default
        if 'sev-1' in message or 'critical' in message or 'severe' in message:
            severity = 'Sev-1'
        elif 'sev-2' in message or 'high' in message or 'important' in message:
            severity = 'Sev-2'
        
        # If we have enough info, register the incident
        if service or 'readme' in message or 'github' in message or 'codebase' in message:
            # Determine service from context
            if not service:
                if 'readme' in message or 'documentation' in message:
                    service = 'documentation'
                elif 'github' in message or 'codebase' in message:
                    service = 'code-repository'
                else:
                    service = 'general'
            
            # Create incident via API
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    # Extract title and description from message
                    title = message[:100] if len(message) < 100 else message[:97] + '...'
                    
                    response = await client.post(
                        "http://localhost:8001/api/incidents/register",
                        json={
                            "title": title,
                            "service": service,
                            "severity": severity,
                            "description": message,
                            "region": "us-west-1"
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        incident_id = data['incident_id']
                        
                        lines = [f"# ✅ Incident Registered: {incident_id}\n"]
                        lines.append(f"**Service**: {service}")
                        lines.append(f"**Severity**: {severity}")
                        lines.append(f"**Status**: investigating\n")
                        lines.append("## Next Steps")
                        lines.append(f"- View details: `Show incident {incident_id}`")
                        lines.append(f"- Trigger autonomous fix: `Fix incident {incident_id}`")
                        lines.append(f"- Analyze metrics: `Analyze metrics for {service}`")
                        
                        return {
                            "response": "\n".join(lines),
                            "type": "incident_registered",
                            "incident_id": incident_id
                        }
                except Exception as e:
                    return {
                        "response": f"❌ Failed to register incident: {str(e)}",
                        "type": "error"
                    }
        else:
            return {
                "response": """# 📝 Register New Incident

To register a new incident, provide:
- Service name (e.g., api-gateway, payment-service, documentation)
- Severity (Sev-1, Sev-2, or Sev-3)
- Description of the issue

**Example**:
```
Create a Sev-2 incident for payment-service with high latency
```

Try again with more details!""",
                "type": "help"
            }
    
    # Check for workflow trigger
    if any(keyword in message for keyword in ['fix incident', 'resolve incident', 'auto fix', 'trigger workflow']):
        # Extract incident ID
        incident_match = re.search(r'INC-\d+', message.upper())
        
        if incident_match:
            incident_id = incident_match.group(0)
            
            # Trigger autonomous workflow
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    response = await client.post(
                        "http://localhost:8001/api/incidents/trigger_workflow",
                        json={
                            "incident_id": incident_id,
                            "auto_approve": True
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Format workflow response
                        lines = [f"# 🤖 Autonomous Workflow: {incident_id}\n"]
                        lines.append("## Workflow Execution\n")
                        
                        for step in data['workflow_steps']:
                            status_icon = "✅" if step['status'] == 'completed' else "❌" if step['status'] == 'failed' else "⏭️" if step['status'] == 'skipped' else "⏳"
                            lines.append(f"{status_icon} **Step {step['step']}: {step['name']}**")
                            
                            if step['status'] == 'completed':
                                lines.append(f"   {step.get('result', 'Completed')}")
                                if step.get('pr_url'):
                                    lines.append(f"   PR: {step['pr_url']}")
                            elif step['status'] == 'failed':
                                lines.append(f"   Error: {step.get('error', 'Unknown error')}")
                            elif step['status'] == 'skipped':
                                lines.append(f"   {step.get('message', 'Skipped')}")
                            
                            lines.append("")
                        
                        lines.append(f"\n## Summary")
                        summary = data['summary']
                        lines.append(f"- Total Steps: {summary['total_steps']}")
                        lines.append(f"- Completed: {summary['completed']} ✅")
                        lines.append(f"- Failed: {summary['failed']} ❌")
                        lines.append(f"- Skipped: {summary['skipped']} ⏭️")
                        
                        if data.get('pr_url'):
                            lines.append(f"\n🔗 **Pull Request**: {data['pr_url']}")
                            lines.append("\n✅ **Next Steps**: Review and approve the PR for deployment")
                        
                        return {
                            "response": "\n".join(lines),
                            "type": "workflow_execution",
                            "incident_id": incident_id,
                            "workflow_data": data
                        }
                except Exception as e:
                    return {
                        "response": f"❌ Failed to trigger workflow: {str(e)}",
                        "type": "error"
                    }
        else:
            return {
                "response": "Please specify an incident ID. Example: `Fix incident INC-0063`",
                "type": "error"
            }
    
    # Detect analysis requests
    if any(keyword in message for keyword in ['analyze', 'analysis', 'metrics', 'check', 'show me']):
        # Extract service name
        services = ['api-gateway', 'auth-service', 'payment-service', 'user-service', 
                   'order-service', 'inventory-service', 'notification-service',
                   'database', 'cache', 'frontend']
        
        service = None
        for svc in services:
            if svc in message or svc.replace('-', ' ') in message:
                service = svc
                break
        
        if service:
            # Call rich analysis API
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.post(
                        "http://localhost:8001/api/analysis/service_metrics",
                        json={"service": service, "hours": 24}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            "response": data['analysis'],
                            "type": "rich_analysis",
                            "service": service,
                            "raw_data": data.get('raw_data', {}),
                            "anomaly_count": data.get('anomaly_count', 0)
                        }
                except Exception as e:
                    pass
    
    # Check for service health comparison
    if any(keyword in message for keyword in ['compare', 'health', 'all services', 'which service']):
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get("http://localhost:8001/api/analysis/service_health")
                
                if response.status_code == 200:
                    data = response.json()
                    services = data['services']
                    
                    # Format response
                    lines = ["# 🏥 Service Health Comparison\n"]
                    lines.append("## Services Ranked by Error Rate (Worst First)\n")
                    
                    for i, svc in enumerate(services[:10], 1):
                        status = "🚨" if svc['error_rate'] > 2 else "⚠️" if svc['error_rate'] > 1 else "✅"
                        lines.append(f"{i}. **{svc['service']}** {status}")
                        lines.append(f"   - Error Rate: {svc['error_rate']:.2f}%")
                        lines.append(f"   - Latency: {svc['latency']:.2f}ms")
                        lines.append(f"   - CPU: {svc['cpu']:.2f}%\n")
                    
                    return {
                        "response": "\n".join(lines),
                        "type": "service_comparison",
                        "services": services
                    }
            except Exception as e:
                pass
    
    # For everything else, use the actual AI agent (not hardcoded responses)
    # This makes it truly adaptive and intelligent
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                "http://localhost:8001/api/agent/chat",
                json=request.dict()
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "response": "I'm having trouble processing your request. Please try rephrasing.",
                    "type": "error"
                }
        except Exception as e:
            return {
                "response": f"Error: {str(e)}",
                "type": "error"
            }
    
    # Check for incident details
    if any(keyword in message for keyword in ['incident', 'inc-']):
        # Extract incident ID
        import re
        incident_match = re.search(r'INC-\d+', message.upper())
        
        if incident_match:
            incident_id = incident_match.group(0)
            
            # Query Elasticsearch directly
            from elasticsearch import Elasticsearch
            from app.core.config import settings
            
            es = Elasticsearch(
                hosts=[settings.elasticsearch_url],
                api_key=settings.elasticsearch_api_key,
                verify_certs=True
            )
            
            try:
                result = es.search(
                    index='incident-history',
                    body={
                        'query': {'term': {'id': incident_id}},
                        'size': 1
                    }
                )
                
                if result['hits']['hits']:
                    incident = result['hits']['hits'][0]['_source']
                    
                    # Check if this is a basic incident (3 digits) or detailed incident (4 digits)
                    is_basic = len(incident_id.split('-')[1]) == 3
                    
                    # Format rich incident details
                    lines = [f"# 🚨 Incident Details: {incident_id}\n"]
                    lines.append(f"**Title**: {incident.get('title', 'N/A')}")
                    lines.append(f"**Service**: {incident.get('service', 'N/A')}")
                    lines.append(f"**Severity**: {incident.get('severity', 'N/A')}")
                    lines.append(f"**Status**: {incident.get('status', 'N/A')}")
                    lines.append(f"**Region**: {incident.get('region', 'N/A')}")
                    lines.append(f"**Created**: {incident.get('created_at', 'N/A')}")
                    
                    if incident.get('resolved_at'):
                        lines.append(f"**Resolved**: {incident['resolved_at']}")
                        lines.append(f"**MTTR**: {incident.get('mttr_minutes', 0)} minutes")
                    
                    lines.append(f"\n**Description**: {incident.get('description', 'N/A')}\n")
                    
                    # Anomaly details
                    if 'anomaly' in incident:
                        anom = incident['anomaly']
                        lines.append("## 📊 Anomaly Details")
                        lines.append(f"- **Metric**: {anom.get('metric', 'N/A')}")
                        lines.append(f"- **Current Value**: {anom.get('current_value', 0):.2f}")
                        lines.append(f"- **Expected Value**: {anom.get('expected_value', 0):.2f}")
                        lines.append(f"- **Deviation**: {anom.get('deviation_sigma', 0):.1f}σ")
                        lines.append(f"- **Detected At**: {anom.get('detected_at', 'N/A')}\n")
                    
                    # Diagnosis
                    if 'diagnosis' in incident:
                        diag = incident['diagnosis']
                        lines.append("## 🔍 Diagnosis")
                        lines.append(f"- **Root Cause**: {diag.get('root_cause', 'N/A')}")
                        lines.append(f"- **Affected Component**: {diag.get('affected_component', 'N/A')}")
                        lines.append(f"- **Impact**: {diag.get('impact_explanation', 'N/A')}")
                        lines.append(f"- **Confidence**: {diag.get('confidence', 0):.0%}")
                        
                        if 'correlated_metrics' in diag:
                            lines.append(f"- **Correlated Metrics**: {', '.join(diag['correlated_metrics'])}\n")
                    
                    # Remediation
                    if 'remediation' in incident:
                        rem = incident['remediation']
                        lines.append("## 🔧 Remediation")
                        lines.append(f"- **File**: `{rem.get('file_path', 'N/A')}`")
                        lines.append(f"- **Fix**: {rem.get('explanation', 'N/A')}")
                        
                        if rem.get('pr_url'):
                            lines.append(f"- **PR**: {rem['pr_url']}\n")
                    
                    # Tags
                    if 'tags' in incident:
                        tags = incident['tags']
                        lines.append("## 🏷️ Tags")
                        lines.append(f"- Auto-detected: {'✅' if tags.get('auto_detected') else '❌'}")
                        lines.append(f"- Has Runbook: {'✅' if tags.get('has_runbook') else '❌'}")
                        lines.append(f"- Customer Impact: {tags.get('customer_impact', 'unknown')}")
                    
                    # Add helpful note for basic incidents
                    if is_basic and not ('diagnosis' in incident or 'remediation' in incident):
                        lines.append("\n---")
                        lines.append("\n💡 **Note**: This is a basic incident record with limited details.")
                        lines.append("For comprehensive incident analysis including diagnosis, remediation, and tags, try:")
                        lines.append(f"- `Show incident INC-0{incident_id.split('-')[1]}` (4-digit format)")
                        lines.append("- Example: `Show incident INC-0001` through `INC-1000`")
                    
                    return {
                        "response": "\n".join(lines),
                        "type": "incident_details",
                        "incident": incident
                    }
            except Exception as e:
                pass
    
    # Check for incident statistics
    if any(keyword in message for keyword in ['incident', 'statistics', 'stats', 'mttr']):
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get("http://localhost:8001/api/analysis/incident_stats")
                
                if response.status_code == 200:
                    data = response.json()
                    stats = data['statistics'][:10]
                    
                    lines = ["# 📊 Incident Statistics by Service\n"]
                    
                    for i, stat in enumerate(stats, 1):
                        lines.append(f"{i}. **{stat['service']}**")
                        lines.append(f"   - Total Incidents: {stat['total_incidents']}")
                        lines.append(f"   - Sev-1: {stat['sev1_count']} | Sev-2: {stat['sev2_count']} | Sev-3: {stat['sev3_count']}")
                        lines.append(f"   - Avg MTTR: {stat['avg_mttr_minutes']:.1f} minutes\n")
                    
                    return {
                        "response": "\n".join(lines),
                        "type": "incident_stats",
                        "statistics": stats
                    }
            except Exception as e:
                pass
    
    # Fall back to regular agent
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                "http://localhost:8001/api/agent/chat",
                json=request.dict()
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "response": "I'm having trouble processing your request. Please try rephrasing or ask about:\n- Analyzing metrics for a service\n- Comparing service health\n- Viewing active anomalies\n- Incident statistics",
                    "type": "error"
                }
        except Exception as e:
            return {
                "response": f"Error: {str(e)}",
                "type": "error"
            }
