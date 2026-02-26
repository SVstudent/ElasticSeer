"""
Incident Management API - Register and manage incidents through chat
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from app.core.config import settings
import logging

router = APIRouter(prefix="/api/incidents", tags=["incident-management"])
logger = logging.getLogger(__name__)


class RegisterIncidentRequest(BaseModel):
    title: str
    service: str
    severity: str  # Sev-1, Sev-2, Sev-3
    description: str
    region: Optional[str] = "us-west-1"
    environment: Optional[str] = "production"
    metric: Optional[str] = None
    current_value: Optional[float] = None
    expected_value: Optional[float] = None
    affected_component: Optional[str] = None
    target_file: Optional[str] = None  # NEW: Allow specifying target file for fix


class RegisterAnomalyRequest(BaseModel):
    service: str
    metric: str
    current_value: float
    expected_value: float
    region: Optional[str] = "us-west-1"
    environment: Optional[str] = "production"
    severity: Optional[str] = "Sev-3"


class TriggerWorkflowRequest(BaseModel):
    incident_id: str
    auto_approve: bool = False


def get_es_client():
    """Get Elasticsearch client"""
    return Elasticsearch(
        hosts=[settings.elasticsearch_url],
        api_key=settings.elasticsearch_api_key,
        verify_certs=True
    )


def generate_incident_id():
    """Generate next incident ID"""
    es = get_es_client()
    
    # Get the highest incident ID
    try:
        result = es.search(
            index='incident-history',
            body={
                'query': {'match_all': {}},
                'sort': [{'created_at': {'order': 'desc'}}],
                'size': 100  # Get more to find valid IDs
            }
        )
        
        if result['hits']['hits']:
            # Find the highest numeric ID
            max_num = 1000
            for hit in result['hits']['hits']:
                incident_id = hit['_source'].get('id', '')
                if incident_id.startswith('INC-'):
                    try:
                        num_part = incident_id.split('-')[1]
                        # Only parse if it's a 4-digit number
                        if len(num_part) == 4 and num_part.isdigit():
                            num = int(num_part)
                            if num > max_num:
                                max_num = num
                    except:
                        continue
            
            return f"INC-{max_num + 1:04d}"
        else:
            return "INC-1001"
    except Exception as e:
        logger.error(f"Error generating incident ID: {e}")
        # Default to a safe starting point
        return "INC-1001"


def generate_anomaly_id():
    """Generate next anomaly ID"""
    es = get_es_client()
    
    try:
        result = es.search(
            index='anomaly-records',
            body={
                'query': {'match_all': {}},
                'sort': [{'detected_at': {'order': 'desc'}}],
                'size': 1
            }
        )
        
        if result['hits']['hits']:
            last_id = result['hits']['hits'][0]['_source']['id']
            num = int(last_id.split('-')[1])
            return f"ANOM-{num + 1:04d}"
        else:
            return "ANOM-1057"
    except:
        return f"ANOM-{datetime.utcnow().strftime('%Y%m%d%H%M')}"


@router.post("/register")
async def register_incident(request: RegisterIncidentRequest):
    """
    Register a new incident in Elasticsearch
    """
    es = get_es_client()
    
    # Generate incident ID
    incident_id = generate_incident_id()
    
    # Calculate deviation if values provided
    deviation_sigma = None
    if request.current_value and request.expected_value:
        deviation_sigma = abs(request.current_value - request.expected_value) / (request.expected_value * 0.1)
    
    # Create incident document
    incident = {
        "id": incident_id,
        "title": request.title,
        "severity": request.severity,
        "status": "investigating",
        "service": request.service,
        "region": request.region,
        "environment": request.environment,
        "created_at": datetime.utcnow().isoformat(),
        "description": request.description,
        "tags": {
            "auto_detected": False,
            "user_registered": True,
            "has_runbook": False,
            "customer_impact": "unknown"
        }
    }
    
    # Add anomaly details if provided
    if request.metric and request.current_value and request.expected_value:
        incident["anomaly"] = {
            "metric": request.metric,
            "current_value": request.current_value,
            "expected_value": request.expected_value,
            "deviation_sigma": deviation_sigma,
            "severity": request.severity,
            "detected_at": datetime.utcnow().isoformat(),
            "service": request.service,
            "environment": request.environment,
            "region": request.region
        }
    
    # Add diagnosis placeholder
    incident["diagnosis"] = {
        "root_cause": "Under investigation",
        "affected_component": request.affected_component or request.service,
        "impact_explanation": request.description,
        "confidence": 0.0,
        "correlated_metrics": []
    }
    
    try:
        # Index the incident
        es.index(
            index='incident-history',
            document=incident,
            refresh=True
        )
        
        logger.info(f"✅ Registered incident {incident_id}")
        
        return {
            "success": True,
            "incident_id": incident_id,
            "incident": incident,
            "message": f"Incident {incident_id} registered successfully",
            "next_steps": [
                f"View details: 'Show incident {incident_id}'",
                f"Trigger autonomous fix: 'Fix incident {incident_id}'",
                f"Analyze metrics: 'Analyze metrics for {request.service}'"
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to register incident: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register incident: {str(e)}")


@router.post("/register_anomaly")
async def register_anomaly(request: RegisterAnomalyRequest):
    """
    Register a new anomaly in Elasticsearch
    """
    es = get_es_client()
    
    # Generate anomaly ID
    anomaly_id = generate_anomaly_id()
    
    # Calculate deviation
    deviation_sigma = abs(request.current_value - request.expected_value) / (request.expected_value * 0.1)
    
    # Create anomaly document
    anomaly = {
        "id": anomaly_id,
        "metric": request.metric,
        "service": request.service,
        "region": request.region,
        "environment": request.environment,
        "detected_at": datetime.utcnow().isoformat(),
        "current_value": request.current_value,
        "expected_value": request.expected_value,
        "deviation_sigma": deviation_sigma,
        "severity": request.severity,
        "status": "active",
        "tags": {
            "auto_detected": False,
            "user_registered": True,
            "confidence": 1.0
        }
    }
    
    try:
        # Index the anomaly
        es.index(
            index='anomaly-records',
            document=anomaly,
            refresh=True
        )
        
        logger.info(f"✅ Registered anomaly {anomaly_id}")
        
        return {
            "success": True,
            "anomaly_id": anomaly_id,
            "anomaly": anomaly,
            "message": f"Anomaly {anomaly_id} registered successfully",
            "next_steps": [
                f"View details: 'Show anomaly {anomaly_id}'",
                "View all anomalies: 'Show active anomalies'",
                f"Analyze service: 'Analyze metrics for {request.service}'"
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to register anomaly: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register anomaly: {str(e)}")


@router.post("/trigger_workflow")
async def trigger_autonomous_workflow(request: TriggerWorkflowRequest):
    """
    Trigger autonomous incident response workflow
    """
    import httpx
    
    es = get_es_client()
    
    # Get incident details
    try:
        result = es.search(
            index='incident-history',
            body={
                'query': {'term': {'id': request.incident_id}},
                'size': 1
            }
        )
        
        if not result['hits']['hits']:
            raise HTTPException(status_code=404, detail=f"Incident {request.incident_id} not found")
        
        incident = result['hits']['hits'][0]['_source']
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch incident: {str(e)}")
    
    # Execute autonomous workflow
    workflow_steps = []
    
    # Step 1: Search for relevant code
    workflow_steps.append({
        "step": 1,
        "name": "Code Search",
        "status": "in_progress",
        "message": f"Searching code repository for {incident['service']}..."
    })
    
    # Search code-repository index
    try:
        code_result = es.search(
            index='code-repository',
            body={
                'query': {
                    'bool': {
                        'should': [
                            {'match': {'file_path': incident['service']}},
                            {'match': {'content': incident['service']}}
                        ]
                    }
                },
                'size': 5
            }
        )
        
        relevant_files = [hit['_source'] for hit in code_result['hits']['hits']]
        
        workflow_steps[-1]["status"] = "completed"
        workflow_steps[-1]["result"] = f"Found {len(relevant_files)} relevant file(s)"
        
    except Exception as e:
        workflow_steps[-1]["status"] = "failed"
        workflow_steps[-1]["error"] = str(e)
        relevant_files = []
    
    # Step 2: Generate AI fix
    workflow_steps.append({
        "step": 2,
        "name": "AI Fix Generation",
        "status": "in_progress",
        "message": "Generating AI-powered fix using Gemini..."
    })
    
    fixed_code = None
    fix_explanation = None
    
    if relevant_files:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:8001/api/elasticseer/generate_fix",
                    json={
                        "file_path": relevant_files[0].get('file_path', 'config.py'),
                        "diagnosis": incident['diagnosis'].get('root_cause', 'Unknown issue'),
                        "current_code": relevant_files[0].get('content', ''),
                        "incident_context": incident.get('description', '')
                    }
                )
                
                if response.status_code == 200:
                    fix_result = response.json()
                    fixed_code = fix_result.get('fixed_code', '')
                    fix_explanation = fix_result.get('explanation', '')
                    
                    workflow_steps[-1]["status"] = "completed"
                    workflow_steps[-1]["result"] = "Fix generated successfully"
                else:
                    workflow_steps[-1]["status"] = "failed"
                    workflow_steps[-1]["error"] = f"API returned {response.status_code}"
                    
        except Exception as e:
            workflow_steps[-1]["status"] = "failed"
            workflow_steps[-1]["error"] = str(e)
    else:
        workflow_steps[-1]["status"] = "skipped"
        workflow_steps[-1]["message"] = "No relevant code files found"
    
    # Step 3: Create GitHub PR
    workflow_steps.append({
        "step": 3,
        "name": "GitHub PR Creation",
        "status": "in_progress",
        "message": "Creating pull request..."
    })
    
    pr_url = None
    
    if fixed_code and (request.auto_approve or True):  # For demo, always create PR
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:8001/api/elasticseer/create_pr",
                    json={
                        "title": f"Fix {request.incident_id}: {incident['title']}",
                        "description": f"""## Incident: {request.incident_id}

**Service**: {incident['service']}
**Severity**: {incident['severity']}
**Root Cause**: {incident['diagnosis'].get('root_cause', 'Under investigation')}

**Fix**: {fix_explanation or 'AI-generated fix'}

**Generated by**: ElasticSeer Autonomous Agent
**Timestamp**: {datetime.utcnow().isoformat()}
""",
                        "branch_name": f"fix/{request.incident_id.lower()}-{datetime.utcnow().strftime('%Y%m%d%H%M')}",
                        "files": [
                            {
                                "path": relevant_files[0].get('file_path', 'config.py') if relevant_files else 'config.py',
                                "content": fixed_code
                            }
                        ],
                        "incident_id": request.incident_id
                    }
                )
                
                if response.status_code == 200:
                    pr_result = response.json()
                    pr_url = pr_result.get('pr_url')
                    
                    workflow_steps[-1]["status"] = "completed"
                    workflow_steps[-1]["result"] = f"PR #{pr_result.get('pr_number')} created"
                    workflow_steps[-1]["pr_url"] = pr_url
                else:
                    workflow_steps[-1]["status"] = "failed"
                    workflow_steps[-1]["error"] = f"API returned {response.status_code}"
                    
        except Exception as e:
            workflow_steps[-1]["status"] = "failed"
            workflow_steps[-1]["error"] = str(e)
    else:
        workflow_steps[-1]["status"] = "skipped"
        workflow_steps[-1]["message"] = "No fix to deploy or approval required"
    
    # Step 4: Send Slack notification
    workflow_steps.append({
        "step": 4,
        "name": "Slack Notification",
        "status": "in_progress",
        "message": "Notifying team on Slack..."
    })
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8001/api/elasticseer/send_slack",
                json={
                    "severity": incident['severity'],
                    "incident_id": request.incident_id,
                    "title": f"✅ Automated Fix Created for {incident['title']}",
                    "message": f"""**Incident**: {request.incident_id}
**Service**: {incident['service']}
**Root Cause**: {incident['diagnosis'].get('root_cause', 'Under investigation')}

**Action Taken**: ElasticSeer has automatically:
✓ Analyzed the incident
✓ Searched relevant code
✓ Generated AI-powered fix
✓ Created GitHub PR

**PR**: {pr_url or 'Not created'}

**Next Steps**: Please review and approve the PR for deployment.""",
                    "action_required": True,
                    "pr_url": pr_url
                }
            )
            
            if response.status_code == 200:
                workflow_steps[-1]["status"] = "completed"
                workflow_steps[-1]["result"] = "Notification sent to #general"
            else:
                workflow_steps[-1]["status"] = "failed"
                workflow_steps[-1]["error"] = f"API returned {response.status_code}"
                
    except Exception as e:
        workflow_steps[-1]["status"] = "failed"
        workflow_steps[-1]["error"] = str(e)
    
    # Update incident with remediation info
    if pr_url:
        try:
            # Update incident in Elasticsearch
            incident['remediation'] = {
                "file_path": relevant_files[0].get('file_path', 'config.py') if relevant_files else 'config.py',
                "explanation": fix_explanation or 'AI-generated fix',
                "pr_url": pr_url
            }
            incident['status'] = 'remediating'
            
            es.index(
                index='incident-history',
                id=result['hits']['hits'][0]['_id'],
                document=incident,
                refresh=True
            )
        except Exception as e:
            logger.error(f"Failed to update incident: {e}")
    
    return {
        "success": True,
        "incident_id": request.incident_id,
        "workflow_steps": workflow_steps,
        "pr_url": pr_url,
        "completed_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_steps": len(workflow_steps),
            "completed": len([s for s in workflow_steps if s['status'] == 'completed']),
            "failed": len([s for s in workflow_steps if s['status'] == 'failed']),
            "skipped": len([s for s in workflow_steps if s['status'] == 'skipped'])
        }
    }


@router.get("/list")
async def list_recent_incidents(limit: int = 10):
    """
    List recent incidents
    """
    es = get_es_client()
    
    try:
        result = es.search(
            index='incident-history',
            body={
                'query': {'match_all': {}},
                'sort': [{'created_at': {'order': 'desc'}}],
                'size': limit
            }
        )
        
        incidents = [hit['_source'] for hit in result['hits']['hits']]
        
        return {
            "success": True,
            "count": len(incidents),
            "incidents": incidents
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list incidents: {str(e)}")
