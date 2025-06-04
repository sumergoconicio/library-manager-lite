"""
Title: Flexible LLM Provider System
Description: Provides a unified interface for multiple LLM providers (Anthropic, OpenAI, etc.) via litellm, configurable per workflow. Supports different models and API keys for different tasks.
Author: ChAI-Engine (chaiji)
Last Updated: 2025-06-04
Dependencies: litellm, typing, re, json, os, pathlib
Design Rationale: Centralizes all LLM calls through litellm with workflow-specific configurations; future-proofs LLM integration for multiple providers and use cases.
"""

from typing import Dict, Optional, Any, Union
import re
import json
import os
from pathlib import Path

class LitellmProvider:
    """
    Purpose: Use litellm to call various LLM providers for different workflows.
    Inputs: model (str), api_key (str), optional kwargs
    Outputs: Depends on the workflow (Dict, str, etc.)
    Role: Central LLM interface for all AI-powered workflows.
    """
    def __init__(self, model: str, api_key: str, **kwargs):
        """
        Purpose: Initialize LitellmProvider with selected model and API key.
        Inputs: model (str), api_key (str), kwargs (dict)
        Outputs: None
        Role: Sets up LLM provider for subsequent metadata extraction.
        """
        import litellm
        self.litellm = litellm
        self.model = model
        self.api_key = api_key
        self.kwargs = kwargs

    def completion(self, prompt: str, user_content: str, output_format: str = None) -> Any:
        """
        Purpose: Submit prompt and user content to LLM, with optional output format handling.
        Inputs: prompt (str), user_content (str), output_format (str, optional)
        Outputs: Raw response content or parsed format (JSON, etc.)
        Role: Generic LLM completion interface for all workflows.
        """
        try:
            response = self.litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_content},
                ],
                api_key=self.api_key,
                **self.kwargs
            )
            content = response['choices'][0]['message']['content']
            
            if output_format == 'json':
                return self._parse_json_response(content)
            elif output_format == 'text':
                return content.strip()
            else:
                return content
        except Exception as e:
            print(f"LitellmProvider completion error: {e}")
            return None
            
    def _parse_json_response(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Purpose: Parse and normalize JSON output from LLM responses.
        Inputs: content (str) - raw LLM response
        Outputs: Dict parsed from JSON or None on failure
        Role: Helper for structured data extraction.
        """
        try:
            # Extract JSON from code block if present
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, flags=re.DOTALL)
            content = match.group(1) if match else content
            content = re.sub(r'^```(?:json)?', '', content.strip(), flags=re.IGNORECASE).strip()
            content = re.sub(r'```$', '', content.strip()).strip()
            content_match = re.search(r'\{.*\}', content, flags=re.DOTALL)
            if content_match:
                content = content_match.group(0)
            if '"' not in content:
                content = content.replace("'", '"')
            content = re.sub(r',\s*([}\]])', r'\1', content)
            return json.loads(content)
        except Exception as e:
            print(f"JSON parsing error: {e}")
            return None
            
    def extract_metadata(self, prompt: str, extracted_text: str) -> Optional[Dict[str, str]]:
        """
        Purpose: Submit prompt and extracted text to LLM, parse and normalize output.
        Inputs: prompt (str), extracted_text (str)
        Outputs: Dict with keys 'author', 'title', 'pubdate' or None
        Role: Main LLM call for metadata extraction.
        """
        guessed = self.completion(prompt, extracted_text, output_format='json')
        if guessed and (
            guessed.get("author", "").strip().lower() in {"unknown", "various"}
            or guessed.get("title", "").strip().lower() == "unknown"
            or not guessed.get("title", "").strip()
        ):
            return None
        return guessed
        
    def embed_text(self, text: str) -> Optional[list[float]]:
        """
        Purpose: Generate embeddings for text using configured embedding model.
        Inputs: text (str) - text to embed
        Outputs: List of floats representing the embedding vector or None on failure
        Role: Text embedding for semantic search and similarity.
        """
        try:
            response = self.litellm.embedding(
                model=self.model,
                input=text,
                api_key=self.api_key,
                **self.kwargs
            )
            return response['data'][0]['embedding']
        except Exception as e:
            print(f"Embedding error: {e}")
            return None

def _load_config() -> Dict[str, Any]:
    """
    Purpose: Load LLM configuration from JSON file.
    Inputs: None
    Outputs: Dict containing workflow configurations
    Role: Provides centralized configuration for all LLM workflows.
    """
    config_path = Path(__file__).parent.parent / 'user_inputs' / 'llm_config.json'
    try:
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            # Return default configuration if file doesn't exist
            return {
                "workflows": {
                    "identify": {
                        "provider": "anthropic",
                        "model": "claude-3-haiku-20240307",
                        "api_key_env": "ANTHROPIC_API_KEY"
                    }
                },
                "defaults": {
                    "provider": "anthropic",
                    "model": "claude-3-haiku-20240307",
                    "api_key_env": "ANTHROPIC_API_KEY"
                }
            }
    except Exception as e:
        print(f"Error loading LLM config: {e}")
        # Fallback to minimal default configuration
        return {
            "defaults": {
                "provider": "anthropic",
                "model": "claude-3-haiku-20240307",
                "api_key_env": "ANTHROPIC_API_KEY"
            }
        }

def get_llm_provider(workflow: str = None, **kwargs) -> 'LitellmProvider':
    """
    Purpose: Factory for LitellmProvider; selects provider/model based on workflow.
    Inputs: workflow (str, optional), kwargs (for additional parameters)
    Outputs: LitellmProvider instance configured for the specified workflow
    Role: Centralizes all logic for LLM selection and secrets management based on workflow.
    """
    config = _load_config()
    
    # Get workflow-specific config or fall back to defaults
    if workflow and workflow in config.get("workflows", {}):
        workflow_config = config["workflows"][workflow]
    else:
        workflow_config = config.get("defaults", {
            "provider": "anthropic",
            "model": "claude-3-haiku-20240307",
            "api_key_env": "ANTHROPIC_API_KEY"
        })
    
    # Extract configuration
    model = kwargs.pop("model", workflow_config.get("model"))
    api_key_env = workflow_config.get("api_key_env")
    additional_params = workflow_config.get("additional_params", {})
    
    # Get API key from environment
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise RuntimeError(f"API key not found. Please set {api_key_env} in your environment or .env file.")
    
    # Merge additional parameters with kwargs
    merged_kwargs = {**additional_params, **kwargs}
    
    return LitellmProvider(model, api_key, **merged_kwargs)
