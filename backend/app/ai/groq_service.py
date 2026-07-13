import json
import logging
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel
from groq import Groq, APIConnectionError, RateLimitError
import httpx
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from app.core.config import settings

logger = logging.getLogger(__name__)

class GroqServiceException(Exception):
    pass

class GroqService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        
        # Configure a custom HTTP client with timeouts
        self.http_client = httpx.Client(
            timeout=httpx.Timeout(
                connect=10.0, 
                read=30.0, 
                write=10.0, 
                pool=10.0
            )
        )
        
        # Initialize Groq client
        # Max retries is set to 0 here because we implement our own tenacity retry wrapper
        self.client = Groq(
            api_key=self.api_key,
            http_client=self.http_client,
            max_retries=0
        )

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((APIConnectionError, RateLimitError, httpx.TimeoutException)),
        reraise=True
    )
    def _execute_completion(
        self, 
        messages: list, 
        model: str = "llama-3.3-70b-versatile",
        response_format: Optional[Dict] = None
    ) -> Any:
        """Wrapper to execute the API call with retries and timeout handling."""
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": 0.0,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = self.client.chat.completions.create(**kwargs)
            return response
        except Exception as e:
            logger.warning(f"Groq API call failed: {str(e)}")
            raise

    def extract_structured_data(
        self, 
        prompt: str, 
        schema_model: Type[BaseModel], 
        model: str = "llama-3.3-70b-versatile"
    ) -> BaseModel:
        """
        Sends a prompt to the Groq LLM and enforces a JSON structured output 
        matching the provided Pydantic schema.
        """
        messages = [
            {
                "role": "system",
                "content": f"You are a strict data extraction assistant. You must output a JSON object matching this JSON schema: {json.dumps(schema_model.model_json_schema())}. Do not output any markdown formatting, only pure JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # Enforce JSON object response format
        response_format = {"type": "json_object"}
        
        try:
            response = self._execute_completion(messages=messages, model=model, response_format=response_format)
            content = response.choices[0].message.content
            
            # Parse the returned JSON string into the Pydantic model
            parsed_data = schema_model.model_validate_json(content)
            return parsed_data
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            raise GroqServiceException("Invalid JSON format returned by LLM.") from e
        except Exception as e:
            logger.error(f"Error during structured extraction: {str(e)}")
            raise GroqServiceException(f"LLM extraction failed: {str(e)}") from e

# Instantiate a reusable default service instance
groq_service = GroqService()
