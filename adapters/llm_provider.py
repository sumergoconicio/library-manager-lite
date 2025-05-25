"""
Title: LitellmProvider for PDF Renamer
Description: Provides a unified interface for Anthropic Claude 3 Haiku via litellm, for extracting PDF metadata. Users select model/provider using litellm's standard API.
Author: ChAI-Engine (chaiji)
Last Updated: 2025-05-25
Dependencies: litellm, typing, re, json
Design Rationale: Centralizes all LLM calls through litellm; future-proofs LLM integration for Anthropic Claude only.
"""

from typing import Dict, Optional
import re
import json

class LitellmProvider:
    """
    Purpose: Use litellm to call Anthropic Claude 3 Haiku for PDF metadata extraction.
    Inputs: model (str), api_key (str), optional kwargs
    Outputs: Dict with keys 'author', 'title', 'pubdate' or None
    Role: Central LLM interface for the renamer pipeline.
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

    def extract_metadata(self, prompt: str, extracted_text: str) -> Optional[Dict[str, str]]:
        """
        Purpose: Submit prompt and extracted text to LLM, parse and normalize output.
        Inputs: prompt (str), extracted_text (str)
        Outputs: Dict with keys 'author', 'title', 'pubdate' or None
        Role: Main LLM call for metadata extraction.
        """
        try:
            response = self.litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": extracted_text},
                ],
                api_key=self.api_key,
                **self.kwargs
            )
            content = response['choices'][0]['message']['content']
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
            guessed = json.loads(content)
            if (
                guessed.get("author", "").strip().lower() in {"unknown", "various"}
                or guessed.get("title", "").strip().lower() == "unknown"
                or not guessed.get("title", "").strip()
            ):
                return None
            return guessed
        except Exception as e:
            print(f"LitellmProvider error: {e}")
            return None

def get_llm_provider(model: str = None, **kwargs) -> 'LitellmProvider':
    """
    Purpose: Factory for LitellmProvider; encapsulates all provider/model/API key logic.
    Inputs: model (str, optional), kwargs (for future extensibility)
    Outputs: LitellmProvider instance
    Role: Centralizes all logic for LLM selection and secrets management. Main script is now fully agnostic.
    """
    import os
    DEFAULT_MODEL = 'claude-3-haiku-20240307'
    selected_model = model or DEFAULT_MODEL
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise RuntimeError("API key for Anthropic Claude not found. Please set ANTHROPIC_API_KEY in your environment or .env file.")
    return LitellmProvider(selected_model, api_key, **kwargs)
