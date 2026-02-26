"""
GitHub Integration API - View, download, and sync files to Elasticsearch
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from github import Github
from elasticsearch import Elasticsearch
from app.core.config import settings
import base64
import logging

router = APIRouter(prefix="/api/github", tags=["github"])
logger = logging.getLogger(__name__)


class ViewFileRequest(BaseModel):
    file_path: str
    branch: Optional[str] = "main"


class SyncFilesRequest(BaseModel):
    file_paths: Optional[List[str]] = None  # If None, sync all
    branch: Optional[str] = "main"
    force: bool = False
    owner: Optional[str] = None  # Repository owner (defaults to configured)
    repo: Optional[str] = None  # Repository name (defaults to configured)


def get_github_client():
    """Get GitHub client"""
    if not settings.github_token:
        raise HTTPException(status_code=503, detail="GitHub not configured")
    return Github(settings.github_token)


def get_es_client():
    """Get Elasticsearch client"""
    return Elasticsearch(
        hosts=[settings.elasticsearch_url],
        api_key=settings.elasticsearch_api_key,
        verify_certs=True
    )


@router.get("/repositories")
async def list_user_repositories(limit: int = 100):
    """
    List all accessible repositories for the authenticated user
    """
    try:
        github = get_github_client()
        user = github.get_user()
        
        repos = []
        for repo in user.get_repos()[:limit]:
            repos.append({
                "name": repo.name,
                "full_name": repo.full_name,
                "owner": repo.owner.login,
                "description": repo.description,
                "language": repo.language,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "url": repo.html_url,
                "private": repo.private,
                "default_branch": repo.default_branch,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None
            })
        
        return {
            "success": True,
            "count": len(repos),
            "repositories": repos
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list repositories: {str(e)}")


@router.get("/files")
async def list_repository_files(
    path: str = "", 
    branch: str = "main",
    owner: Optional[str] = None,
    repo: Optional[str] = None
):
    """
    List files in GitHub repository (supports any accessible repo)
    """
    try:
        github = get_github_client()
        
        # Use specified repo or default to configured one
        if owner and repo:
            full_repo = f"{owner}/{repo}"
        else:
            full_repo = f"{settings.github_owner}/{settings.github_repo}"
        
        repository = github.get_repo(full_repo)
        
        contents = repository.get_contents(path, ref=branch)
        
        files = []
        if not isinstance(contents, list):
            contents = [contents]
        
        for content in contents:
            files.append({
                "name": content.name,
                "path": content.path,
                "type": content.type,
                "size": content.size,
                "sha": content.sha,
                "url": content.html_url
            })
        
        return {
            "success": True,
            "repository": full_repo,
            "path": path,
            "branch": branch,
            "count": len(files),
            "files": files
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.post("/view_file")
async def view_file(request: ViewFileRequest):
    """
    View file content from GitHub
    """
    try:
        github = get_github_client()
        repo = github.get_repo(f"{settings.github_owner}/{settings.github_repo}")
        
        file_content = repo.get_contents(request.file_path, ref=request.branch)
        
        # Decode content
        if file_content.encoding == "base64":
            content = base64.b64decode(file_content.content).decode('utf-8')
        else:
            content = file_content.content
        
        return {
            "success": True,
            "file_path": request.file_path,
            "branch": request.branch,
            "size": file_content.size,
            "sha": file_content.sha,
            "content": content,
            "url": file_content.html_url,
            "last_modified": file_content.last_modified
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to view file: {str(e)}")


@router.post("/sync_to_elasticsearch")
async def sync_files_to_elasticsearch(request: SyncFilesRequest):
    """
    Download files from GitHub and upload to Elasticsearch code-repository index
    Supports syncing from any accessible repository
    """
    try:
        github = get_github_client()
        
        # Use specified repo or default to configured one
        if request.owner and request.repo:
            repo_full_name = f"{request.owner}/{request.repo}"
        else:
            repo_full_name = f"{settings.github_owner}/{settings.github_repo}"
        
        logger.info(f"Syncing repository: {repo_full_name}")
        repo = github.get_repo(repo_full_name)
        es = get_es_client()
        
        synced_files = []
        errors = []
        
        # Get files to sync
        if request.file_paths:
            files_to_sync = request.file_paths
        else:
            # Get all files recursively
            files_to_sync = []
            contents = repo.get_contents("", ref=request.branch)
            
            while contents:
                file_content = contents.pop(0)
                if file_content.type == "dir":
                    contents.extend(repo.get_contents(file_content.path, ref=request.branch))
                else:
                    # Only sync code files
                    if any(file_content.name.endswith(ext) for ext in [
                        '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', 
                        '.rs', '.cpp', '.c', '.h', '.cs', '.rb', '.php',
                        '.md', '.txt', '.json', '.yaml', '.yml', '.toml',
                        '.sh', '.bash', '.sql', '.html', '.css', '.scss'
                    ]):
                        files_to_sync.append(file_content.path)
        
        logger.info(f"Syncing {len(files_to_sync)} files to Elasticsearch...")
        
        for file_path in files_to_sync:
            try:
                # Get file content from GitHub
                file_content = repo.get_contents(file_path, ref=request.branch)
                
                # Decode content
                if file_content.encoding == "base64":
                    content = base64.b64decode(file_content.content).decode('utf-8')
                else:
                    content = file_content.content
                
                # Determine language
                extension = file_path.split('.')[-1] if '.' in file_path else 'unknown'
                language_map = {
                    'py': 'python', 'js': 'javascript', 'ts': 'typescript',
                    'tsx': 'typescript', 'jsx': 'javascript', 'java': 'java',
                    'go': 'go', 'rs': 'rust', 'cpp': 'cpp', 'c': 'c',
                    'cs': 'csharp', 'rb': 'ruby', 'php': 'php',
                    'md': 'markdown', 'json': 'json', 'yaml': 'yaml',
                    'yml': 'yaml', 'sh': 'bash', 'sql': 'sql',
                    'html': 'html', 'css': 'css'
                }
                language = language_map.get(extension, extension)
                
                # Extract service name from path
                service = 'general'
                if '/' in file_path:
                    parts = file_path.split('/')
                    if len(parts) > 1:
                        service = parts[0].replace('_', '-')
                
                # Create document for Elasticsearch
                doc = {
                    "file_path": file_path,
                    "file_name": file_content.name,
                    "content": content,
                    "language": language,
                    "service": service,
                    "repository": repo_full_name,  # Track which repo this came from
                    "size": file_content.size,
                    "sha": file_content.sha,
                    "github_url": file_content.html_url,
                    "branch": request.branch,
                    "synced_at": datetime.utcnow().isoformat(),
                    "last_modified": file_content.last_modified.isoformat() if hasattr(file_content.last_modified, 'isoformat') else str(file_content.last_modified) if file_content.last_modified else None
                }
                
                # Check if file already exists
                existing = es.search(
                    index='code-repository',
                    body={
                        'query': {
                            'bool': {
                                'must': [
                                    {'term': {'file_path': file_path}},
                                    {'term': {'repository': repo_full_name}}
                                ]
                            }
                        },
                        'size': 1
                    }
                )
                
                if existing['hits']['hits'] and not request.force:
                    # Update existing
                    doc_id = existing['hits']['hits'][0]['_id']
                    es.update(
                        index='code-repository',
                        id=doc_id,
                        body={'doc': doc}
                    )
                else:
                    # Create new
                    es.index(
                        index='code-repository',
                        document=doc
                    )
                
                synced_files.append({
                    "file_path": file_path,
                    "size": file_content.size,
                    "language": language,
                    "service": service,
                    "repository": repo_full_name
                })
                
            except Exception as e:
                logger.error(f"Failed to sync {file_path}: {e}")
                errors.append({
                    "file_path": file_path,
                    "error": str(e)
                })
        
        # Refresh index
        es.indices.refresh(index='code-repository')
        
        return {
            "success": True,
            "repository": repo_full_name,
            "synced_count": len(synced_files),
            "error_count": len(errors),
            "synced_files": synced_files,
            "errors": errors,
            "synced_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync files: {str(e)}")


@router.get("/search_code")
async def search_code_in_elasticsearch(
    query: str,
    service: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 10
):
    """
    Search code in Elasticsearch
    """
    try:
        es = get_es_client()
        
        # Build query
        must_clauses = []
        
        # Text search
        must_clauses.append({
            "multi_match": {
                "query": query,
                "fields": ["content", "file_path", "file_name"],
                "type": "best_fields"
            }
        })
        
        # Filter by service
        if service:
            must_clauses.append({"term": {"service": service}})
        
        # Filter by language
        if language:
            must_clauses.append({"term": {"language": language}})
        
        result = es.search(
            index='code-repository',
            body={
                'query': {
                    'bool': {
                        'must': must_clauses
                    }
                },
                'size': limit,
                'highlight': {
                    'fields': {
                        'content': {
                            'fragment_size': 150,
                            'number_of_fragments': 3
                        }
                    }
                }
            }
        )
        
        files = []
        for hit in result['hits']['hits']:
            source = hit['_source']
            files.append({
                "file_path": source['file_path'],
                "file_name": source['file_name'],
                "language": source['language'],
                "service": source['service'],
                "size": source['size'],
                "github_url": source.get('github_url'),
                "score": hit['_score'],
                "highlights": hit.get('highlight', {}).get('content', [])
            })
        
        return {
            "success": True,
            "query": query,
            "total": result['hits']['total']['value'],
            "count": len(files),
            "files": files
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search code: {str(e)}")


@router.get("/stats")
async def get_code_repository_stats():
    """
    Get statistics about code repository in Elasticsearch
    """
    try:
        es = get_es_client()
        
        # Total files
        total = es.count(index='code-repository')
        
        # By language
        lang_agg = es.search(
            index='code-repository',
            body={
                'size': 0,
                'aggs': {
                    'languages': {
                        'terms': {'field': 'language', 'size': 20}
                    }
                }
            }
        )
        
        # By service
        service_agg = es.search(
            index='code-repository',
            body={
                'size': 0,
                'aggs': {
                    'services': {
                        'terms': {'field': 'service', 'size': 20}
                    }
                }
            }
        )
        
        return {
            "success": True,
            "total_files": total['count'],
            "by_language": [
                {"language": b['key'], "count": b['doc_count']}
                for b in lang_agg['aggregations']['languages']['buckets']
            ],
            "by_service": [
                {"service": b['key'], "count": b['doc_count']}
                for b in service_agg['aggregations']['services']['buckets']
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
