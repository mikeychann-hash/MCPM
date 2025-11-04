#!/usr/bin/env python3
"""
CLI Bridge – Talk to MCPM like ChatGPT
"""

import subprocess
import json
import os
from pathlib import Path

def call_tool(tool, args):
    config_path = Path(os.getcwd()) / "fgd_config.yaml"
    cmd = ["python", "mcp_backend.py", str(config_path), "--tool", tool] + \
          [f"{k}={v}" for k, v in args.items()]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

print("MCPM CLI Bridge (type 'exit' to quit)")
while True:
    user = input("You: ")
    if user.lower() == "exit":
        break
    if "read" in user.lower():
        path = user.split()[-1]
        print("MCPM:", call_tool("read_file", {"filepath": path}))
    elif "list" in user.lower():
        print("MCPM:", call_tool("list_directory", {}))
    elif "diff" in user.lower():
        print("MCPM:", call_tool("git_diff", {}))
    elif "commit" in user.lower():
        msg = user.split("commit")[-1].strip()
        print("MCPM:", call_tool("git_commit", {"message": msg}))
    else:
        print("Supported: read <file>, list, diff, commit <msg>")