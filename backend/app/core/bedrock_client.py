"""AWS Bedrock client for Amazon Nova models."""

from __future__ import annotations

import json
import logging
from typing import Any

import boto3
from app.config import get_settings

logger = logging.getLogger(__name__)


class BedrockClient:
    """Wrapper around the AWS Bedrock Runtime for Amazon Nova inference."""

    def __init__(self, model_id: str | None = None):
        settings = get_settings()
        self.model_id = model_id or settings.bedrock_model_id
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )

    async def invoke(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> str:
        """Send a prompt to Nova and return the text response."""
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        body: dict[str, Any] = {
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature,
            },
        }
        if system:
            body["system"] = [{"text": system}]

        logger.info("Bedrock invoke | model=%s tokens=%d", self.model_id, max_tokens)

        response = self._client.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        result = json.loads(response["body"].read())
        text = result["output"]["message"]["content"][0]["text"]
        logger.debug("Bedrock response length: %d chars", len(text))
        return text

    async def invoke_with_tools(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        system: str = "",
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Invoke Nova with structured tool-calling support."""
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        body: dict[str, Any] = {
            "messages": messages,
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0.2},
            "toolConfig": {"tools": tools},
        }
        if system:
            body["system"] = [{"text": system}]

        response = self._client.invoke_model(
            modelId=self.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        return json.loads(response["body"].read())