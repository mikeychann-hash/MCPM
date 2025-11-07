# MCPM Crash Analysis and Fixes

**Analysis Date**: 2025-11-06
**Severity Levels**: 🔴 CRITICAL | 🟠 HIGH | 🟡 MEDIUM | 🟢 LOW

---

## Executive Summary

Analysis of the MCPM codebase revealed **7 critical crash-prone issues** that can cause:
- Application hangs/freezes
- Zombie processes
- Deadlocks
- Resource leaks
- Unclean shutdowns

All issues have been identified with specific locations and recommended fixes.

---

## 🔴 CRITICAL Issues

### 1. **Subprocess Pipe Deadlock** (CRITICAL)
**Location**: `gui_main_pro.py:1289-1317`

**Problem**:
```python
def _read_subprocess_stdout(self):
    for line in self.process.stdout:  # ← BLOCKS INDEFINITELY
        # Process line...
```

**Why This Crashes**:
- If subprocess doesn't produce output, thread blocks forever
- If subprocess crashes, pipe may never close
- Daemon threads blocking on I/O can cause ugly exits
- Can cause GUI to hang waiting for threads to finish

**Impact**: 🔴 **Application hang**, zombie processes

**Fix**:
```python
def _read_subprocess_stdout(self):
    """Background thread to read subprocess stdout."""
    try:
        while self.process and self.process.poll() is None:
            line = self.process.stdout.readline()
            if not line:
                break
            try:
                decoded = line.decode('utf-8', errors='replace')
                if self.log_file:
                    with self._log_lock:  # Thread-safe file writes
                        with open(self.log_file, 'a') as f:
                            f.write(decoded)
                            f.flush()
            except Exception as e:
                logger.error(f"Error writing stdout to log: {e}")
                break
    except Exception as e:
        logger.debug(f"Stdout reader stopped: {e}")
```

**Same issue exists for stderr reader at line 1304-1317.**

---

### 2. **Process Termination Without Cleanup** (CRITICAL)
**Location**: `gui_main_pro.py:1321`

**Problem**:
```python
def toggle_server(self):
    if self.process and self.process.poll() is None:
        self.process.terminate()  # ← NO WAIT!
        self.process = None       # ← Immediate cleanup
```

**Why This Crashes**:
- Sets `self.process = None` immediately after terminate
- Daemon threads still reading from pipes crash when process is None
- No `.wait()` call = zombie process
- Race condition: threads may try to read from None process

**Impact**: 🔴 **Zombie processes**, thread crashes, resource leaks

**Fix**:
```python
def toggle_server(self):
    if self.process and self.process.poll() is None:
        logger.info("Stopping MCP backend process...")
        self.process.terminate()

        try:
            # Wait up to 5 seconds for clean shutdown
            self.process.wait(timeout=5)
            logger.info("Process terminated cleanly")
        except subprocess.TimeoutExpired:
            logger.warning("Process didn't stop, forcing kill...")
            self.process.kill()
            self.process.wait()  # Wait for kill to complete

        # Now safe to set to None
        self.process = None

        self.connection_status.set_status("stopped", "🔴 Server stopped")
        self.start_btn.setText("▶ Start Server")
```

---

### 3. **Infinite Approval Monitor Loop** (CRITICAL)
**Location**: `mcp_backend.py:293-303`

**Problem**:
```python
async def _approval_monitor_loop(self):
    while True:  # ← INFINITE LOOP, NO CANCELLATION
        try:
            await asyncio.sleep(2)
            # Process approvals...
        except Exception as e:
            logger.debug(f"Approval monitor error: {e}")
```

**Why This Crashes**:
- Infinite loop with no exit condition
- If task isn't properly cancelled on shutdown, hangs forever
- Exception handling catches ALL exceptions (including cancellation)
- No reference to task = can't cancel it

**Impact**: 🔴 **Application hang on exit**, resource leak

**Fix**:
```python
async def _approval_monitor_loop(self):
    """Background loop to check for approval files and auto-apply edits."""
    try:
        while True:
            await asyncio.sleep(2)

            approval_file = self.watch_dir / ".fgd_approval.json"
            if not approval_file.exists():
                continue

            # Process approvals...

    except asyncio.CancelledError:
        logger.info("Approval monitor cancelled, shutting down cleanly")
        raise  # Re-raise to allow proper cancellation
    except Exception as e:
        logger.error(f"Approval monitor error: {e}", exc_info=True)
```

**AND store the task reference:**
```python
def __init__(self, config_path: str):
    # ...existing init code...
    self._approval_task = None  # Track the task

async def run(self):
    logger.info("MCP Server starting...")

    # Start approval monitor and STORE reference
    self._approval_task = asyncio.create_task(self._approval_monitor_loop())

    try:
        async with stdio_server() as (read, write):
            await self.server.run(read, write, self.server.create_initialization_options())
    finally:
        # Clean shutdown
        if self._approval_task and not self._approval_task.done():
            self._approval_task.cancel()
            try:
                await self._approval_task
            except asyncio.CancelledError:
                pass
```

---

### 4. **Observer Thread Join Without Timeout** (HIGH)
**Location**: `mcp_backend.py:759-762`

**Problem**:
```python
def stop(self):
    if self.observer:
        self.observer.stop()
        self.observer.join()  # ← CAN HANG FOREVER
```

**Why This Crashes**:
- `join()` without timeout can hang indefinitely
- If observer thread is stuck, application freezes on exit
- No error handling if join fails

**Impact**: 🟠 **Application freeze on exit**

**Fix**:
```python
def stop(self):
    if self.observer:
        logger.info("Stopping file watcher...")
        self.observer.stop()

        # Join with timeout to prevent hanging
        self.observer.join(timeout=5.0)

        if self.observer.is_alive():
            logger.warning("File watcher thread did not stop cleanly")
        else:
            logger.info("File watcher stopped cleanly")

        self.observer = None
```

---

## 🟠 HIGH Priority Issues

### 5. **File I/O Race Condition** (HIGH)
**Location**: `gui_main_pro.py:1296, 1311`

**Problem**:
- Two daemon threads writing to same log file
- No file locking or synchronization
- Concurrent writes can corrupt log file or cause IOError

**Impact**: 🟠 **Corrupted logs**, potential crashes

**Fix**:
```python
import threading

class FGDGUI(QWidget):
    def __init__(self):
        # ...existing init code...
        self._log_lock = threading.Lock()

    def _read_subprocess_stdout(self):
        try:
            while self.process and self.process.poll() is None:
                line = self.process.stdout.readline()
                if not line:
                    break
                decoded = line.decode('utf-8', errors='replace')
                if self.log_file:
                    with self._log_lock:  # Thread-safe
                        with open(self.log_file, 'a') as f:
                            f.write(decoded)
                            f.flush()
        except Exception as e:
            logger.debug(f"Stdout reader stopped: {e}")
```

---

### 6. **Process Object Race Condition** (HIGH)
**Location**: `gui_main_pro.py:1292, 1320`

**Problem**:
```python
# Thread 1 (daemon):
for line in self.process.stdout:  # Reading process

# Thread 2 (main):
self.process.terminate()
self.process = None  # ← RACE: Thread 1 crashes!
```

**Impact**: 🟠 **Thread crashes**, attribute errors

**Fix**:
```python
def toggle_server(self):
    if self.process and self.process.poll() is None:
        # Store reference before setting to None
        process_to_stop = self.process

        logger.info("Stopping MCP backend process...")
        process_to_stop.terminate()

        try:
            process_to_stop.wait(timeout=5)
            logger.info("Process terminated cleanly")
        except subprocess.TimeoutExpired:
            logger.warning("Process didn't stop, forcing kill...")
            process_to_stop.kill()
            process_to_stop.wait()

        # Now safe to set to None (daemon threads will exit on pipe close)
        self.process = None
```

---

### 7. **Missing Subprocess Cleanup on Close** (HIGH)
**Location**: `gui_main_pro.py:1689-1702`

**Problem**:
```python
def closeEvent(self, event):
    if self.process:
        self.process.terminate()
        try:
            self.process.wait(timeout=2)
        except Exception:
            pass  # ← Silent failure, no kill
```

**Why This Is Bad**:
- If process doesn't stop in 2 seconds, leaves zombie
- No `.kill()` fallback
- Daemon threads may still be blocked on pipes

**Impact**: 🟠 **Zombie processes** on application exit

**Fix**:
```python
def closeEvent(self, event):
    """Clean shutdown of all resources."""
    logger.info("Application closing, cleaning up...")

    # Stop timers
    if hasattr(self, "timer") and self.timer.isActive():
        self.timer.stop()
    if hasattr(self, "_header_timer") and self._header_timer.isActive():
        self._header_timer.stop()

    # Stop subprocess with proper cleanup
    if self.process:
        logger.info("Terminating MCP backend...")
        self.process.terminate()

        try:
            self.process.wait(timeout=5)
            logger.info("Backend stopped cleanly")
        except subprocess.TimeoutExpired:
            logger.warning("Backend didn't stop, forcing kill...")
            self.process.kill()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                logger.error("Backend refused to die!")
        except Exception as e:
            logger.error(f"Error stopping backend: {e}")

    # Close pop-out windows
    for window in self.pop_out_windows:
        try:
            window.close()
        except Exception as e:
            logger.debug(f"Error closing pop-out window: {e}")

    event.accept()
    logger.info("Application closed")
```

---

## 🟡 MEDIUM Priority Issues

### 8. **No Thread Cleanup Tracking** (MEDIUM)
**Location**: `gui_main_pro.py:1396-1399`

**Problem**:
- Daemon threads started but never tracked
- No way to check if they're still running
- No graceful shutdown mechanism

**Fix**: Add thread tracking and shutdown signals:
```python
def __init__(self):
    # ...existing init code...
    self._shutdown_event = threading.Event()
    self._stdout_thread = None
    self._stderr_thread = None

def _read_subprocess_stdout(self):
    try:
        while not self._shutdown_event.is_set():
            if not self.process or self.process.poll() is not None:
                break
            # Read with timeout to allow checking shutdown flag
            # ... (implementation using select or similar)
    except Exception as e:
        logger.debug(f"Stdout reader stopped: {e}")

def stop(self):
    # Signal threads to stop
    self._shutdown_event.set()

    # Stop process
    # ... (existing stop code)
```

---

## Testing Recommendations

### Crash Testing Scenarios

1. **Subprocess Crash Test**:
   ```bash
   # Start GUI, then kill backend manually
   ps aux | grep mcp_backend
   kill -9 <PID>
   # GUI should handle gracefully
   ```

2. **Rapid Start/Stop Test**:
   ```python
   # Click Start → Stop → Start → Stop rapidly
   # Should not crash or leave zombies
   ```

3. **Force Quit Test**:
   ```bash
   # Close GUI window during operation
   # Check for zombie processes:
   ps aux | grep defunct
   ```

4. **Long-Running Test**:
   ```bash
   # Run for hours, then close
   # Check memory usage doesn't grow
   # Verify clean shutdown
   ```

---

## Implementation Priority

### Phase 1 - Critical Fixes (Do First)
1. ✅ Fix subprocess pipe deadlock (Issue #1)
2. ✅ Fix process termination cleanup (Issue #2)
3. ✅ Fix infinite approval monitor loop (Issue #3)

### Phase 2 - High Priority
4. ✅ Add observer join timeout (Issue #4)
5. ✅ Add file I/O locking (Issue #5)
6. ✅ Fix process race condition (Issue #6)

### Phase 3 - Medium Priority
7. ✅ Improve closeEvent cleanup (Issue #7)
8. ✅ Add thread tracking (Issue #8)

---

## Monitoring and Prevention

### Add Crash Logging
```python
import atexit

def _cleanup_on_exit():
    """Emergency cleanup on abnormal exit."""
    logger.critical("Emergency cleanup triggered!")
    # Log process state, thread count, etc.

atexit.register(_cleanup_on_exit)
```

### Add Health Checks
```python
def _health_check(self):
    """Periodic health check to detect hung state."""
    if self.process:
        if self.process.poll() is not None:
            # Process died unexpectedly!
            logger.error("Backend process died unexpectedly!")
            self.connection_status.set_status("error", "🔴 Backend crashed")
```

---

## Summary

**Total Issues Found**: 8
**Critical**: 4 🔴
**High**: 3 🟠
**Medium**: 1 🟡

**Primary Crash Causes**:
1. Blocking I/O on subprocess pipes
2. Missing process cleanup
3. Uncancellable async tasks
4. Thread joins without timeouts
5. Race conditions on shared resources

**Estimated Fix Time**: 4-6 hours
**Testing Time**: 2-3 hours

All issues are fixable with the provided solutions. Priority should be given to Critical issues as they cause immediate application hangs and crashes.
