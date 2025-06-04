# Flexible LLM Provider System

## Overview

The Library Manager Lite now supports a configurable LLM provider system that allows you to set specific models, providers, and API keys for different workflows. This makes it easy to use the most appropriate model for each task.

## Configuration

The system uses a JSON configuration file located at `user_inputs/llm_config.json`. This file maps workflows to specific LLM providers, models, and API keys.

### Example Configuration

```json
{
  "workflows": {
    "identify": {
      "provider": "anthropic",
      "model": "claude-3-haiku-20240307",
      "api_key_env": "ANTHROPIC_API_KEY",
      "additional_params": {}
    },
    "embed": {
      "provider": "openai",
      "model": "text-embedding-small",
      "api_key_env": "OPENAI_API_KEY",
      "additional_params": {
        "dimensions": 1536
      }
    }
  },
  "defaults": {
    "provider": "anthropic",
    "model": "claude-3-haiku-20240307",
    "api_key_env": "ANTHROPIC_API_KEY"
  }
}
```

### Configuration Fields

- **workflows**: A dictionary mapping workflow names to their configurations
  - **provider**: The LLM provider (e.g., "anthropic", "openai")
  - **model**: The specific model to use
  - **api_key_env**: The environment variable name containing the API key
  - **additional_params**: Any additional parameters needed for the specific model/provider

- **defaults**: The default configuration to use when a workflow-specific configuration is not found

## Environment Variables

For each provider you want to use, you'll need to set the corresponding API key in your environment or `.env` file:

```
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key
```

## Usage in Code

The LLM provider system is designed to be simple to use:

```python
from adapters.llm_provider import get_llm_provider

# Get a provider for a specific workflow
llm = get_llm_provider(workflow="identify")

# Use the provider for that workflow
metadata = llm.extract_metadata(prompt, text)

# For embedding tasks
llm = get_llm_provider(workflow="embed")
embedding = llm.embed_text(text)
```

## Available Methods

The LLM provider now supports multiple methods for different tasks:

- **completion(prompt, user_content, output_format)**: General-purpose completion method
  - **output_format**: Optional format specifier ('json', 'text', or None)

- **extract_metadata(prompt, extracted_text)**: Extract metadata from text (used by PDF renamer)

- **embed_text(text)**: Generate embeddings for text (for semantic search)

## Adding New Workflows

To add a new workflow:

1. Add a new entry to the `workflows` section in `user_inputs/llm_config.json`
2. Set the appropriate provider, model, and API key environment variable
3. Add any additional parameters needed for that specific workflow
4. Use `get_llm_provider(workflow="your_workflow_name")` in your code

## Fallback Behavior

If a workflow configuration is not found, the system will fall back to the default configuration. If the default configuration is not defined, it will use Anthropic Claude 3 Haiku as the default model.
