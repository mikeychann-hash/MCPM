#!/usr/bin/env python3
"""Test script to verify path validation logic"""

import platform
import yaml
from pathlib import Path

def validate_paths(config):
    """Validate paths and warn about OS mismatches"""
    current_os = platform.system()
    watch_dir_str = config.get('watch_dir', '')

    print(f"Current OS: {current_os}")
    print(f"Configured watch_dir: {watch_dir_str}")
    print()

    # Check for Windows path patterns on non-Windows systems
    is_windows_path = (
        ':' in watch_dir_str and watch_dir_str[1:3] == ':\\' or
        ':' in watch_dir_str and watch_dir_str[1:3] == ':/'
    )

    if is_windows_path and current_os != 'Windows':
        print("=" * 80)
        print("🚨 CRITICAL PATH CONFIGURATION ERROR 🚨")
        print("=" * 80)
        print(f"Running on: {current_os}")
        print(f"Config has Windows path: {watch_dir_str}")
        print("")
        print("This will cause ALL write operations to fail silently!")
        print("Files will be written to unexpected locations or not at all.")
        print("")
        print("To fix: Update fgd_config.yaml with the correct path for your OS:")
        print(f"  watch_dir: /home/user/your-project-directory")
        print("=" * 80)

        # Try to resolve the path anyway and show where it would go
        try:
            resolved = Path(watch_dir_str).resolve()
            print(f"Path would resolve to: {resolved}")
            if not resolved.exists():
                print(f"⚠️  WARNING: This path does not exist!")
        except Exception as e:
            print(f"⚠️  Path resolution failed: {e}")
        print("=" * 80)

    # Check if path exists
    try:
        path = Path(watch_dir_str).resolve()
        print(f"Resolved path: {path}")
        if not path.exists():
            print("=" * 80)
            print(f"⚠️  WARNING: watch_dir does not exist: {path}")
            print("Write operations will fail until this directory is created.")
            print("=" * 80)
        else:
            print("✅ Path exists and is accessible")
    except Exception as e:
        print(f"Failed to validate watch_dir: {e}")

if __name__ == "__main__":
    with open('fgd_config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    validate_paths(config)
