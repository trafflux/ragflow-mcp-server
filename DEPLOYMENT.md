# RAGFlow MCP Server - Deployment Checklist

## Pre-Deployment

- [ ] RAGFlow backend is running and accessible
- [ ] RAGFlow API key is obtained
- [ ] Docker/Docker Desktop is installed
- [ ] MCP Gateway is available (for Docker integration)

## Docker Build

```bash
cd /home/USER/projects/ragflow/docker
docker build -t ragflow-mcp-server:latest -f mcp/server/Dockerfile mcp/server
```

- [ ] Build completes without errors
- [ ] Image size is ~226MB
- [ ] Verify with: `docker images ragflow-mcp-server`

## Configuration

Set environment variables:
```bash
export RAGFLOW_API_KEY="your-actual-api-key"
export RAGFLOW_BASE_URL="http://ragflow-backend:9380"
```

- [ ] API key is valid
- [ ] Base URL is correct and accessible
- [ ] Backend is reachable from container network

## Local Testing

```bash
# Test 1: Direct run
docker run --rm \
  -e RAGFLOW_API_KEY="$RAGFLOW_API_KEY" \
  -e RAGFLOW_BASE_URL="$RAGFLOW_BASE_URL" \
  ragflow-mcp-server:latest

# Test 2: Docker Compose
docker-compose -f docker-compose.ragflow-mcp.yml up
```

- [ ] Server starts without errors
- [ ] Shows "Transport: stdio" message
- [ ] Connection pool initializes properly
- [ ] Graceful shutdown on Ctrl+C

## MCP Gateway Integration

```bash
# Copy catalog
cp mcp/server/ragflow-mcp.yaml ~/.docker/mcp/catalogs/

# Enable server
docker mcp server enable ragflow-mcp

# Run gateway
docker mcp gateway run --servers=ragflow-mcp
```

- [ ] Catalog file copied successfully
- [ ] Server appears in `docker mcp server list`
- [ ] Gateway starts with ragflow-mcp enabled
- [ ] Tools are discovered by MCP clients

## Client Configuration

### Claude Desktop
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "ragflow-mcp": {
      "command": "docker",
      "args": ["mcp", "gateway", "run", "--servers=ragflow-mcp"]
    }
  }
}
```

- [ ] Configuration file updated
- [ ] Claude Desktop restarted
- [ ] MCP server appears in Claude interface

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
