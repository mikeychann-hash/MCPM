#!/usr/bin/env python3
"""
Diagnostic script to test Grok API connection.
Run this to verify your XAI_API_KEY and connectivity.
"""

import os
import sys
import asyncio
import aiohttp
from pathlib import Path
from dotenv import load_dotenv

# Fix UTF-8 encoding on Windows
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}[OK] {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}[ERROR] {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}[WARN] {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.BLUE}[INFO] {text}{Colors.RESET}")

async def test_grok_connection():
    """Main test function."""
    print_header("Grok API Connection Diagnostic")
    print_info("Testing Grok-3 model (grok-beta was deprecated)")
    print_info("This test will verify your API key and connectivity")
    print()

    # Step 1: Check for .env file
    print_info("Step 1: Checking for .env file...")
    env_path = Path(".env")
    if env_path.exists():
        print_success(".env file found")
        load_dotenv()
    else:
        print_warning(".env file not found (optional if env vars set)")

    # Step 2: Check XAI_API_KEY
    print_info("Step 2: Checking XAI_API_KEY environment variable...")
    api_key = os.getenv("XAI_API_KEY")

    if not api_key:
        print_error("XAI_API_KEY not set!")
        print_info("Solutions:")
        print("  1. Create .env file with: XAI_API_KEY=your_key")
        print("  2. Or set environment variable:")
        print("     - Windows CMD: set XAI_API_KEY=your_key")
        print("     - Windows PS: $env:XAI_API_KEY='your_key'")
        print("     - Linux/Mac: export XAI_API_KEY='your_key'")
        return False

    print_success(f"XAI_API_KEY found: {api_key[:10]}...{api_key[-4:]}")

    # Step 3: Validate API key format
    print_info("Step 3: Validating API key format...")
    if api_key.startswith("xai-") or api_key.startswith("xai_"):
        print_success("API key format looks correct")
    else:
        print_warning("API key doesn't start with 'xai-' or 'xai_'")
        print_info("This might be okay, but verify with X.AI support if issues occur")

    # Step 4: Test network connectivity
    print_info("Step 4: Testing network connectivity to api.x.ai...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head("https://api.x.ai/", timeout=aiohttp.ClientTimeout(total=5)) as response:
                print_success(f"Can reach api.x.ai (status: {response.status})")
    except asyncio.TimeoutError:
        print_error("Connection timeout - check internet connection")
        return False
    except Exception as e:
        print_error(f"Cannot reach api.x.ai: {e}")
        print_warning("Check firewall/proxy settings")
        return False

    # Step 5: Test actual Grok API call
    print_info("Step 5: Testing actual Grok API call...")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "grok-3",
        "messages": [{"role": "user", "content": "Say 'Connection successful' in one word."}]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.x.ai/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    message = data['choices'][0]['message']['content']
                    print_success(f"Grok API responded: '{message}'")
                    return True
                elif response.status == 401:
                    print_error("API returned 401 Unauthorized")
                    print_info("Reasons:")
                    print("  - API key is invalid or expired")
                    print("  - API key doesn't have proper permissions")
                    print("  - Account might be suspended")
                    text = await response.text()
                    print_info(f"Error details: {text}")
                    return False
                elif response.status == 429:
                    print_error("API returned 429 Rate Limited")
                    print_info("Wait 1-2 minutes and try again")
                    return False
                else:
                    text = await response.text()
                    print_error(f"API returned {response.status}: {text}")
                    return False
    except asyncio.TimeoutError:
        print_error("Request timeout - Grok API took too long to respond")
        return False
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return False

async def main():
    """Run all tests."""
    try:
        success = await test_grok_connection()

        print_header("Test Summary")

        if success:
            print_success("All tests passed! Grok connection is working.")
            print_info("You can now use Grok in MCPM:")
            print("  1. python gui_main_pro.py")
            print("  2. Click 'Browse' and select a folder")
            print("  3. Select 'grok' from the provider dropdown")
            print("  4. Click 'Start Server'")
            return 0
        else:
            print_error("Some tests failed. See above for details.")
            return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
