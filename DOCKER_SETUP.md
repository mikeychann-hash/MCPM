# MCPM Docker Setup Guide
**Version:** 6.0
**Status:** Production-Ready
**Last Updated:** 2025-11-09

---

## Overview

MCPM is now fully containerized for Docker. This guide covers:
- Building and running MCPM in Docker
- Configuration management
- Networking and port mapping
- Monitoring and logging
- Production deployment

---

## Prerequisites

### Required
- Docker >= 20.10
- Docker Compose >= 2.0
- 2GB RAM minimum
- 2GB disk space minimum

### Optional
- Docker Buildkit (faster builds)
- Kubernetes (for orchestration)
- SSL certificates (for production)

---

## Quick Start

### 1. Clone/Setup the Project
```bash
cd /path/to/MCPM-main
```

### 2. Configure Environment
```bash
# Copy example env file
cp .env.example .env

# Edit with your API keys
nano .env
```

### 3. Build Docker Image
```bash
# Option A: Using docker-compose (recommended)
docker-compose build

# Option B: Using docker directly
docker build -t mcpm:latest .
```

### 4. Start Services
```bash
# Start all services (MCP backend, Nginx gateway, Redis, Prometheus)
docker-compose up -d

# View logs
docker-compose logs -f mcp-backend

# Stop services
docker-compose down
```

### 5. Verify Setup
```bash
# Check container status
docker-compose ps

# Test health check
curl http://localhost:8000/health

# Check MCP backend
docker-compose exec mcp-backend python -c "import mcp_backend; print('✅ MCP loaded')"
```

---

## Services Included

### Core Services

#### 1. MCP Backend (`mcp-backend`)
- **Purpose:** Core MCP server handling file operations and LLM integration
- **Port:** 5000 (internal), 8000 (via nginx)
- **Health Check:** Every 30 seconds
- **Restart Policy:** Unless stopped

#### 2. API Gateway (Nginx)
- **Purpose:** HTTP reverse proxy and load balancer
- **Port:** 8000 (API), 9000 (metrics)
- **Features:**
  - Rate limiting
  - Gzip compression
  - SSL termination ready

#### 3. Cache (Redis)
- **Purpose:** Caching and session management
- **Port:** 6379 (internal only)

#### 4. Monitoring (Prometheus)
- **Purpose:** Metrics collection and monitoring
- **Port:** 9090 (metrics dashboard)

---

## Configuration

### Environment Variables

Create a `.env` file:

```env
XAI_API_KEY=your_xai_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
LOG_LEVEL=INFO
```

### Quick Commands

```bash
# Build
docker-compose build

# Start
docker-compose up -d

# Logs
docker-compose logs -f

# Stop
docker-compose down

# Status
docker-compose ps
```

---

**Created:** 2025-11-09
**Status:** Production-Ready
