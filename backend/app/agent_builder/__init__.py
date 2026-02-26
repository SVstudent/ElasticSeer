"""
Agent Builder infrastructure for ElasticSeer.

This module provides the infrastructure for Agent Builder agents,
including custom tools, inference services, and helper functions.
"""

from .inference_service import InferenceService, create_inference_service
from .custom_tools import (
    ToolRegistry,
    ToolDefinition,
    ToolType,
    register_tool,
    get_tool,
    list_tools,
    execute_tool,
    export_tools_yaml
)
from .gemini_helper import GeminiClient, create_gemini_client
from .github_helper import GitHubClient, create_github_client
from .hybrid_search_helper import HybridSearchHelper, create_hybrid_search_helper

__all__ = [
    # Inference service
    "InferenceService",
    "create_inference_service",
    # Custom tools
    "ToolRegistry",
    "ToolDefinition",
    "ToolType",
    "register_tool",
    "get_tool",
    "list_tools",
    "execute_tool",
    "export_tools_yaml",
    # Gemini helper
    "GeminiClient",
    "create_gemini_client",
    # GitHub helper
    "GitHubClient",
    "create_github_client",
    # Hybrid search helper
    "HybridSearchHelper",
    "create_hybrid_search_helper",
]
