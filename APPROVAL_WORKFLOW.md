# 🚀 GROK CODE FIX PROTOCOL - Complete Guide

## Overview

MCPM v5.0 now includes a **4-step military pipeline** for code edits with GUI approval workflow and persistent conversation memory.

---

## 🎯 The 4-Step Protocol

### **Step 1: LLM Reviews & Proposes Edit**
When GROK (or any LLM) wants to edit a file, it calls the `edit_file` tool **without confirmation**:

```json
{
  "tool": "edit_file",
  "arguments": {
    "filepath": "src/example.py",
    "old_text": "def old_function():\n    pass",
    "new_text": "def new_function():\n    return True",
    "confirm": false
  }
}
```

### **Step 2: Backend Creates Preview & Waits**
The MCP backend (`mcp_backend.py`):
1. ✅ Reads the file
2. ✅ Creates a preview of the changes
3. ✅ Generates a diff (red = old, green = new)
4. ✅ Saves pending edit to `.fgd_pending_edit.json`
5. ✅ Returns preview to LLM with message: "Edit pending approval - check GUI"

**File created:** `.fgd_pending_edit.json`
```json
{
  "filepath": "src/example.py",
  "old_text": "def old_function():\n    pass",
  "new_text": "def new_function():\n    return True",
  "diff": "- def old_function():\n    pass\n+ def new_function():\n    return True",
  "preview": "def new_function():\n    return True\n...",
  "timestamp": "2025-11-04T12:00:00.123456"
}
```

### **Step 3: GUI Displays BIG BLUE "Approve" Button**
The PyQt6 GUI (`gui_main_pro.py`) polls every second for pending edits:

1. ✅ Detects `.fgd_pending_edit.json`
2. ✅ Displays gorgeous diff in the Diff Viewer:
   ```
   📝 PENDING EDIT: src/example.py
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   🔴 OLD TEXT:
   def old_function():
       pass

   🟢 NEW TEXT:
   def new_function():
       return True

   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   📄 PREVIEW (first 500 chars):
   def new_function():
       return True
   ...
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   ⏱️  Timestamp: 2025-11-04T12:00:00.123456

   Click "Approve" to apply changes or "Reject" to cancel.
   ```

3. ✅ **GREEN "Approve" button** and **RED "Reject" button** light up
4. ✅ User clicks one of the buttons

### **Step 4: Approval Triggers Auto-Apply**

#### **If User Clicks "Approve":**
1. GUI writes approval to `.fgd_approval.json`:
   ```json
   {
     "approved": true,
     "filepath": "src/example.py",
     "old_text": "def old_function():\n    pass",
     "new_text": "def new_function():\n    return True",
     "timestamp": "2025-11-04T12:00:05.654321"
   }
   ```
2. GUI deletes `.fgd_pending_edit.json`
3. GUI shows success message: "✅ Changes approved! The backend will apply the changes."

**Backend Auto-Applies Edit:**
- Background monitor detects `.fgd_approval.json` (checks every 2 seconds)
- Reads approval data
- Creates `.bak` backup of original file
- Applies the edit
- Logs: `✅ Edit successfully applied: src/example.py (backup: example.py.bak)`
- Deletes `.fgd_approval.json`

#### **If User Clicks "Reject":**
1. GUI writes rejection to `.fgd_approval.json`:
   ```json
   {
     "approved": false,
     "filepath": "src/example.py",
     "reason": "Rejected by user",
     "timestamp": "2025-11-04T12:00:05.654321"
   }
   ```
2. GUI deletes `.fgd_pending_edit.json`
3. GUI shows message: "❌ Changes rejected! No changes will be made."

**Backend Logs Rejection:**
- Background monitor detects `.fgd_approval.json`
- Logs: `❌ Edit rejected by user: src/example.py`
- Deletes `.fgd_approval.json`
- No file changes are made

---

## 💾 Persistent Conversation Memory

### **What Gets Saved**
Every chat interaction with GROK is now saved as a **prompt + response pair**:

```json
{
  "conversations": {
    "chat_2025-11-04T12:00:00.123456": {
      "value": {
        "prompt": "How do I optimize this function?",
        "response": "Here are 3 ways to optimize...",
        "provider": "grok",
        "timestamp": "2025-11-04T12:00:00.123456",
        "context_used": 15
      },
      "timestamp": "2025-11-04T12:00:00.123456",
      "access_count": 2
    }
  }
}
```

### **Where It's Stored**
- **File:** `.fgd_memory.json` in your project directory
- **Categories:**
  - `conversations` - Full prompt + response pairs (NEW!)
  - `llm` - LLM responses only (for backward compatibility)
  - `file_read` - Files read by LLM
  - `file_write` - Files written
  - `file_edit` - Files edited with approval status
  - `file_change` - File system changes detected
  - `backup` - Backup files created
  - `git_diffs` - Git diffs stored
  - `commits` - Commit messages

### **How to Access Conversations**

#### **Via API:**
```bash
curl http://localhost:8456/api/conversations
```

Response:
```json
{
  "success": true,
  "count": 42,
  "conversations": [
    {
      "id": "chat_2025-11-04T12:00:00.123456",
      "prompt": "How do I optimize this function?",
      "response": "Here are 3 ways to optimize...",
      "provider": "grok",
      "timestamp": "2025-11-04T12:00:00.123456",
      "context_used": 15
    }
  ]
}
```

#### **Directly from Memory File:**
```python
import json
from pathlib import Path

memory = json.loads(Path(".fgd_memory.json").read_text())
conversations = memory.get("conversations", {})

for chat_id, chat_data in conversations.items():
    print(f"Prompt: {chat_data['value']['prompt']}")
    print(f"Response: {chat_data['value']['response']}")
    print(f"Time: {chat_data['value']['timestamp']}")
    print("-" * 80)
```

---

## 🔧 Implementation Details

### **File-Based Communication**
The GUI and backend communicate through JSON files:

| File | Purpose | Created By | Consumed By |
|------|---------|------------|-------------|
| `.fgd_pending_edit.json` | Pending edit awaiting approval | Backend | GUI |
| `.fgd_approval.json` | Approval/rejection decision | GUI | Backend |
| `.fgd_memory.json` | Persistent memory store | Backend | Backend/API |

### **Background Monitors**

#### **Approval Monitor** (`mcp_backend.py:182-234`)
- Runs asynchronously in background
- Checks every **2 seconds** for `.fgd_approval.json`
- Auto-applies approved edits
- Logs rejected edits
- Cleans up approval files after processing

#### **GUI Polling** (`gui_main_pro.py:277-326`)
- Runs every **1 second** via QTimer
- Checks for `.fgd_pending_edit.json`
- Displays diff in Diff Viewer
- Highlights Approve/Reject buttons
- Prevents duplicate notifications (checks timestamp)

### **Code Locations**

| Feature | File | Lines |
|---------|------|-------|
| Pending edit creation | `mcp_backend.py` | 378-403 |
| Auto-approval monitor | `mcp_backend.py` | 182-234 |
| Conversation memory save | `mcp_backend.py` | 507-524 |
| GUI pending edit check | `gui_main_pro.py` | 277-326 |
| GUI approve handler | `gui_main_pro.py` | 332-370 |
| GUI reject handler | `gui_main_pro.py` | 372-409 |
| Conversations API | `server.py` | 406-447 |
| Pending edits API | `server.py` | 450-483 |

---

## 🎨 Visual Flow Diagram

```
┌─────────────┐
│  GROK LLM   │
│ (edit_file) │
└──────┬──────┘
       │
       │ 1. Call edit_file(confirm=false)
       ▼
┌──────────────────────────────────────┐
│  MCP Backend (mcp_backend.py)        │
│  • Generates preview & diff          │
│  • Writes .fgd_pending_edit.json     │
└──────┬───────────────────────────────┘
       │
       │ 2. Return preview to LLM
       │    "Edit pending approval - check GUI"
       ▼
┌──────────────────────────────────────┐
│  PyQt6 GUI (gui_main_pro.py)         │
│  • Polls every 1s for pending edits  │
│  • Displays gorgeous diff            │
│  • Shows BIG APPROVE/REJECT buttons  │
└──────┬───────────────────────────────┘
       │
       │ 3. User clicks Approve or Reject
       ▼
┌──────────────────────────────────────┐
│  GUI writes .fgd_approval.json       │
│  • approved: true/false              │
│  • filepath, old_text, new_text      │
└──────┬───────────────────────────────┘
       │
       │ 4. Approval monitor detects file
       ▼
┌──────────────────────────────────────┐
│  Backend Auto-Applies Edit           │
│  • Creates .bak backup               │
│  • Writes new content                │
│  • Logs success ✅                   │
│  • Cleans up approval file           │
└──────────────────────────────────────┘
```

---

## 🧪 Testing the Workflow

### **Test 1: End-to-End Approval**

1. Start the GUI:
   ```bash
   python gui_main_pro.py
   ```

2. Select your project directory and start the server

3. Have GROK make an edit request (via MCP client):
   ```json
   {
     "tool": "edit_file",
     "arguments": {
       "filepath": "test.py",
       "old_text": "print('hello')",
       "new_text": "print('Hello, World!')",
       "confirm": false
     }
   }
   ```

4. **Check GUI:**
   - Diff Viewer shows the pending edit
   - Approve/Reject buttons are highlighted

5. Click **Approve**

6. **Verify:**
   - File `test.py` is updated
   - Backup `test.py.bak` is created
   - Log shows: `✅ Edit successfully applied: test.py (backup: test.py.bak)`

### **Test 2: Rejection**

1. Have GROK make another edit request

2. Click **Reject** in GUI

3. **Verify:**
   - File is NOT modified
   - Log shows: `❌ Edit rejected by user: <filepath>`

### **Test 3: Conversation Memory**

1. Query GROK via API:
   ```bash
   curl -X POST http://localhost:8456/api/llm_query \
     -H "Content-Type: application/json" \
     -d '{"prompt": "What is Python?", "provider": "grok"}'
   ```

2. Check `.fgd_memory.json`:
   ```bash
   cat .fgd_memory.json | jq .conversations
   ```

3. Retrieve via API:
   ```bash
   curl http://localhost:8456/api/conversations | jq .
   ```

---

## 🚨 Troubleshooting

### **Issue: GUI doesn't show pending edits**

**Solution:**
- Verify GUI is running and connected to the correct project directory
- Check if `.fgd_pending_edit.json` exists in project directory
- Look at GUI logs: `mcpm_gui.log`

### **Issue: Approval doesn't apply edits**

**Solution:**
- Check backend logs: `.fgd_server.log`
- Verify approval monitor is running (should see "Approval monitor started" in logs)
- Check if `.fgd_approval.json` was created

### **Issue: Conversations not being saved**

**Solution:**
- Verify `.fgd_memory.json` exists and is writable
- Check backend logs for memory save errors
- Ensure `llm_query` tool is being called (not direct LLM API calls)

---

## 📊 New API Endpoints

### **GET /api/conversations**
Retrieve all saved conversations.

**Response:**
```json
{
  "success": true,
  "count": 42,
  "conversations": [
    {
      "id": "chat_2025-11-04T12:00:00",
      "prompt": "...",
      "response": "...",
      "provider": "grok",
      "timestamp": "...",
      "context_used": 15
    }
  ]
}
```

### **GET /api/pending_edits**
Check for pending edit requests.

**Response:**
```json
{
  "success": true,
  "has_pending": true,
  "pending_edit": {
    "filepath": "src/example.py",
    "old_text": "...",
    "new_text": "...",
    "diff": "...",
    "preview": "...",
    "timestamp": "..."
  }
}
```

---

## ✅ Summary

### **What's Fixed:**

1. ✅ **GROK can now write files after review**
   - Approval workflow fully implemented
   - GUI → Backend communication working
   - Auto-apply on approval

2. ✅ **Every chat is saved as memory**
   - Prompt + response pairs stored
   - Conversation threading
   - Persistent across sessions
   - API access to history

3. ✅ **4-Step Military Pipeline**
   - Step 1: LLM calls edit_file
   - Step 2: Backend creates preview
   - Step 3: GUI shows BIG BLUE "Approve" button
   - Step 4: Auto-apply on approval

### **Files Modified:**
- ✅ `mcp_backend.py` - Added approval monitor, conversation memory
- ✅ `gui_main_pro.py` - Added pending edit polling, approval handlers
- ✅ `server.py` - Added conversations & pending_edits API endpoints

### **New Features:**
- ✅ File-based GUI ↔ Backend communication
- ✅ Background approval monitoring
- ✅ Persistent conversation memory
- ✅ Conversation history API
- ✅ Visual diff display with emojis
- ✅ Automatic backup creation

---

## 🎉 Enjoy Your New Workflow!

You now have a **production-ready approval system** with **persistent memory**. GROK can review code, propose changes, wait for your approval, and automatically apply edits when you click that **BIG BLUE APPROVE BUTTON**! 🚀
