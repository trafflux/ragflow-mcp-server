# RAGFlow MCP Server - Deployment Guide

This guide covers deploying the RAGFlow MCP Server with Docker MCP Toolkit compliance.

## Prerequisites

- [ ] RAGFlow backend is running and accessible
- [ ] RAGFlow API key is obtained
- [ ] Docker Desktop with MCP Toolkit installed
- [ ] Docker CLI version 24.0 or later

## Quick Start with Docker MCP Toolkit

### 1. Add Server to Docker MCP Registry

If the server is published in the Docker MCP Registry:

```bash
# Add from official registry
docker mcp server add ragflow-mcp-server
```

Or use the local `server.yaml`:

```bash
# Import from this repository
docker mcp catalog import ./server.yaml
```

### 2. Configure Secrets

```bash
# Set RAGFlow API key
docker mcp secret set ragflow-mcp-server.api_key="ragflow-xxxxxxxx"

# Set base URL (optional, defaults to http://ragflow:9380)
docker mcp env set ragflow-mcp-server.base_url="http://your-ragflow:9380"
```

### 3. Enable and Test

```bash
# Enable the server
docker mcp server enable ragflow-mcp-server

# List available tools
docker mcp server tools ragflow-mcp-server
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
