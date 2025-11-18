# MCPM TODO - Prioritized Action Items

**Last Updated**: 2025-11-18
**Total Issues**: 32 (8 P0, 10 P1, 14 P2)
**Branch**: `claude/mcpm-autonomous-refactor-01XwFQpU2BkXsbrvSNTuiNpA`

---

## Priority Legend

- **P0 (Critical)**: Blocks production use, causes crashes, data loss, or security issues
- **P1 (Important)**: Affects reliability, causes silent failures, or major UX issues
- **P2 (Nice to Have)**: Improvements, optimizations, or polish

---

## P0 - CRITICAL ISSUES (Do First - Week 1)

### Estimated Time: 8-12 hours

### Code Fixes

- [ ] **P0-1**: Fix bare except clauses in `mcp_backend.py`
  - **File**: `/home/user/MCPM/mcp_backend.py`
  - **Lines**: 121, 128 (FileLock.__exit__)
  - **Issue**: Catches ALL exceptions including SystemExit, masks critical errors
  - **Impact**: Makes debugging impossible, violates PEP 8
  - **Fix**:
    ```python
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self._lock.release()
        except (RuntimeError, ValueError) as e:
            logger.warning(f"Lock release failed: {e}")
        return False  # Don't suppress exceptions
    ```
  - **Test**: Verify lock releases properly on normal and error cases
  - **Time**: 30 minutes

- [ ] **P0-2**: Add exception handling for JSON parsing in approval monitor
  - **File**: `/home/user/MCPM/mcp_backend.py`
  - **Line**: 637
  - **Issue**: JSONDecodeError crashes approval loop, leaves edits in limbo
  - **Impact**: Approval workflow completely breaks on corrupted file
  - **Fix**:
    ```python
    try:
        approval_data = json.loads(approval_file.read_text())
    except json.JSONDecodeError as e:
        logger.error(f"Corrupted approval file {approval_file}: {e}")
        approval_file.unlink(missing_ok=True)  # Clean up corrupted file
        pending_file.unlink(missing_ok=True)
        continue
    except Exception as e:
        logger.error(f"Unexpected error reading approval: {e}")
        continue
    ```
  - **Test**: Create corrupted .fgd_approval.json and verify graceful handling
  - **Time**: 30 minutes

- [ ] **P0-3**: Add type hints to increase coverage from 32% to 80%+
  - **Files**: All Python files (mcp_backend.py, server.py, gui_main_pro.py, claude_bridge.py)
  - **Issue**: Only 32-34% of functions have type hints
  - **Impact**: No mypy/type checking, limited IDE autocomplete
  - **Strategy**:
    1. Start with mcp_backend.py (highest priority)
    2. Add return types to all functions
    3. Add parameter types
    4. Use typing.Optional, typing.Union, typing.Dict, etc.
  - **Example**:
    ```python
    from typing import Dict, List, Optional, Any

    async def list_directory(
        self,
        path: str,
        include_hidden: bool = False
    ) -> Dict[str, Any]:
        """List directory contents with gitignore filtering."""
        ...
    ```
  - **Test**: Run `mypy mcp_backend.py` and fix all type errors
  - **Time**: 4-6 hours

- [ ] **P0-4**: Handle JSON-RPC exceptions gracefully instead of re-raising
  - **File**: `/home/user/MCPM/mcp_backend.py`
  - **Line**: 1328
  - **Issue**: `raise Exception(f"Unsupported tool: {name}")` crashes server
  - **Impact**: Invalid tool requests crash entire MCP server
  - **Fix**:
    ```python
    # Instead of raise Exception:
    logger.warning(f"Unsupported tool requested: {name}")
    available = [t.name for t in await list_tools()]
    return {
        "error": f"Unsupported tool: {name}",
        "available_tools": available,
        "message": f"Please use one of: {', '.join(available)}"
    }
    ```
  - **Test**: Send invalid tool request via MCP protocol
  - **Time**: 30 minutes

- [ ] **P0-5**: Fix daemon thread race condition on shutdown
  - **File**: `/home/user/MCPM/gui_main_pro.py`
  - **Line**: 1796 (_read_stdout method)
  - **Issue**: Daemon thread accesses self.process which might be None during shutdown
  - **Impact**: AttributeError crashes on GUI shutdown
  - **Fix**:
    ```python
    def _read_stdout(self):
        """Background thread to read stdout from MCP process."""
        try:
            process = self.process  # Capture reference
            if not process or not process.stdout:
                logger.debug("No process or stdout available")
                return

            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                # ... existing processing ...
        except Exception as e:
            logger.debug(f"Stdout reader stopped: {e}")
        finally:
            logger.debug("Stdout reader thread exiting")
    ```
  - **Test**: Start GUI, start MCP process, close GUI rapidly, check for AttributeError
  - **Time**: 45 minutes

- [ ] **P0-6**: Prevent subprocess output deadlock
  - **File**: `/home/user/MCPM/gui_main_pro.py`
  - **Lines**: 1862-1869 (subprocess.Popen call)
  - **Issue**: Separate stdout/stderr pipes can deadlock if buffers fill
  - **Impact**: Process hangs indefinitely on large output
  - **Fix**:
    ```python
    self.process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Merge stderr into stdout
        stdin=subprocess.PIPE,
        bufsize=0,  # Unbuffered
        text=True,
        env=env
    )
    # Remove separate stderr thread since it's merged
    ```
  - **Test**: Generate tool with large stderr output, verify no deadlock
  - **Time**: 1 hour

- [ ] **P0-7**: Handle file lock timeout properly (don't return empty dict)
  - **File**: `/home/user/MCPM/mcp_backend.py`
  - **Lines**: 153-155 (FileLock.try_lock)
  - **Issue**: Returns empty dict {} on timeout, causes silent data loss
  - **Impact**: Memory operations silently fail, data lost
  - **Fix**:
    ```python
    if not self._lock.acquire(timeout=timeout):
        raise TimeoutError(
            f"Failed to acquire lock on {self.filepath} after {timeout}s. "
            f"Another process may be holding the lock."
        )
    return True
    ```
  - **Test**: Simulate lock contention, verify proper error propagation
  - **Time**: 30 minutes

- [ ] **P0-8**: Remove hardcoded Windows paths from fgd_config.yaml
  - **File**: `/home/user/MCPM/fgd_config.yaml`
  - **Lines**: All hardcoded paths
  - **Issue**: Absolute Windows paths break on Linux/macOS
  - **Impact**: Cannot run on Linux or macOS
  - **Fix**:
    ```yaml
    # Change from:
    project_root: "C:\\Users\\mikey\\Desktop\\MCPM"
    watch_dirs:
      - "C:\\Users\\mikey\\Desktop\\MCPM"

    # To:
    project_root: "."
    watch_dirs:
      - "."
      - "./src"
    ```
  - **Alternative**: Rename to `fgd_config.personal.yaml` and gitignore it
  - **Test**: Run on Linux, verify paths work
  - **Time**: 15 minutes

---

## P1 - IMPORTANT ISSUES (Week 2-3)

### Estimated Time: 20-30 hours

### Code Reliability

- [ ] **P1-1**: Add subprocess returncode validation (4 locations)
  - **File**: `/home/user/MCPM/mcp_backend.py`
  - **Lines**: 773 (git_diff), 1130 (git_commit), 1155 (git_log), 1189 (other git ops)
  - **Issue**: subprocess.run() return codes not checked
  - **Impact**: Silent git command failures return "No commits yet" even on errors
  - **Fix** (apply to all 4 locations):
    ```python
    result = subprocess.run(
        ["git", "diff"],
        capture_output=True,
        text=True,
        cwd=project_root
    )
    if result.returncode != 0:
        logger.error(f"git diff failed (code {result.returncode}): {result.stderr}")
        return {
            "error": f"git command failed: {result.stderr}",
            "returncode": result.returncode
        }
    return result.stdout
    ```
  - **Test**: Run git commands in non-git directory, verify error messages
  - **Time**: 2 hours

- [ ] **P1-2**: Improve async exception handling in _retry_request
  - **File**: `/home/user/MCPM/mcp_backend.py`
  - **Lines**: 382-396
  - **Issue**: Only catches aiohttp.ClientError, missing other aiohttp exceptions
  - **Impact**: InvalidURL, ClientPayloadError, ClientSSLError crash immediately
  - **Fix**:
    ```python
    except (
        aiohttp.ClientError,
        aiohttp.InvalidURL,
        aiohttp.ClientPayloadError,
        aiohttp.ClientSSLError,
        aiohttp.ServerTimeoutError,
        asyncio.TimeoutError
    ) as e:
        logger.error(f"Request failed (attempt {attempt + 1}): {type(e).__name__}: {e}")
        if attempt < retries - 1:
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff
        else:
            raise
    ```
  - **Test**: Simulate various aiohttp errors, verify retry logic
  - **Time**: 1 hour

- [ ] **P1-3**: Verify memory file initialization
  - **File**: `/home/user/MCPM/mcp_backend.py`
  - **Line**: 530 (MemoryStore.__init__)
  - **Issue**: Memory file creation not verified for success
  - **Impact**: Memory operations fail silently if watch_dir is invalid
  - **Fix**:
    ```python
    self.memory_file = Path(watch_dir) / ".fgd_memory.json"
    if not self.memory_file.parent.exists():
        raise ValueError(f"Watch directory does not exist: {watch_dir}")
    if not self.memory_file.parent.is_dir():
        raise ValueError(f"Watch directory is not a directory: {watch_dir}")

    # Try to create/read memory file
    try:
        if not self.memory_file.exists():
            self.memory_file.write_text("{}")
        self.memory_file.read_text()  # Verify readable
    except (OSError, PermissionError) as e:
        raise ValueError(f"Cannot access memory file {self.memory_file}: {e}")
    ```
  - **Test**: Initialize with invalid watch_dir, verify error message
  - **Time**: 1 hour

- [ ] **P1-4**: Make CLI timeout configurable
  - **File**: `/home/user/MCPM/claude_bridge.py`
  - **Line**: 23
  - **Issue**: 60-second timeout too short for long operations (git clone, large file ops)
  - **Impact**: Long operations fail even though they would succeed
  - **Fix**:
    ```python
    import os

    TIMEOUT = int(os.getenv("MCPM_CLI_TIMEOUT", "300"))  # Default 5 minutes

    @click.option(
        '--timeout',
        default=TIMEOUT,
        help='Maximum time to wait for operation (seconds)'
    )
    def cli(timeout):
        """MCPM command-line interface."""
        # Use timeout parameter in operations
    ```
  - **Add to .env.example**: `MCPM_CLI_TIMEOUT=300`
  - **Test**: Run long operation with different timeouts
  - **Time**: 1 hour

- [ ] **P1-5**: Add tool argument validation (all tool handlers)
  - **File**: `/home/user/MCPM/mcp_backend.py`
  - **Lines**: All @server.call_tool() handlers
  - **Issue**: No KeyError handling for missing required arguments
  - **Impact**: Crashes on malformed tool requests
  - **Fix** (example for read_file):
    ```python
    @self.server.call_tool()
    async def call_tool(name: str, arguments: dict):
        try:
            if name == "read_file":
                path = arguments.get("path")
                if not path:
                    return {"error": "Missing required argument: path"}
                # ... rest of implementation ...
        except KeyError as e:
            logger.error(f"Missing argument in tool call: {e}")
            return {"error": f"Missing required argument: {e}"}
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}", exc_info=True)
            return {"error": f"Tool execution failed: {str(e)}"}
    ```
  - **Test**: Send tool requests with missing arguments
  - **Time**: 2 hours

- [ ] **P1-6**: Remove blocking calls from async context
  - **File**: `/home/user/MCPM/mcp_backend.py`
  - **Lines**: Git operations, file I/O in async functions
  - **Issue**: subprocess.run() blocks event loop for 30s+ on slow git operations
  - **Impact**: Entire server freezes during git operations
  - **Fix**:
    ```python
    import asyncio

    # Instead of:
    result = subprocess.run(["git", "diff"], capture_output=True, text=True)

    # Use:
    result = await asyncio.create_subprocess_exec(
        "git", "diff",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=project_root
    )
    stdout, stderr = await result.communicate()
    if result.returncode != 0:
        return {"error": stderr.decode()}
    return stdout.decode()
    ```
  - **Test**: Run git diff during other MCP operations, verify no blocking
  - **Time**: 3 hours

- [ ] **P1-7**: Implement memory size limits
  - **File**: `/home/user/MCPM/mcp_backend.py`
  - **Lines**: MemoryStore class
  - **Issue**: Memory files can grow to 100MB+ before pruning
  - **Impact**: Excessive disk usage, slow JSON parsing
  - **Fix**:
    ```python
    class MemoryStore:
        MAX_MEMORY_SIZE_MB = 10  # 10MB limit
        MAX_ENTRIES = 1000       # Keep as backup limit

        def _should_prune(self) -> bool:
            """Check if pruning is needed."""
            if len(self.memories) > self.MAX_ENTRIES:
                return True

            # Check file size
            if self.memory_file.exists():
                size_mb = self.memory_file.stat().st_size / (1024 * 1024)
                if size_mb > self.MAX_MEMORY_SIZE_MB:
                    logger.warning(f"Memory file {size_mb:.1f}MB, pruning...")
                    return True
            return False
    ```
  - **Test**: Generate large memory entries, verify pruning at 10MB
  - **Time**: 1.5 hours

- [ ] **P1-8**: Add file locking to approval workflow
  - **File**: `/home/user/MCPM/mcp_backend.py`, `/home/user/MCPM/gui_main_pro.py`
  - **Lines**: Approval file read/write operations
  - **Issue**: Race condition between approval file write (GUI) and read (backend)
  - **Impact**: Edit requests can be lost or partially read
  - **Fix**:
    ```python
    from filelock import FileLock

    # In GUI when writing approval:
    approval_lock = FileLock(".fgd_approval.json.lock", timeout=5)
    with approval_lock:
        with open(".fgd_approval.json", "w") as f:
            json.dump(approval_data, f)

    # In backend when reading approval:
    approval_lock = FileLock(approval_file.with_suffix(".json.lock"), timeout=5)
    with approval_lock:
        approval_data = json.loads(approval_file.read_text())
    ```
  - **Test**: Stress test with rapid approval cycles
  - **Time**: 2 hours

- [ ] **P1-9**: Add git user configuration validation
  - **File**: `/home/user/MCPM/mcp_backend.py`
  - **Lines**: git_commit function
  - **Issue**: git commit fails without user.name/user.email configured
  - **Impact**: Commits fail with cryptic error messages
  - **Fix**:
    ```python
    async def git_commit(message: str, project_root: str) -> dict:
        """Commit changes with validation."""
        # Check git user configuration
        user_name = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True, text=True, cwd=project_root
        )
        user_email = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True, text=True, cwd=project_root
        )

        if not user_name.stdout.strip() or not user_email.stdout.strip():
            return {
                "error": "Git user not configured",
                "help": "Run: git config user.name 'Your Name' && git config user.email 'you@example.com'"
            }

        # Proceed with commit...
    ```
  - **Test**: Try commit without git config, verify helpful error
  - **Time**: 1 hour

- [ ] **P1-10**: Add LLM context size limits
  - **File**: `/home/user/MCPM/mcp_backend.py`
  - **Lines**: llm_query function
  - **Issue**: Can send unlimited context, exceeding provider token limits
  - **Impact**: Silent failures or truncated responses
  - **Fix**:
    ```python
    import tiktoken

    MAX_CONTEXT_TOKENS = {
        "grok": 32000,
        "openai": 8000,
        "claude": 100000,
        "ollama": 4096
    }

    async def llm_query(prompt: str, context: str, provider: str) -> dict:
        """Query LLM with context size validation."""
        max_tokens = MAX_CONTEXT_TOKENS.get(provider, 4096)

        # Estimate tokens (rough approximation: 1 token ≈ 4 chars)
        estimated_tokens = len(prompt + context) // 4

        if estimated_tokens > max_tokens:
            logger.warning(f"Context too large ({estimated_tokens} tokens), truncating to {max_tokens}")
            # Truncate context intelligently (keep recent entries)
            context = context[-(max_tokens * 4):]

        # Proceed with query...
    ```
  - **Test**: Send oversized context, verify truncation
  - **Time**: 2 hours

### Configuration

- [ ] **P1-11**: Create .env from .env.example
  - **File**: `/home/user/MCPM/.env` (create)
  - **Issue**: .env file missing (users must create manually)
  - **Fix**: Document in README that users must copy .env.example to .env
  - **Time**: 5 minutes

- [ ] **P1-12**: Create requirements-lock.txt
  - **Commands**:
    ```bash
    cd /home/user/MCPM
    pip freeze > requirements-lock.txt
    ```
  - **Issue**: No lock file means non-reproducible builds
  - **Impact**: Different versions installed across environments
  - **Test**: Install from requirements-lock.txt in clean virtualenv
  - **Time**: 15 minutes

- [ ] **P1-13**: Create start.sh for Linux/macOS
  - **File**: `/home/user/MCPM/start.sh` (create)
  - **Issue**: No Linux launcher script
  - **Fix**:
    ```bash
    #!/bin/bash
    set -e

    # MCPM Startup Script for Linux/macOS

    echo "Starting MCPM v6.0..."

    # Check Python version
    python3 --version || { echo "Python 3.10+ required"; exit 1; }

    # Check virtual environment
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtualenv
    source venv/bin/activate

    # Install dependencies
    echo "Installing dependencies..."
    pip install -q -r requirements.txt

    # Check .env file
    if [ ! -f ".env" ]; then
        echo "ERROR: .env file not found!"
        echo "Please copy .env.example to .env and configure your API keys"
        exit 1
    fi

    # Start GUI
    echo "Launching MCPM GUI..."
    python gui_main_pro.py
    ```
  - **Make executable**: `chmod +x start.sh`
  - **Test**: Run on Linux, verify it works
  - **Time**: 30 minutes

- [ ] **P1-14**: Update quick_start.bat
  - **File**: `/home/user/MCPM/quick_start.bat`
  - **Issue**: References v4, outdated
  - **Fix**: Update to match start.sh logic for Windows
  - **Time**: 30 minutes

### Branding

- [ ] **P1-15**: Create LICENSE file
  - **File**: `/home/user/MCPM/LICENSE` (create)
  - **Issue**: No LICENSE file in repository
  - **Fix**:
    ```
    MIT License

    Copyright (c) 2024 MCPM Contributors

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
    ```
  - **Time**: 10 minutes

- [ ] **P1-16**: Update README.md placeholder license text
  - **File**: `/home/user/MCPM/README.md`
  - **Line**: 1047
  - **Current**: `[Add your license here]`
  - **Fix**: `MIT License - See [LICENSE](LICENSE) file for details.`
  - **Time**: 5 minutes

- [ ] **P1-17**: Update README.md placeholder contact email
  - **File**: `/home/user/MCPM/README.md`
  - **Line**: 1056
  - **Current**: `- **Email**: [Add contact email]`
  - **Fix**: `- **Email**: support@mcpm.dev` (or actual email)
  - **Time**: 5 minutes

- [ ] **P1-18**: Update mcp_backend.py version to v6.0
  - **File**: `/home/user/MCPM/mcp_backend.py`
  - **Line**: 3 (module docstring)
  - **Current**: `MCPM v5.0 – Full Filesystem Co‑Pilot`
  - **Fix**: `MCPM v6.0 – Full Filesystem Co‑Pilot`
  - **Time**: 5 minutes

- [ ] **P1-19**: Add __version__ constants to all modules
  - **Files**: mcp_backend.py, server.py, gui_main_pro.py, claude_bridge.py
  - **Issue**: No version constants for programmatic access
  - **Fix** (add to each file):
    ```python
    __version__ = "6.0.0"
    __title__ = "MCPM"
    __description__ = "Model Context Protocol Manager - Neo Cyber AI Co-Pilot"
    __author__ = "MCPM Contributors"
    ```
  - **Time**: 30 minutes

---

## P2 - NICE TO HAVE (Month 1-2)

### Estimated Time: 60-100+ hours

### Testing

- [ ] **P2-1**: Add unit tests for file operation tools
  - **File**: `tests/unit/test_tools_file_ops.py` (create)
  - **Tests**: list_directory, read_file, write_file, create_directory
  - **Time**: 4 hours

- [ ] **P2-2**: Add unit tests for git operation tools
  - **File**: `tests/unit/test_tools_git.py` (create)
  - **Tests**: git_diff, git_commit, git_log
  - **Time**: 4 hours

- [ ] **P2-3**: Add unit tests for LLM tool
  - **File**: `tests/unit/test_tools_llm.py` (create)
  - **Tests**: llm_query with different providers, retry logic
  - **Time**: 3 hours

- [ ] **P2-4**: Add unit tests for memory store
  - **File**: `tests/unit/test_memory_store.py` (create)
  - **Tests**: Memory CRUD, pruning, file locking
  - **Time**: 3 hours

- [ ] **P2-5**: Add integration tests for MCP protocol
  - **File**: `tests/integration/test_mcp_protocol.py` (create)
  - **Tests**: Tool discovery, tool execution, error handling
  - **Time**: 4 hours

- [ ] **P2-6**: Add integration tests for approval workflow
  - **File**: `tests/integration/test_approval_workflow.py` (create)
  - **Tests**: Edit request, approval, rejection, timeout
  - **Time**: 4 hours

- [ ] **P2-7**: Achieve 70%+ code coverage
  - **Command**: `pytest --cov=. --cov-report=html`
  - **Time**: 8+ hours

### Documentation

- [ ] **P2-8**: Reorganize documentation into docs/ directory
  - **Structure**:
    ```
    docs/
    ├── README.md
    ├── getting-started/
    │   ├── INSTALLATION.md
    │   ├── QUICK_START.md
    │   └── CONFIGURATION.md
    ├── guides/
    │   ├── USAGE.md
    │   ├── TOOLS.md
    │   ├── LLM_PROVIDERS.md
    │   └── DOCKER.md
    ├── api/
    │   ├── MCP_PROTOCOL.md
    │   ├── REST_API.md
    │   └── TOOL_REFERENCE.md
    ├── development/
    │   ├── ARCHITECTURE.md
    │   ├── CONTRIBUTING.md
    │   ├── TESTING.md
    │   └── SECURITY.md
    └── roadmap/
        ├── v6.0-completed.md
        ├── v6.1-planned.md
        └── FUTURE.md
    ```
  - **Time**: 6 hours

- [ ] **P2-9**: Create GETTING_STARTED.md
  - **File**: `docs/getting-started/GETTING_STARTED.md`
  - **Content**: Quick 5-minute setup guide
  - **Time**: 2 hours

- [ ] **P2-10**: Create TOOL_REFERENCE.md
  - **File**: `docs/api/TOOL_REFERENCE.md`
  - **Content**: Complete reference for all 9 tools with examples
  - **Time**: 3 hours

- [ ] **P2-11**: Create CHANGELOG.md
  - **File**: `/home/user/MCPM/CHANGELOG.md`
  - **Content**: Version history, breaking changes, migrations
  - **Time**: 2 hours

- [ ] **P2-12**: Streamline README.md to 200-300 lines
  - **File**: `/home/user/MCPM/README.md`
  - **Current**: 1,070 lines
  - **Strategy**: Move detailed sections to docs/, keep overview in README
  - **Time**: 3 hours

### Performance Optimizations

- [ ] **P2-13**: Consolidate file polling loops
  - **File**: `/home/user/MCPM/gui_main_pro.py`
  - **Issue**: 3 separate polling timers (approval, watchdog, memory)
  - **Opportunity**: Single event loop with 67% I/O reduction
  - **Fix**: Use asyncio event loop or single QTimer with multiplexing
  - **Time**: 4 hours

- [ ] **P2-14**: Implement git operation caching
  - **File**: `/home/user/MCPM/mcp_backend.py`
  - **Opportunity**: Cache git status, diff for 1-2 seconds
  - **Gain**: 90% subprocess reduction for rapid operations
  - **Time**: 3 hours

- [ ] **P2-15**: Add watchdog directory filtering
  - **File**: `/home/user/MCPM/gui_main_pro.py`
  - **Opportunity**: Filter events at watchdog level, not in handler
  - **Gain**: 10x fewer events processed
  - **Time**: 2 hours

- [ ] **P2-16**: Benchmark and profile hot paths
  - **Tools**: cProfile, py-spy, memory_profiler
  - **Targets**: Memory operations, file I/O, git operations
  - **Time**: 4 hours

### Extensibility

- [ ] **P2-17**: Design plugin architecture
  - **Goal**: Allow dynamic tool registration from external modules
  - **Design**: Plugin discovery, versioning, dependency management
  - **Time**: 8 hours

- [ ] **P2-18**: Implement dynamic tool registration
  - **Feature**: Load tools from plugins/ directory at runtime
  - **Time**: 6 hours

- [ ] **P2-19**: Add batch tool endpoint
  - **Feature**: Execute multiple tools in single MCP request
  - **Use case**: Reduce round-trip latency for multi-step operations
  - **Time**: 4 hours

- [ ] **P2-20**: Add tool versioning support
  - **Feature**: Version tools independently, support multiple versions
  - **Time**: 4 hours

- [ ] **P2-21**: Add tool response caching
  - **Feature**: Cache read_file, list_directory responses for 5-10s
  - **Time**: 3 hours

### Enhancement

- [ ] **P2-22**: Create brand assets
  - **Files**:
    - `assets/logo/logo.svg`
    - `assets/logo/logo-icon.svg`
    - `assets/logo/favicon.ico`
    - `assets/logo/favicon.png`
    - `assets/logo/banner.png`
  - **Time**: 6 hours (requires design work)

- [ ] **P2-23**: Add CI/CD workflows
  - **File**: `.github/workflows/ci.yml`
  - **Jobs**: Lint, type check, test, build, deploy
  - **Time**: 4 hours

- [ ] **P2-24**: Create pyproject.toml for modern packaging
  - **File**: `/home/user/MCPM/pyproject.toml`
  - **Content**: PEP 517/518 compliant packaging
  - **Time**: 2 hours

- [ ] **P2-25**: Add pre-commit hooks
  - **File**: `.pre-commit-config.yaml`
  - **Hooks**: black, ruff, mypy, pytest
  - **Time**: 2 hours

- [ ] **P2-26**: Add GitHub issue templates
  - **Files**:
    - `.github/ISSUE_TEMPLATE/bug_report.md`
    - `.github/ISSUE_TEMPLATE/feature_request.md`
  - **Time**: 1 hour

- [ ] **P2-27**: Add standardized output validation
  - **Issue**: Tool outputs inconsistent (some return strings, some dicts)
  - **Fix**: Standardize all tool outputs to dict with status, data, error fields
  - **Time**: 3 hours

- [ ] **P2-28**: Add rate limiting to MCP server
  - **Feature**: Prevent abuse via rate limiting on tool calls
  - **Time**: 2 hours

- [ ] **P2-29**: Add audit logging for file modifications
  - **Feature**: Log all write_file, edit_file operations to audit trail
  - **Time**: 2 hours

- [ ] **P2-30**: Add secrets encryption at rest
  - **Feature**: Encrypt .env file, memory files with user passphrase
  - **Time**: 6 hours

---

## Development Dependencies (Optional)

Create `requirements-dev.txt`:

```txt
# Testing
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-cov==5.0.0
pytest-mock==3.14.0

# Type Checking
mypy==1.11.2
types-PyYAML==6.0.12.20240917
types-aiohttp==3.10.0.20240819

# Linting & Formatting
black==24.8.0
ruff==0.6.9
isort==5.13.2

# Profiling
py-spy==0.3.14
memory-profiler==0.61.0

# Pre-commit
pre-commit==3.8.0
```

---

## Progress Tracking

### Week 1 (P0 Critical)
- [ ] 0/8 P0 issues fixed
- [ ] Code builds without errors
- [ ] All startup methods work
- [ ] Tests pass on Linux and Windows

### Week 2-3 (P1 Important)
- [ ] 0/19 P1 tasks completed
- [ ] All reliability fixes implemented
- [ ] Configuration complete
- [ ] Branding updated

### Month 1 (P2 Testing & Docs)
- [ ] 0/12 testing tasks completed
- [ ] 70%+ code coverage achieved
- [ ] Documentation reorganized
- [ ] Performance benchmarks run

### Month 2+ (P2 Enhancements)
- [ ] 0/18 enhancement tasks completed
- [ ] Plugin system implemented
- [ ] CI/CD workflows active
- [ ] Brand assets created

---

## Quick Reference

### Files Requiring Immediate Attention (P0):
1. `/home/user/MCPM/mcp_backend.py` (lines 121, 128, 637, 1328, 773, 1130, 1155, 1189, 382, 530)
2. `/home/user/MCPM/gui_main_pro.py` (lines 1796, 1862-1869)
3. `/home/user/MCPM/fgd_config.yaml` (all hardcoded paths)
4. All Python files (add type hints)

### Files to Create:
- LICENSE
- .env (from .env.example)
- requirements-lock.txt
- start.sh
- requirements-dev.txt (optional)

### Files to Update:
- README.md (lines 1047, 1056)
- quick_start.bat
- mcp_backend.py (version to v6.0)

---

## Notes

- **Estimated Total Effort**: 100-150 hours for complete P0+P1+P2
- **Critical Path**: 8-12 hours (P0 fixes only)
- **Production Ready**: 30-40 hours (P0 + P1)
- **Fully Polished**: 100+ hours (all priorities)

---

**Last Updated**: 2025-11-18
**Total Tasks**: 54 (8 P0, 19 P1, 27 P2)
