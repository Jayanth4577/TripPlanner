"""
VoyageMind Bedrock Client Module

Handles AWS Bedrock integration for invoking Nova models.
Supports streaming and non-streaming responses.
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional, List
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class BedrockClient:
    """
    Client for interacting with AWS Bedrock and Nova models.
    
    Supports:
    - Text generation with Nova 2 Pro / Lite / Sonic
    - Structured tool calling (JSON schemas)
    - Streaming responses
    - Prompt caching for efficiency
    """

    def __init__(self):
        """Initialize Bedrock client with AWS credentials"""
        self.region = settings.aws.bedrock_region
        self.model_id = settings.aws.bedrock_model_id
        
        # Initialize boto3 client
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=self.region,
            aws_access_key_id=settings.aws.access_key_id,
            aws_secret_access_key=settings.aws.secret_access_key,
        )
        
        logger.info(f"Initialized Bedrock client with model: {self.model_id} in region: {self.region}")

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        top_p: float = 0.9,
    ) -> Dict[str, Any]:
        """
        Invoke a Nova model with text completion.
        
        Args:
            prompt: User message/prompt
            system_prompt: System instructions for the model
            tools: Optional list of tool definitions (JSON schemas)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            top_p: Nucleus sampling parameter
            
        Returns:
            Response from the model including content and metadata
            
        Raises:
            ClientError: If Bedrock API call fails
        """
        
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            logger.debug(f"Using system prompt: {system_prompt[:100]}...")
        
        # Prepare user message
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Prepare request body
        body = {
            "anthropic_version": "bedrock-2024-04-04",
            "max_tokens": max_tokens,
            "system": system_prompt or "",
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
        }
        
        # Add tools if provided
        if tools:
            body["tools"] = tools
            logger.debug(f"Including {len(tools)} tools in request")
        
        try:
            logger.debug(f"Invoking {self.model_id}...")
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
            )
            
            # Parse response
            response_body = json.loads(response["body"].read())
            logger.debug(f"Received response from Bedrock")
            
            return response_body
            
        except ClientError as e:
            logger.error(f"Bedrock API error: {str(e)}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Bedrock response: {str(e)}")
            raise

    async def invoke_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        top_p: float = 0.9,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Invoke a Nova model with streaming response.
        
        This is useful for real-time agent reasoning where we want to stream
        intermediate steps to the frontend.
        
        Args:
            prompt: User message/prompt
            system_prompt: System instructions for the model
            tools: Optional list of tool definitions
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            top_p: Nucleus sampling parameter
            
        Yields:
            Streaming response chunks with incremental content
            
        Raises:
            ClientError: If Bedrock API call fails
        """
        
        messages = [{
            "role": "user",
            "content": prompt
        }]
        
        # Prepare request body
        body = {
            "anthropic_version": "bedrock-2024-04-04",
            "max_tokens": max_tokens,
            "system": system_prompt or "",
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
        }
        
        if tools:
            body["tools"] = tools
        
        try:
            logger.debug(f"Invoking {self.model_id} with streaming...")
            response = self.client.invoke_model_with_response_stream(
                modelId=self.model_id,
                body=json.dumps(body),
            )
            
            # Stream response chunks
            for event in response["body"]:
                chunk = json.loads(event["chunk"]["bytes"])
                yield chunk
                logger.debug(f"Streamed chunk: {chunk.get('type')}")
                
        except ClientError as e:
            logger.error(f"Bedrock streaming error: {str(e)}")
            raise

    def extract_text_from_response(self, response: Dict[str, Any]) -> str:
        """
        Extract text content from Bedrock response.
        
        Args:
            response: Response from invoke()
            
        Returns:
            Extracted text content
        """
        if "content" in response:
            content = response["content"]
            if isinstance(content, list):
                # Multiple blocks
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and "text" in block:
                        text_parts.append(block["text"])
                return "".join(text_parts)
            elif isinstance(content, str):
                return content
        
        return ""

    def extract_tool_calls_from_response(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tool calls from Bedrock response.
        
        The model can invoke multiple tools in parallel.
        
        Args:
            response: Response from invoke()
            
        Returns:
            List of tool calls with input and metadata
        """
        tool_calls = []
        
        if "content" in response:
            content = response["content"]
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_calls.append({
                            "id": block.get("id"),
                            "name": block.get("name"),
                            "input": block.get("input", {}),
                        })
        
        return tool_calls

    def get_model_info(self) -> Dict[str, str]:
        """
        Get information about the current model.
        
        Returns:
            Dictionary with model metadata
        """
        return {
            "model_id": self.model_id,
            "region": self.region,
            "timestamp": datetime.utcnow().isoformat(),
        }


# Singleton instance
_bedrock_client: Optional[BedrockClient] = None


def get_bedrock_client() -> BedrockClient:
    """
    Get or create Bedrock client instance (singleton).
    
    Returns:
        BedrockClient instance
    """
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = BedrockClient()
    return _bedrock_client
