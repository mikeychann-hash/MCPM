#!/usr/bin/env python3
"""
MCPM Setup & Diagnostics
Tests dependencies and provides helpful error messages
"""

import sys
import importlib

def _check_import(module_name, pip_name=None):
    """Test if a module can be imported"""
    pip_name = pip_name or module_name
    try:
        importlib.import_module(module_name)
        print(f"✓ {module_name} is installed")
        return True
    except ImportError:
        print(f"✗ {module_name} is NOT installed")
        print(f"  Install with: pip install {pip_name}")
        return False

def main():
    print("="*60)
    print("MCPM Dependency Check")
    print("="*60)
    print()

    all_ok = True

    # Check Python version
    print(f"Python version: {sys.version}")
    if sys.version_info < (3, 8):
        print("✗ Python 3.8+ is required")
        all_ok = False
    else:
        print("✓ Python version is compatible")
    print()

    # Check required modules
    print("Checking dependencies...")
    print()

    required = [
        ("PyQt6", "PyQt6"),
        ("yaml", "pyyaml"),
        ("watchdog", "watchdog"),
        ("aiohttp", "aiohttp"),
        ("dotenv", "python-dotenv"),
        ("mcp.server", "mcp"),
    ]

    for module, pip_name in required:
        if not _check_import(module, pip_name):
            all_ok = False

    print()
    print("="*60)

    if all_ok:
        print("✓ All dependencies are installed!")
        print()
        print("You can now run:")
        print("  python gui_main_pro.py    - Start the GUI")
        print("  python claude_bridge.py   - Start the CLI")
        print()
    else:
        print("✗ Some dependencies are missing")
        print()
        print("Install all at once:")
        print("  pip install PyQt6 pyyaml watchdog aiohttp python-dotenv mcp")
        print()

    print("="*60)

    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
