# RAGFlow MCP Server - Deployment Guide

This guide covers deploying the RAGFlow MCP Server with Docker MCP Toolkit compliance.

## Prerequisites

- [ ] RAGFlow backend is running and accessible
- [ ] RAGFlow API key is obtained
- [ ] Docker Desktop with MCP Toolkit installed (Settings > Features > Enable MCP Toolkit)
- [ ] Docker CLI version 24.0 or later

## Local Testing with Docker Desktop MCP Toolkit

### Step 1: Build the Docker Image Locally

```bash
# Build the image with a local tag
docker build -t ragflow-mcp-server:local .
```

### Step 2: Install the Local Catalog

Place the catalog file in Docker Desktop's MCP directory:

**macOS/Linux:**
```bash
mkdir -p ~/.docker/mcp/catalogs
cp ragflow-mcp-catalog.yaml ~/.docker/mcp/catalogs/ragflow-local.yaml
```

**Windows (PowerShell):**
```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.docker\mcp\catalogs"
Copy-Item ragflow-mcp-catalog.yaml "$env:USERPROFILE\.docker\mcp\catalogs\ragflow-local.yaml"
```

### Step 3: Restart Docker Desktop

After placing the catalog file, restart Docker Desktop to load the new catalog:
1. Quit Docker Desktop completely
2. Restart Docker Desktop
3. Wait for it to fully initialize (watch for the Docker icon to become steady)

### Step 4: Configure in Docker Desktop UI

1. Open **Docker Desktop**
2. Go to **Settings** → **MCP Toolkit**
3. You should see **RAGFlow MCP Server** in the list
4. Click on it to configure:
   - Set **ragflow_api_key**: Your RAGFlow API key (e.g., `ragflow-xxxxxxxx`)
   - Set **ragflow_base_url**: Your RAGFlow server URL (e.g., `http://host.docker.internal:9380`)
5. Toggle the switch to **Enable** the server
6. Click **Apply & Restart**

### Step 5: Verify in Docker Desktop

After enabling, the MCP server should appear as active in the MCP Toolkit section. You can:
- View available tools
- Check server status
- View logs if there are any issues

### Step 6: Test with MCP Client

Configure your MCP client (Claude Desktop, VS Code Copilot, etc.) to use the Docker MCP Gateway:

```json
{
  "mcpServers": {
    "docker-mcp-gateway": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/var/run/docker.sock:/var/run/docker.sock",
        "-v", "~/.docker/mcp:/mcp",
        "docker/mcp-gateway",
        "--catalog=/mcp/catalogs/ragflow-local.yaml",
        "--transport=stdio"
      ]
    }
  }
}
```

### Troubleshooting Local Testing

**Issue: Server not appearing in Docker Desktop UI**
- Ensure the catalog file is in the correct location: `~/.docker/mcp/catalogs/ragflow-local.yaml`
- Verify MCP Toolkit is enabled in Docker Desktop Settings → Features
- Restart Docker Desktop completely (not just refresh)
- Check the catalog file syntax: `python3 -c "import yaml; yaml.safe_load(open('ragflow-mcp-catalog.yaml'))"`
- Check Docker Desktop logs for any catalog loading errors

**Issue: Server fails to start**
- Check Docker Desktop logs for the MCP server
- Verify the image exists: `docker images ragflow-mcp-server:local`
- Ensure RAGFlow backend is accessible from Docker containers
- Try running manually to test: `docker run -it --rm -e RAGFLOW_API_KEY=test -e RAGFLOW_BASE_URL=http://host.docker.internal:9380 ragflow-mcp-server:local`

**Issue: Can't connect to RAGFlow backend**
- Use `host.docker.internal` instead of `localhost` if RAGFlow runs on host
- Verify RAGFlow is accessible: `curl http://your-ragflow:9380/api/v1/datasets`
- Check firewall rules allow Docker containers to access RAGFlow

## Production Deployment

### Quick Start with Docker MCP Registry (After Publication)

Once published to the Docker MCP Registry:

```bash
# Add from official registry
docker mcp server add ragflow-mcp-server

# Configure via Docker Desktop UI
# Settings → MCP Toolkit → RAGFlow MCP Server
```

## Manual Docker Deployment

## Manual Docker Deployment

### Docker Build

```bash
# Build the image
docker build -t ragflow-mcp-server:latest .
```

- [ ] Build completes without errors
- [ ] Image created successfully
- [ ] Verify with: `docker images ragflow-mcp-server`

### Run Container Manually

```bash
# Run with environment variables
docker run -i --rm \
  -e RAGFLOW_API_KEY="ragflow-xxxxxxxx" \
  -e RAGFLOW_BASE_URL="http://ragflow:9380" \
  ragflow-mcp-server:latest
```

- [ ] Server starts without errors
- [ ] Shows "Transport: stdio" message
- [ ] Connection pool initializes properly
- [ ] Responds to stdio MCP protocol messages

## MCP Client Configuration

## MCP Client Configuration

### Using Docker MCP Gateway (Recommended)

The Docker MCP Gateway automatically manages the server:

```json
{
  "mcpServers": {
    "mcp-toolkit-gateway": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/var/run/docker.sock:/var/run/docker.sock",
        "-v", "~/.docker/mcp:/mcp",
        "docker/mcp-gateway",
        "--catalog=/mcp/catalogs/custom.yaml",
        "--transport=stdio"
      ]
    }
  }
}
```

### Direct Container Connection

For advanced use cases, connect directly to the container:

```json
{
  "mcpServers": {
    "ragflow": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "RAGFLOW_API_KEY=ragflow-xxxxxxxx",
        "-e", "RAGFLOW_BASE_URL=http://ragflow:9380",
        "ragflow-mcp-server:latest"
      ]
    }
  }
}
```

## Verification

- [ ] Server starts on demand
- [ ] ragflow_retrieval tool is available
- [ ] Tool accepts search queries
- [ ] Results returned from RAGFlow
- [ ] Connection handling is stable
- [ ] No resource leaks on repeated calls

## Troubleshooting

If issues occur:

1. **Check logs**: `docker logs <container-id>`
2. **Verify connectivity**: Ensure RAGFlow backend is reachable
3. **Validate API key**: Confirm it has proper permissions
4. **Check resource limits**: Ensure host has available CPU/memory
5. **Review TOOLKIT.md**: Detailed configuration reference
6. **Check Docker MCP version**: Must support stdio transport

## Production Checklist

- [ ] Image is tagged with version
- [ ] Image is pushed to registry (if needed)
- [ ] Resource limits are appropriate for workload
- [ ] Logging is configured correctly
- [ ] Health checks pass consistently
- [ ] Security settings are verified
- [ ] Network connectivity is tested
- [ ] Error handling is verified
- [ ] Documentation is updated
- [ ] Team is trained on deployment
