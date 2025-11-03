import os, json, asyncio, logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
from mcp_backend import FGDMCPServer

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("fgd_server")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve index if present
if Path("index.html").exists():
    app.mount("/static", StaticFiles(directory="."), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse("index.html")

RUN = {"server": None, "watch_dir": None, "memory_file": None, "log_file": "fgd_runtime.log"}

@app.get("/api/status")
async def status():
    running = RUN["server"] is not None
    return {"api": "ok", "mcp_running": running, "watch_dir": RUN["watch_dir"]}

@app.get("/api/suggest")
async def suggest():
    base = Path(".")
    dirs = [str(p) for p in base.rglob("*") if p.is_dir()]
    return dirs

@app.post("/api/start")
async def start(request: Request):
    data = await request.json()
    watch_dir = data.get("watch_dir")
    provider = data.get("default_provider", "openai")
    if not watch_dir:
        return {"success": False, "error": "No directory selected"}
    if not Path(watch_dir).exists():
        return {"success": False, "error": f"Directory not found: {watch_dir}"}
    try:
        config_path = "config.example.yaml"
        if not Path(config_path).exists():
            return {"success": False, "error": "Missing config.example.yaml"}

        RUN["server"] = FGDMCPServer(config_path)
        RUN["watch_dir"] = watch_dir
        RUN["memory_file"] = str(Path(watch_dir) / ".fgd_memory.json")

        # Start MCP loop in background
        asyncio.create_task(RUN["server"].run())
        # Optionally append to log
        Path(RUN["log_file"]).write_text("INFO: MCP server launching...\n")
        return {"success": True, "memory_file": RUN["memory_file"], "log_file": RUN["log_file"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/logs", response_class=PlainTextResponse)
async def logs(file: str):
    p = Path(file)
    if not p.exists():
        return "No logs yet."
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading logs: {e}"

@app.get("/api/memory")
async def memory():
    if not RUN["server"]:
        return {"error": "Server not running"}
    return RUN["server"].memory.recall()

@app.post("/api/llm_query")
async def llm_query(request: Request):
    if not RUN["server"]:
        return {"error": "Server not running"}
    data = await request.json()
    prompt = data.get("prompt")
    provider = data.get("provider")
    if not prompt:
        return {"error": "No prompt provided"}
    resp = await RUN["server"].llm.query(prompt, provider)
    return {"response": resp}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8456)
