"""
Configuration settings for ElasticSeer
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Elasticsearch Configuration
    elasticsearch_url: str
    elasticsearch_api_key: str
    kibana_url: str
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    
    # GitHub Configuration
    github_token: Optional[str] = None
    github_owner: Optional[str] = None
    github_repo: Optional[str] = None
    
    # Gemini API Configuration
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    
    # Slack Configuration (Optional)
    slack_bot_token: Optional[str] = None
    slack_signing_secret: Optional[str] = None
    slack_war_room_channel: Optional[str] = None
    
    # Jira Configuration (Optional)
    jira_url: Optional[str] = None
    jira_email: Optional[str] = None
    jira_token: Optional[str] = None
    jira_project: str = "INCIDENT"
    
    # Application Settings
    check_interval_seconds: int = 60
    baseline_window_days: int = 7
    approval_timeout_minutes: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
