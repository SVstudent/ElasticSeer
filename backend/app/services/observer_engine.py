"""
Observer Engine - Continuous Monitoring with 3σ Anomaly Detection

This engine continuously monitors:
- Elasticsearch metrics with statistical anomaly detection (3σ)
- GitHub commits and PRs
- Jira ticket activity
- Slack messages

When anomalies are detected, it triggers the Planner workflow with user approval.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from elasticsearch import Elasticsearch
from app.core.config import settings
import httpx

logger = logging.getLogger(__name__)


class ObserverEngine:
    """Continuous monitoring engine with statistical anomaly detection"""
    
    def __init__(self):
        self.es = Elasticsearch(
            hosts=[settings.elasticsearch_url],
            api_key=settings.elasticsearch_api_key,
            verify_certs=True
        )
        self.running = False
        self.check_interval = 60  # Check every 60 seconds
        self.anomaly_threshold_sigma = 3.0  # 3σ threshold
        
    async def start(self):
        """Start the observer engine"""
        self.running = True
        logger.info("🔍 Observer Engine started - monitoring for anomalies...")
        
        while self.running:
            try:
                # Run all monitoring checks
                await self.check_metrics_anomalies()
                await self.check_github_activity()
                await self.check_jira_activity()
                await self.check_slack_activity()
                await self.check_agent_activity()
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Observer Engine error: {e}", exc_info=True)
                await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """Stop the observer engine"""
        self.running = False
        logger.info("🛑 Observer Engine stopped")
    
    async def check_metrics_anomalies(self) -> List[Dict[str, Any]]:
        """
        Check for metric anomalies using 3σ statistical detection
        
        Uses ES|QL to calculate:
        - Moving average (baseline)
        - Standard deviation
        - Detects values > 3σ from baseline
        """
        try:
            now = datetime.utcnow()
            
            # Query last hour for current values
            current_start = now - timedelta(hours=1)
            
            # Query last 7 days for baseline calculation
            baseline_start = now - timedelta(days=7)
            
            # ES|QL query for statistical anomaly detection
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"range": {"@timestamp": {"gte": baseline_start.isoformat(), "lte": now.isoformat()}}}
                        ]
                    }
                },
                "size": 0,
                "aggs": {
                    "by_service_metric": {
                        "composite": {
                            "size": 100,
                            "sources": [
                                {"service": {"terms": {"field": "service"}}},
                                {"metric": {"terms": {"field": "metric_name"}}}
                            ]
                        },
                        "aggs": {
                            # Baseline statistics (7 days)
                            "baseline_stats": {
                                "stats": {"field": "value"}
                            },
                            # Current hour values
                            "current_values": {
                                "filter": {
                                    "range": {"@timestamp": {"gte": current_start.isoformat()}}
                                },
                                "aggs": {
                                    "current_stats": {
                                        "stats": {"field": "value"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            result = self.es.search(index="metrics", body=query)
            
            anomalies = []
            
            for bucket in result['aggregations']['by_service_metric']['buckets']:
                service = bucket['key']['service']
                metric = bucket['key']['metric']
                
                baseline = bucket['baseline_stats']
                current = bucket['current_values']['current_stats']
                
                if baseline['count'] > 0 and current['count'] > 0:
                    # Calculate baseline mean and std dev
                    baseline_mean = baseline['avg']
                    baseline_std = baseline['std_deviation']
                    
                    # Current max value
                    current_max = current['max']
                    current_avg = current['avg']
                    
                    # Calculate sigma deviation
                    if baseline_std > 0:
                        sigma_deviation = abs(current_max - baseline_mean) / baseline_std
                        
                        # Anomaly detected if > 3σ
                        if sigma_deviation > self.anomaly_threshold_sigma:
                            anomaly = {
                                "detected_at": now.isoformat(),
                                "service": service,
                                "metric": metric,
                                "current_value": round(current_max, 2),
                                "current_avg": round(current_avg, 2),
                                "baseline_mean": round(baseline_mean, 2),
                                "baseline_std": round(baseline_std, 2),
                                "sigma_deviation": round(sigma_deviation, 2),
                                "severity": self._calculate_severity(sigma_deviation),
                                "type": "statistical_anomaly"
                            }
                            
                            anomalies.append(anomaly)
                            
                            logger.warning(
                                f"🚨 ANOMALY DETECTED: {service}.{metric} = {current_max:.2f} "
                                f"(baseline: {baseline_mean:.2f} ± {baseline_std:.2f}, "
                                f"{sigma_deviation:.1f}σ deviation)"
                            )
                            
                            # Trigger planner workflow with approval
                            await self.trigger_planner_workflow(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error checking metrics anomalies: {e}", exc_info=True)
            return []
    
    async def check_github_activity(self) -> List[Dict[str, Any]]:
        """
        Monitor GitHub for recent commits and PRs
        Correlates with anomaly timestamps to identify suspect commits
        """
        try:
            if not settings.github_token:
                return []
            
            now = datetime.utcnow()
            since = now - timedelta(hours=1)
            
            activities = []
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get recent commits
                commits_url = f"https://api.github.com/repos/{settings.github_owner}/{settings.github_repo}/commits"
                commits_response = await client.get(
                    commits_url,
                    headers={
                        "Authorization": f"token {settings.github_token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    params={"since": since.isoformat()}
                )
                
                if commits_response.status_code == 200:
                    commits = commits_response.json()
                    for commit in commits[:5]:  # Last 5 commits
                        activities.append({
                            "type": "commit",
                            "sha": commit['sha'][:7],
                            "message": commit['commit']['message'].split('\n')[0],
                            "author": commit['commit']['author']['name'],
                            "timestamp": commit['commit']['author']['date'],
                            "url": commit['html_url']
                        })
                
                # Get recent PRs
                prs_url = f"https://api.github.com/repos/{settings.github_owner}/{settings.github_repo}/pulls"
                prs_response = await client.get(
                    prs_url,
                    headers={
                        "Authorization": f"token {settings.github_token}",
                        "Accept": "application/vnd.github.v3+json"
                    },
                    params={"state": "all", "sort": "updated", "direction": "desc"}
                )
                
                if prs_response.status_code == 200:
                    prs = prs_response.json()
                    for pr in prs[:5]:  # Last 5 PRs
                        if pr['updated_at'] >= since.isoformat():
                            activities.append({
                                "type": "pull_request",
                                "number": pr['number'],
                                "title": pr['title'],
                                "state": pr['state'],
                                "author": pr['user']['login'],
                                "timestamp": pr['updated_at'],
                                "url": pr['html_url']
                            })
            
            if activities:
                logger.info(f"📊 GitHub Activity: {len(activities)} events in last hour")
            
            return activities
            
        except Exception as e:
            logger.error(f"Error checking GitHub activity: {e}", exc_info=True)
            return []
    
    async def check_jira_activity(self) -> List[Dict[str, Any]]:
        """Monitor Jira for recent ticket updates or creations"""
        try:
            # Check if index exists
            if not self.es.indices.exists(index="activity-log"):
                return []

            result = self.es.search(
                index="activity-log",
                body={
                    "query": {"term": {"type": "jira_created"}},
                    "sort": [{"timestamp": "desc"}],
                    "size": 5
                }
            )
            
            activities = [hit['_source'] for hit in result['hits']['hits']]
            
            if activities:
                logger.info(f"📊 Jira Activity: {len(activities)} events found in activity log")
            
            return activities
            
        except Exception as e:
            logger.error(f"Error checking Jira activity: {e}", exc_info=True)
            return []
            
    async def check_slack_activity(self) -> List[Dict[str, Any]]:
        """Monitor Slack for recent alerts sent by the agent"""
        try:
            # Check if index exists
            if not self.es.indices.exists(index="activity-log"):
                return []

            result = self.es.search(
                index="activity-log",
                body={
                    "query": {"term": {"type": "slack_sent"}},
                    "sort": [{"timestamp": "desc"}],
                    "size": 5
                }
            )
            
            activities = [hit['_source'] for hit in result['hits']['hits']]
            
            if activities:
                logger.info(f"📊 Slack Activity: {len(activities)} alerts found in activity log")
            
            return activities
            
        except Exception as e:
            logger.error(f"Error checking Slack activity: {e}", exc_info=True)
            return []

    async def check_agent_activity(self) -> List[Dict[str, Any]]:
        """Monitor general agent interactions and actions"""
        try:
            # Check if index exists
            if not self.es.indices.exists(index="activity-log"):
                return []

            result = self.es.search(
                index="activity-log",
                body={
                    "query": {
                        "bool": {
                            "must_not": [
                                {"terms": {"type": ["jira_created", "slack_sent", "metrics", "github"]}}
                            ]
                        }
                    },
                    "sort": [{"timestamp": "desc"}],
                    "size": 10
                }
            )
            
            activities = [hit['_source'] for hit in result['hits']['hits']]
            
            if activities:
                logger.info(f"📊 Agent Activity: {len(activities)} interactions found")
            
            return activities
            
        except Exception as e:
            logger.error(f"Error checking agent activity: {e}", exc_info=True)
            return []
    
    def _calculate_severity(self, sigma: float) -> str:
        """Calculate severity based on sigma deviation"""
        if sigma >= 5.0:
            return "Sev-1"  # Critical
        elif sigma >= 4.0:
            return "Sev-2"  # High
        else:
            return "Sev-3"  # Medium
    
    async def trigger_planner_workflow(self, anomaly: Dict[str, Any]):
        """
        Trigger the Planner workflow when anomaly is detected
        
        This creates a pending workflow that requires user approval
        """
        try:
            # Create pending workflow in database
            workflow = {
                "id": f"workflow-{datetime.utcnow().timestamp()}",
                "type": "anomaly_response",
                "status": "pending_approval",
                "created_at": datetime.utcnow().isoformat(),
                "anomaly": anomaly,
                "actions": [
                    "investigate_root_cause",
                    "search_related_code",
                    "identify_suspect_commit",
                    "generate_fix",
                    "create_pr",
                    "notify_team"
                ]
            }
            
            # Store in Elasticsearch for UI to display
            self.es.index(
                index="pending-workflows",
                document=workflow,
                refresh=True
            )
            
            logger.info(f"🎯 Planner workflow triggered for {anomaly['service']}.{anomaly['metric']} - awaiting approval")
            
        except Exception as e:
            logger.error(f"Error triggering planner workflow: {e}", exc_info=True)
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status for UI"""
        try:
            now = datetime.utcnow()
            
            # Get recent anomalies
            try:
                # Query anomaly-records instead of raw metrics for better UI data
                anomalies_result = self.es.search(index="anomaly-records", body={
                    "query": {"match_all": {}},
                    "sort": [{"detected_at": "desc"}],
                    "size": 10
                })
                anomalies = [hit['_source'] for hit in anomalies_result['hits']['hits']]
            except Exception:
                anomalies = []
            
            # Get pending workflows
            try:
                workflows_result = self.es.search(
                    index="pending-workflows",
                    body={
                        "query": {"term": {"status": "pending_approval"}},
                        "sort": [{"created_at": "desc"}],
                        "size": 5
                    }
                )
                pending_workflows = [hit['_source'] for hit in workflows_result['hits']['hits']]
            except Exception:
                pending_workflows = []
            
            # Get detailed activity for monitoring categories
            github_activity = await self.check_github_activity()
            jira_activity = await self.check_jira_activity()
            slack_activity = await self.check_slack_activity()
            agent_activity = await self.check_agent_activity()
            
            return {
                "status": "running" if self.running else "stopped",
                "last_check": now.isoformat(),
                "check_interval_seconds": self.check_interval,
                "anomaly_threshold_sigma": self.anomaly_threshold_sigma,
                "recent_anomalies": anomalies,
                "pending_workflows": pending_workflows,
                "activity_log": {
                    "github": github_activity,
                    "jira": jira_activity,
                    "slack": slack_activity,
                    "agent": agent_activity
                },
                "monitoring": {
                    "metrics": True,
                    "github": bool(settings.github_token),
                    "jira": True,  # Monitored via activity log
                    "slack": True, # Monitored via activity log
                    "agent": True
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting monitoring status: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }


# Global observer instance
observer_engine = ObserverEngine()
