# MCPM Docker - Quick Start Guide
**5-Minute Setup for Docker-Only Deployment**

---

## One-Time Setup

### 1. Install Docker
```bash
# macOS/Windows: Download Docker Desktop
# Linux: sudo apt-get install docker.io docker-compose
```

### 2. Clone and Configure
```bash
git clone <repo-url> && cd MCPM-main
cp .env.example .env
# Edit .env with your API keys
nano .env
```

### 3. Build and Start
```bash
docker-compose build
docker-compose up -d
```

### 4. Verify
```bash
curl http://localhost:8000/health
# Should return: healthy
```

---

## Daily Operations

### Start Services
```bash
docker-compose up -d
```

### View Logs
```bash
docker-compose logs -f mcp-backend
```

### Stop Services
```bash
docker-compose down
```

### Check Status
```bash
docker-compose ps
```

### Access Shell
```bash
docker-compose exec mcp-backend /bin/bash
```

---

## Quick Commands with Make

Install Make, then use `Makefile.docker`:

```bash
make build          # Build image
make up             # Start services
make down           # Stop services
make logs           # View logs
make status         # Check status
make shell          # Access container
make test           # Run tests
make clean          # Remove containers
make help           # Show all commands
```

---

## Port Access

| Service | Port | URL |
|---------|------|-----|
| MCP API | 8000 | http://localhost:8000 |
| Metrics | 9090 | http://localhost:9090 |
| Health | 8000 | http://localhost:8000/health |

---

## Environment Setup

Edit `.env`:
```env
XAI_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
LOG_LEVEL=INFO
```

---

## Troubleshooting

### Container won't start
```bash
docker-compose logs mcp-backend
# Check for error messages and fix .env or configuration
```

### Port already in use
```bash
docker-compose down
# or change port in docker-compose.yml
```

### Need fresh start
```bash
docker-compose down -v
docker-compose up -d --build
```

---

## Full Documentation
See `DOCKER_SETUP.md` for comprehensive guide.

---

**Setup Time:** ~5 minutes
**Status:** Production-Ready
