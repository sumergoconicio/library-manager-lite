"""
ports/profile_loader.py | Library Profile Loader
Purpose: Load library profile settings from folder_paths.json based on profile name
Author: ChAI-Engine (chaiji)
Last-Updated: 2025-06-06
Non-Std Deps: None
Abstract Spec: Loads profile-specific settings from folder_paths.json, with fallback to DEFAULT_LIBRARY_PROFILE in .env
"""

import os
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_profile_name(args: Optional[argparse.Namespace] = None) -> str:
    """
    Purpose: Determine which profile to use based on CLI args and environment variables.
    Inputs: args (argparse.Namespace) - Command line arguments, may contain 'profile' attribute.
    Outputs: profile_name (str) - Name of the profile to use.
    Role: Centralizes profile selection logic with CLI args taking precedence over env vars.
    """
    # Check CLI args first (highest priority)
    if args and hasattr(args, 'profile') and args.profile:
        return args.profile
    
    # Fall back to environment variable
    env_profile = os.environ.get('DEFAULT_LIBRARY_PROFILE')
    if env_profile:
        return env_profile
    
    # Default fallback if nothing else is specified
    # Use first profile in the config file instead of hardcoding "default"
    config_path = Path(__file__).parent.parent / "user_inputs" / "folder_paths.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            if config and isinstance(config, dict) and len(config) > 0:
                # Return the first profile name in the config
                return list(config.keys())[0]
    except Exception:
        pass
    
    # Last resort fallback
    return "default"


def load_profile_config(profile_name: str = None, args: Optional[argparse.Namespace] = None) -> Dict[str, Any]:
    """
    Purpose: Load the specified profile configuration from folder_paths.json.
    Inputs: profile_name (str) - Name of the profile to load, or None to auto-detect.
            args (argparse.Namespace) - Command line arguments, used if profile_name is None.
    Outputs: profile_config (dict) - Configuration dictionary for the specified profile.
    Role: Provides profile-specific configuration to other modules.
    """
    # Determine profile name if not provided
    if profile_name is None:
        profile_name = get_profile_name(args)
    
    # Load the config file using absolute path
    config_path = Path(__file__).parent.parent / "user_inputs" / "folder_paths.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # Extract the profile config
        if profile_name in config:
            return config[profile_name]
        else:
            available_profiles = list(config.keys())
            if len(available_profiles) > 0:
                # Suggest using an available profile
                first_profile = available_profiles[0]
                error_msg = f"Profile '{profile_name}' not found in folder_paths.json. Available profiles: {', '.join(available_profiles)}"
                error_msg += f"\nTry using --profile {first_profile} or set DEFAULT_LIBRARY_PROFILE={first_profile} in .env"
                raise ValueError(error_msg)
            else:
                raise ValueError(f"No profiles found in folder_paths.json. Please add at least one profile to the config file.")
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found at {config_path}. Please create this file with at least one profile.")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in {config_path}. Please check the file format.")
    except Exception as e:
        raise ValueError(f"Error loading profile config: {str(e)}")


def add_profile_arg(parser: argparse.ArgumentParser) -> None:
    """
    Purpose: Add profile selection argument to an ArgumentParser.
    Inputs: parser (argparse.ArgumentParser) - Parser to add the argument to.
    Outputs: None (modifies parser in-place).
    Role: Standardizes how profile selection is exposed in CLI interfaces.
    """
    parser.add_argument("--profile", type=str, help="Library profile to use (from folder_paths.json)")
