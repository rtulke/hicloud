#!/usr/bin/env python3
# lib/config.py - Configuration manager for hicloud

import os
import stat
import toml
from typing import Dict

from utils.constants import DEFAULT_CONFIG_PATH


class ConfigManager:
    """Manages configuration loading and generation"""
    
    @staticmethod
    def check_file_permissions(config_path: str) -> bool:
        """Check if the config file has 600 permissions"""
        if not os.path.exists(config_path):
            return False
            
        file_mode = os.stat(config_path).st_mode
        return (file_mode & stat.S_IRWXU) == stat.S_IRUSR | stat.S_IWUSR
    
    @staticmethod
    def load_config(config_path: str) -> Dict:
        """Load configuration from a TOML file"""
        if not os.path.exists(config_path):
            print(f"Configuration file not found: {config_path}")
            return {}
            
        # Check file permissions (must be 600)
        if not ConfigManager.check_file_permissions(config_path):
            print(f"WARNING: Insecure permissions on {config_path}")
            print("Please change permissions to 600 (chmod 600 filename)")
            print("Configuration file was not loaded for security reasons")
            return {}
            
        try:
            return toml.load(config_path)
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
            return {}
    
    @staticmethod
    def generate_config(output_path: str) -> bool:
        """Generate a sample configuration file"""
        sample_config = {
            "default": {
                "api_token": "your_api_token_here",
                "project_name": "default"
            },
            "project1": {
                "api_token": "project1_api_token",
                "project_name": "Production"
            },
            "project2": {
                "api_token": "project2_api_token",
                "project_name": "Development"
            }
        }
        
        try:
            with open(output_path, 'w') as f:
                toml.dump(sample_config, f)
                
            # Set permissions to 600
            os.chmod(output_path, stat.S_IRUSR | stat.S_IWUSR)
            print(f"Sample configuration generated at {output_path} with secure permissions")
            return True
        except Exception as e:
            print(f"Error generating configuration: {str(e)}")
            return False
