#!/usr/bin/env python3
"""
CLI Bridge – Talk to MCPM like ChatGPT
"""

import subprocess
import json
import os
import sys
import shlex
from pathlib import Path

def call_tool(tool, args):
    """Call an MCPM backend tool with proper error handling"""
    config_path = Path(os.getcwd()) / "fgd_config.yaml"

    if not config_path.exists():
        return f"Error: Config file not found at {config_path}"

    try:
        cmd = ["python", "mcp_backend.py", str(config_path), "--tool", tool] + \
              [f"{k}={v}" for k, v in args.items()]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            return f"Error: {result.stderr or 'Tool execution failed'}"

        return result.stdout or "No output"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        return f"Error: {e}"

def parse_command(user_input):
    """Parse user input with proper handling of quoted paths"""
    try:
        parts = shlex.split(user_input)
        return parts
    except ValueError:
        # If shlex fails, fall back to simple split
        return user_input.split()

print("="*60)
print("MCPM CLI Bridge - Interactive File Assistant")
print("="*60)
print("Commands:")
print("  read <file>       - Read a file")
print("  list [path]       - List directory contents")
print("  diff [files...]   - Show git diff")
print("  commit <msg>      - Commit changes with message")
print("  help              - Show this help")
print("  exit              - Quit")
print("="*60)

while True:
    try:
        user = input("\nYou: ").strip()

        if not user:
            continue

        if user.lower() in ["exit", "quit", "q"]:
            print("Goodbye!")
            break

        if user.lower() in ["help", "?"]:
            print("\nSupported commands:")
            print("  read <file>       - Read a file (supports quoted paths)")
            print("  list [path]       - List directory (default: current)")
            print("  diff              - Show git diff")
            print("  commit <msg>      - Commit with message")
            continue

        parts = parse_command(user)
        command = parts[0].lower() if parts else ""

        if command == "read" or "read" in user.lower():
            if len(parts) < 2:
                print("MCPM: Error - Please specify a file path")
                continue
            filepath = parts[-1]
            print("MCPM:", call_tool("read_file", {"filepath": filepath}))

        elif command == "list" or "list" in user.lower():
            path = parts[1] if len(parts) > 1 else "."
            print("MCPM:", call_tool("list_directory", {"path": path}))

        elif command == "diff" or "diff" in user.lower():
            print("MCPM:", call_tool("git_diff", {}))

        elif command == "commit" or "commit" in user.lower():
            # Extract message after "commit"
            msg_start = user.lower().find("commit") + 6
            msg = user[msg_start:].strip()
            if not msg:
                print("MCPM: Error - Please provide a commit message")
                continue
            print("MCPM:", call_tool("git_commit", {"message": msg}))

        else:
            print("MCPM: Unknown command. Type 'help' for available commands.")

    except KeyboardInterrupt:
        print("\n\nInterrupted. Type 'exit' to quit.")
    except Exception as e:
        print(f"MCPM: Error - {e}")