"""
Jira Client for ElasticSeer

Handles Jira ticket creation and management for incident tracking
"""

import httpx
import logging
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)


class JiraClient:
    """Client for interacting with Jira API"""
    
    def __init__(self):
        self.base_url = settings.jira_url
        self.token = settings.jira_token
        self.project = settings.jira_project
        self.email = settings.jira_email if hasattr(settings, 'jira_email') else None
        self.enabled = bool(self.base_url and self.token)
        
        if not self.enabled:
            logger.warning("Jira integration not configured - tickets will be logged to console only")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers for Jira API"""
        # Jira Cloud uses Basic Auth with email:token
        # If no email provided, try Bearer token (for Jira Server/PAT)
        if self.email:
            # Basic Auth for Jira Cloud
            auth_string = f"{self.email}:{self.token}"
            auth_bytes = auth_string.encode('ascii')
            base64_bytes = base64.b64encode(auth_bytes)
            base64_string = base64_bytes.decode('ascii')
            
            return {
                "Authorization": f"Basic {base64_string}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        else:
            # Bearer token for Jira Server/Data Center
            return {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
    
    def _map_priority(self, priority: str) -> str:
        """Map ElasticSeer priority to Jira priority"""
        priority_map = {
            "Critical": "Highest",
            "High": "High",
            "Medium": "Medium",
            "Low": "Low"
        }
        return priority_map.get(priority, "Medium")
    
    async def create_ticket(
        self,
        summary: str,
        description: str,
        priority: str = "High",
        incident_id: Optional[str] = None,
        labels: Optional[List[str]] = None,
        issue_type: str = "Bug"
    ) -> Dict[str, Any]:
        """
        Create a Jira ticket
        
        Args:
            summary: Ticket title/summary
            description: Detailed description
            priority: Priority level (Critical, High, Medium, Low)
            incident_id: Related incident ID
            labels: List of labels to add
            issue_type: Jira issue type (Bug, Task, Story, etc.)
        
        Returns:
            Dict with ticket details including ticket_id and url
        """
        
        if not self.enabled:
            return self._log_to_console(summary, description, priority, incident_id, labels)
        
        try:
            # Build ticket payload
            ticket_labels = labels or []
            ticket_labels.extend(["elasticseer", "automated"])
            if incident_id:
                ticket_labels.append(f"incident-{incident_id}")
            
            # Format description with Jira markup
            formatted_description = self._format_description(description, incident_id)
            
            payload = {
                "fields": {
                    "project": {
                        "key": self.project
                    },
                    "summary": summary,
                    "description": formatted_description,
                    "issuetype": {
                        "name": issue_type
                    },
                    "priority": {
                        "name": self._map_priority(priority)
                    },
                    "labels": ticket_labels
                }
            }
            
            # Create ticket via Jira API
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/rest/api/3/issue",
                    headers=self._get_headers(),
                    json=payload
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    ticket_key = data.get("key")
                    ticket_url = f"{self.base_url}/browse/{ticket_key}"
                    
                    logger.info(f"✅ Jira ticket created: {ticket_key}")
                    
                    return {
                        "success": True,
                        "ticket_id": ticket_key,
                        "ticket_key": ticket_key,
                        "url": ticket_url,
                        "project": self.project,
                        "priority": priority,
                        "created_at": datetime.utcnow().isoformat()
                    }
                else:
                    error_msg = response.text
                    logger.error(f"Failed to create Jira ticket: {response.status_code} - {error_msg}")
                    
                    # Fallback to console logging
                    return self._log_to_console(summary, description, priority, incident_id, labels, error=error_msg)
        
        except Exception as e:
            logger.error(f"Error creating Jira ticket: {e}", exc_info=True)
            return self._log_to_console(summary, description, priority, incident_id, labels, error=str(e))
    
    def _format_description(self, description: str, incident_id: Optional[str] = None) -> Dict[str, Any]:
        """Format description with Atlassian Document Format (ADF)"""
        
        content = []
        
        # Add incident ID if provided
        if incident_id:
            content.append({
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "Incident ID: ",
                        "marks": [{"type": "strong"}]
                    },
                    {
                        "type": "text",
                        "text": incident_id
                    }
                ]
            })
        
        # Add metadata
        content.append({
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "Generated by: ",
                    "marks": [{"type": "strong"}]
                },
                {
                    "type": "text",
                    "text": "ElasticSeer Autonomous Agent"
                }
            ]
        })
        
        content.append({
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "Created at: ",
                    "marks": [{"type": "strong"}]
                },
                {
                    "type": "text",
                    "text": datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
                }
            ]
        })
        
        # Add separator
        content.append({
            "type": "rule"
        })
        
        # Add main description - split by newlines and create paragraphs
        for line in description.split('\n'):
            if line.strip():
                content.append({
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": line.strip()
                        }
                    ]
                })
        
        # Add footer
        content.append({
            "type": "rule"
        })
        
        content.append({
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "This ticket was automatically created by ElasticSeer AI Agent",
                    "marks": [{"type": "em"}]
                }
            ]
        })
        
        return {
            "type": "doc",
            "version": 1,
            "content": content
        }
    
    def _log_to_console(
        self,
        summary: str,
        description: str,
        priority: str,
        incident_id: Optional[str],
        labels: Optional[List[str]],
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log ticket to console when Jira is not available"""
        
        priority_emoji = {
            "Critical": "🔴",
            "High": "🟠",
            "Medium": "🟡",
            "Low": "🟢"
        }
        
        emoji = priority_emoji.get(priority, "📋")
        
        # Generate mock ticket ID
        ticket_id = f"{self.project}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        print(f"\n{'='*70}")
        print(f"{emoji} JIRA TICKET (Console Log)")
        print('='*70)
        print(f"Ticket ID: {ticket_id}")
        print(f"Project: {self.project}")
        print(f"Priority: {priority}")
        
        if incident_id:
            print(f"Incident: {incident_id}")
        
        if labels:
            print(f"Labels: {', '.join(labels)}")
        
        print(f"\nSummary: {summary}")
        print(f"\nDescription:\n{description}")
        
        if error:
            print(f"\n⚠️ Note: Jira API error - {error}")
            print("Ticket logged to console only")
        elif not self.enabled:
            print("\n⚠️ Note: Jira not configured")
            print("Set JIRA_URL and JIRA_TOKEN in .env to enable Jira integration")
        
        print('='*70)
        
        return {
            "success": True,
            "ticket_id": ticket_id,
            "project": self.project,
            "priority": priority,
            "url": f"{self.base_url}/browse/{ticket_id}" if self.base_url else None,
            "created_at": datetime.utcnow().isoformat(),
            "note": "Logged to console (Jira not fully configured)" if not self.enabled else "Jira API error - logged to console"
        }
    
    async def add_comment(self, ticket_id: str, comment: str) -> Dict[str, Any]:
        """Add a comment to an existing Jira ticket"""
        
        if not self.enabled:
            logger.info(f"Would add comment to {ticket_id}: {comment}")
            return {"success": True, "note": "Jira not configured"}
        
        try:
            payload = {
                "body": comment
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/rest/api/3/issue/{ticket_id}/comment",
                    headers=self._get_headers(),
                    json=payload
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"✅ Comment added to {ticket_id}")
                    return {"success": True, "ticket_id": ticket_id}
                else:
                    logger.error(f"Failed to add comment: {response.status_code}")
                    return {"success": False, "error": response.text}
        
        except Exception as e:
            logger.error(f"Error adding comment: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_ticket(
        self,
        ticket_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Update an existing Jira ticket"""
        
        if not self.enabled:
            logger.info(f"Would update {ticket_id}")
            return {"success": True, "note": "Jira not configured"}
        
        try:
            fields = {}
            
            if status:
                fields["status"] = {"name": status}
            
            if priority:
                fields["priority"] = {"name": self._map_priority(priority)}
            
            if labels:
                fields["labels"] = labels
            
            if not fields:
                return {"success": False, "error": "No fields to update"}
            
            payload = {"fields": fields}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(
                    f"{self.base_url}/rest/api/3/issue/{ticket_id}",
                    headers=self._get_headers(),
                    json=payload
                )
                
                if response.status_code == 204:
                    logger.info(f"✅ Ticket {ticket_id} updated")
                    return {"success": True, "ticket_id": ticket_id}
                else:
                    logger.error(f"Failed to update ticket: {response.status_code}")
                    return {"success": False, "error": response.text}
        
        except Exception as e:
            logger.error(f"Error updating ticket: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """Get details of a Jira ticket"""
        
        if not self.enabled:
            return {"success": False, "error": "Jira not configured"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/rest/api/3/issue/{ticket_id}",
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "ticket": {
                            "id": data.get("id"),
                            "key": data.get("key"),
                            "summary": data["fields"].get("summary"),
                            "status": data["fields"]["status"].get("name"),
                            "priority": data["fields"]["priority"].get("name"),
                            "created": data["fields"].get("created"),
                            "updated": data["fields"].get("updated")
                        }
                    }
                else:
                    return {"success": False, "error": response.text}
        
        except Exception as e:
            logger.error(f"Error getting ticket: {e}")
            return {"success": False, "error": str(e)}


# Global Jira client instance
jira_client = JiraClient()
