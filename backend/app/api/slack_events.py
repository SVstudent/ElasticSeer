"""
Slack Events Webhook Handler
Handles bidirectional interactions between Slack and ElasticSeer
"""

from fastapi import APIRouter, Request, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import httpx
from app.core.config import settings
from app.api.agent_chat_with_reasoning import ChatRequest, ChatMessage, chat_with_reasoning

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/slack", tags=["slack-events"])

class SlackEvent(BaseModel):
    token: str
    challenge: Optional[str] = None
    type: str
    event: Optional[Dict[str, Any]] = None

async def process_slack_mention(event_data: Dict[str, Any]):
    """Process a Slack @mention in the background"""
    channel = event_data.get("channel")
    user = event_data.get("user")
    text = event_data.get("text", "")
    thread_ts = event_data.get("ts") # Reply in thread
    
    # Remove the bot mention from the text (usually like <@U12345678>)
    clean_text = text
    if ">" in text:
        clean_text = text.split(">", 1)[1].strip()
    
    if not clean_text:
        clean_text = "How can I help you today?"

    logger.info(f"Processing Slack mention from {user} in {channel}: {clean_text}")

    try:
        # Create a ChatRequest for our existing agent logic
        chat_request = ChatRequest(
            message=clean_text,
            conversation_history=[] # For now, no history for Slack mentions unless we implement thread-based state
        )
        
        # Call the reasoning agent
        response = await chat_with_reasoning(chat_request)
        
        # Format the response for Slack
        slack_message = f"*ElasticSeer Response*\n\n{response.response}\n\n"
        
        if response.reasoning_trace:
            slack_message += "🔍 *Reasoning Trace populated in dashboard*"
            
        # Send back to Slack
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {settings.slack_bot_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "channel": channel,
                    "thread_ts": thread_ts,
                    "text": slack_message,
                    "mrkdwn": True
                }
            )
            
    except Exception as e:
        logger.error(f"Error processing Slack mention: {e}", exc_info=True)
        # Send error back to Slack
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {settings.slack_bot_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "channel": channel,
                    "thread_ts": thread_ts,
                    "text": f"❌ Sorry, I encountered an error processing your request: {str(e)}"
                }
            )

@router.post("/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """Main entry point for Slack Event Subscriptions"""
    body = await request.json()
    
    # Handle URL Verification (Challenge)
    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge")}
    
    # Handle Event Callbacks
    if body.get("type") == "event_callback":
        event = body.get("event", {})
        
        # Handle @mentions
        if event.get("type") == "app_mention":
            # Process in background to avoid Slack timeout (3s)
            background_tasks.add_task(process_slack_mention, event)
            return {"status": "processing"}
            
    return {"status": "ignored"}
