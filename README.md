# FGD Fusion Stack Pro (v4)

Professional, dark-themed PyQt6 console for managing your FGD stack.

## Features
- PyQt6 GUI (tabs: Overview, Logs, Memory, Chat, Config)
- Dark theme by default with light toggle
- System tray integration
- Hidden console (FastAPI backend runs silently)
- LLM providers: OpenAI, Grok, Claude

## Quick Start (Windows)
1) Install dependencies:
   ```bat
   pip install -r requirements.txt
   ```
2) Create `.env` from `.env.example` and add your API keys.
3) Start the GUI:
   ```bat
   python gui_main_pro.py
   ```
4) In the GUI:
   - Pick a directory
   - Choose provider
   - Click **Launch Server**
   - Use Logs/Memory/Chat tabs

## Notes
- The GUI starts the FastAPI backend automatically (hidden) if it isn't running.
- `config.example.yaml` defines your default LLM models and options.
