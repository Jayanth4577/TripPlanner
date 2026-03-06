"""
VoyageMind Core Module

Provides core infrastructure:
- Bedrock AI integration
- Redis caching
- Prompt templates
"""

from app.core.bedrock_client import BedrockClient, get_bedrock_client
from app.core.cache import CacheManager, CacheKeys, get_cache_manager
from app.core.prompt_templates import PromptTemplates, ErrorMessages

__all__ = [
    "BedrockClient",
    "get_bedrock_client",
    "CacheManager",
    "CacheKeys",
    "get_cache_manager",
    "PromptTemplates",
    "ErrorMessages",
]
