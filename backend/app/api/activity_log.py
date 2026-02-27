"""
Activity Log API - Track all agent interactions and actions

Logs all agent activities including:
- Chat interactions
- GitHub PRs created
- Code commits
- Jira tickets created
- Slack alerts sent
- Incidents registered
- Workflows executed
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from app.core.config import settings

router = APIRouter(prefix="/api/activity", tags=["activity-log"])

es = Elasticsearch(
    hosts=[settings.elasticsearch_url],
    api_key=settings.elasticsearch_api_key,
    verify_certs=True
)


class ActivityLogEntry(BaseModel):
    timestamp: str
    type: str  # chat, pr_created, jira_created, slack_sent, incident_registered, workflow_executed
    user: Optional[str] = None
    summary: str
    details: Dict[str, Any]
    status: str  # success, failed, pending
    metadata: Optional[Dict[str, Any]] = None


async def log_activity(
    activity_type: str,
    summary: str,
    details: Dict[str, Any],
    status: str = "success",
    user: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Log an activity to Elasticsearch
    
    This is called by other services to track actions
    """
    try:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": activity_type,
            "user": user or "system",
            "summary": summary,
            "details": details,
            "status": status,
            "metadata": metadata or {}
        }
        
        es.index(
            index="activity-log",
            document=entry,
            refresh=True
        )
        
    except Exception as e:
        print(f"Error logging activity: {e}")


@router.get("/recent")
async def get_recent_activities(
    limit: int = 50,
    activity_type: Optional[str] = None,
    hours: int = 24
):
    """
    Get recent activities
    
    Args:
        limit: Maximum number of activities to return
        activity_type: Filter by type (chat, pr_created, etc.)
        hours: Look back this many hours
    """
    try:
        now = datetime.utcnow()
        start_time = now - timedelta(hours=hours)
        
        query = {
            "bool": {
                "must": [
                    {"range": {"timestamp": {"gte": start_time.isoformat()}}}
                ]
            }
        }
        
        if activity_type:
            query["bool"]["must"].append({"term": {"type": activity_type}})
        
        result = es.search(
            index="activity-log",
            body={
                "query": query,
                "sort": [{"timestamp": "desc"}],
                "size": limit
            }
        )
        
        activities = []
        for hit in result['hits']['hits']:
            activity = hit['_source']
            activity['_id'] = hit['_id']
            activities.append(activity)
        
        return {
            "success": True,
            "count": len(activities),
            "activities": activities
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_activity_stats(hours: int = 24):
    """Get activity statistics"""
    try:
        now = datetime.utcnow()
        start_time = now - timedelta(hours=hours)
        
        result = es.search(
            index="activity-log",
            body={
                "query": {
                    "range": {"timestamp": {"gte": start_time.isoformat()}}
                },
                "size": 0,
                "aggs": {
                    "by_type": {
                        "terms": {"field": "type", "size": 20}
                    },
                    "by_status": {
                        "terms": {"field": "status", "size": 10}
                    },
                    "by_hour": {
                        "date_histogram": {
                            "field": "timestamp",
                            "fixed_interval": "1h"
                        }
                    }
                }
            }
        )
        
        stats = {
            "total": result['hits']['total']['value'],
            "by_type": {},
            "by_status": {},
            "timeline": []
        }
        
        for bucket in result['aggregations']['by_type']['buckets']:
            stats['by_type'][bucket['key']] = bucket['doc_count']
        
        for bucket in result['aggregations']['by_status']['buckets']:
            stats['by_status'][bucket['key']] = bucket['doc_count']
        
        for bucket in result['aggregations']['by_hour']['buckets']:
            stats['timeline'].append({
                "timestamp": bucket['key_as_string'],
                "count": bucket['doc_count']
            })
        
        return {
            "success": True,
            "time_range_hours": hours,
            "stats": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/github")
async def get_github_activities(limit: int = 20):
    """Get GitHub-related activities (PRs, commits)"""
    try:
        result = es.search(
            index="activity-log",
            body={
                "query": {
                    "terms": {"type": ["pr_created", "commit_pushed"]}
                },
                "sort": [{"timestamp": "desc"}],
                "size": limit
            }
        )
        
        activities = []
        for hit in result['hits']['hits']:
            activity = hit['_source']
            activities.append(activity)
        
        return {
            "success": True,
            "count": len(activities),
            "activities": activities
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jira")
async def get_jira_activities(limit: int = 20):
    """Get Jira-related activities (tickets created)"""
    try:
        result = es.search(
            index="activity-log",
            body={
                "query": {"term": {"type": "jira_created"}},
                "sort": [{"timestamp": "desc"}],
                "size": limit
            }
        )
        
        activities = []
        for hit in result['hits']['hits']:
            activity = hit['_source']
            activities.append(activity)
        
        return {
            "success": True,
            "count": len(activities),
            "activities": activities
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/slack")
async def get_slack_activities(limit: int = 20):
    """Get Slack-related activities (alerts sent)"""
    try:
        result = es.search(
            index="activity-log",
            body={
                "query": {"term": {"type": "slack_sent"}},
                "sort": [{"timestamp": "desc"}],
                "size": limit
            }
        )
        
        activities = []
        for hit in result['hits']['hits']:
            activity = hit['_source']
            activities.append(activity)
        
        return {
            "success": True,
            "count": len(activities),
            "activities": activities
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows")
async def get_workflow_activities(limit: int = 20):
    """Get autonomous workflow executions"""
    try:
        result = es.search(
            index="activity-log",
            body={
                "query": {"term": {"type": "workflow_executed"}},
                "sort": [{"timestamp": "desc"}],
                "size": limit
            }
        )
        
        activities = []
        for hit in result['hits']['hits']:
            activity = hit['_source']
            activities.append(activity)
        
        return {
            "success": True,
            "count": len(activities),
            "activities": activities
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
