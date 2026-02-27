"""
Observer Engine API - Endpoints for monitoring and workflow management
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.services.observer_engine import observer_engine
from elasticsearch import Elasticsearch
from app.core.config import settings
from datetime import datetime

router = APIRouter(prefix="/api/observer", tags=["observer"])

es = Elasticsearch(
    hosts=[settings.elasticsearch_url],
    api_key=settings.elasticsearch_api_key,
    verify_certs=True
)


class WorkflowApprovalRequest(BaseModel):
    workflow_id: str
    approved: bool
    reason: Optional[str] = None


@router.get("/status")
async def get_observer_status():
    """Get current observer engine status"""
    try:
        status = await observer_engine.get_monitoring_status()
        return {
            "success": True,
            **status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_observer():
    """Start the observer engine"""
    try:
        if not observer_engine.running:
            # Start in background
            import asyncio
            asyncio.create_task(observer_engine.start())
            return {
                "success": True,
                "message": "Observer engine started",
                "status": "running"
            }
        else:
            return {
                "success": True,
                "message": "Observer engine already running",
                "status": "running"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_observer():
    """Stop the observer engine"""
    try:
        observer_engine.stop()
        return {
            "success": True,
            "message": "Observer engine stopped",
            "status": "stopped"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anomalies")
async def get_recent_anomalies():
    """Get recent anomalies detected by the observer"""
    try:
        result = es.search(
            index="metrics",
            body={
                "query": {"term": {"is_anomaly": True}},
                "sort": [{"@timestamp": "desc"}],
                "size": 20
            }
        )
        
        anomalies = []
        for hit in result['hits']['hits']:
            anomaly = hit['_source']
            anomalies.append(anomaly)
        
        return {
            "success": True,
            "count": len(anomalies),
            "anomalies": anomalies
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/pending")
async def get_pending_workflows():
    """Get workflows awaiting approval"""
    try:
        result = es.search(
            index="pending-workflows",
            body={
                "query": {"term": {"status": "pending_approval"}},
                "sort": [{"created_at": "desc"}],
                "size": 10
            }
        )
        
        workflows = []
        for hit in result['hits']['hits']:
            workflow = hit['_source']
            workflow['_id'] = hit['_id']
            workflows.append(workflow)
        
        return {
            "success": True,
            "count": len(workflows),
            "workflows": workflows
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/approve")
async def approve_workflow(request: WorkflowApprovalRequest):
    """
    Approve or reject a pending workflow
    
    If approved, triggers the autonomous incident response
    """
    try:
        # Get the workflow
        workflow_result = es.search(
            index="pending-workflows",
            body={
                "query": {"term": {"id": request.workflow_id}},
                "size": 1
            }
        )
        
        if not workflow_result['hits']['hits']:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        workflow = workflow_result['hits']['hits'][0]['_source']
        workflow_doc_id = workflow_result['hits']['hits'][0]['_id']
        
        if request.approved:
            # Update workflow status
            es.update(
                index="pending-workflows",
                id=workflow_doc_id,
                body={
                    "doc": {
                        "status": "approved",
                        "approved_at": datetime.utcnow().isoformat(),
                        "approval_reason": request.reason
                    }
                },
                refresh=True
            )
            
            # Trigger autonomous incident response
            anomaly = workflow['anomaly']
            
            # Call the agent to handle this
            import httpx
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "http://localhost:8001/api/agent/chat_with_reasoning",
                    json={
                        "message": f"URGENT: Anomaly detected in {anomaly['service']}.{anomaly['metric']}. "
                                 f"Current value: {anomaly['current_value']} "
                                 f"(baseline: {anomaly['baseline_mean']} ± {anomaly['baseline_std']}). "
                                 f"Deviation: {anomaly['sigma_deviation']}σ. "
                                 f"Investigate, fix, create PR, alert team, and create Jira ticket.",
                        "conversation_history": []
                    }
                )
                
                agent_response = response.json()
            
            return {
                "success": True,
                "message": "Workflow approved and executed",
                "workflow_id": request.workflow_id,
                "agent_response": agent_response.get('response', 'Workflow initiated')
            }
        else:
            # Reject workflow
            es.update(
                index="pending-workflows",
                id=workflow_doc_id,
                body={
                    "doc": {
                        "status": "rejected",
                        "rejected_at": datetime.utcnow().isoformat(),
                        "rejection_reason": request.reason
                    }
                },
                refresh=True
            )
            
            return {
                "success": True,
                "message": "Workflow rejected",
                "workflow_id": request.workflow_id
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/github/activity")
async def get_github_activity():
    """Get recent GitHub activity"""
    try:
        activity = await observer_engine.check_github_activity()
        return {
            "success": True,
            "count": len(activity),
            "activity": activity
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/github/suspect-commits")
async def identify_suspect_commits(
    service: str,
    anomaly_timestamp: str
):
    """
    Identify suspect commits that may have caused an anomaly
    
    Correlates anomaly timestamp with recent commits
    """
    try:
        from datetime import datetime, timedelta
        import httpx
        
        anomaly_time = datetime.fromisoformat(anomaly_timestamp.replace('Z', '+00:00'))
        
        # Look for commits in the 2 hours before the anomaly
        search_start = anomaly_time - timedelta(hours=2)
        
        suspects = []
        
        if settings.github_token:
            async with httpx.AsyncClient(timeout=30.0) as client:
                commits_url = f"https://api.github.com/repos/{settings.github_owner}/{settings.github_repo}/commits"
                response = await client.get(
                    commits_url,
                    headers={
                        "Authorization": f"token {settings.github_token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    params={
                        "since": search_start.isoformat(),
                        "until": anomaly_time.isoformat()
                    }
                )
                
                if response.status_code == 200:
                    commits = response.json()
                    
                    for commit in commits:
                        commit_time = datetime.fromisoformat(
                            commit['commit']['author']['date'].replace('Z', '+00:00')
                        )
                        
                        # Calculate time delta
                        time_delta = (anomaly_time - commit_time).total_seconds() / 60  # minutes
                        
                        suspects.append({
                            "sha": commit['sha'][:7],
                            "full_sha": commit['sha'],
                            "message": commit['commit']['message'].split('\n')[0],
                            "author": commit['commit']['author']['name'],
                            "timestamp": commit['commit']['author']['date'],
                            "minutes_before_anomaly": round(time_delta, 1),
                            "url": commit['html_url'],
                            "suspicion_score": max(0, 100 - time_delta)  # Higher score = closer to anomaly
                        })
                    
                    # Sort by suspicion score
                    suspects.sort(key=lambda x: x['suspicion_score'], reverse=True)
        
        return {
            "success": True,
            "service": service,
            "anomaly_timestamp": anomaly_timestamp,
            "search_window_hours": 2,
            "suspect_commits": suspects,
            "most_likely_suspect": suspects[0] if suspects else None
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
