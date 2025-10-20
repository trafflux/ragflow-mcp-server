# Local Testing Quick Start

This guide shows how to test the RAGFlow MCP Server locally with Docker Desktop's MCP Toolkit **before** publishing to the Docker MCP Registry.

## Prerequisites

- Docker Desktop with MCP Toolkit enabled (Settings → Features → Enable MCP Toolkit)
- RAGFlow instance running (locally or remotely)
- RAGFlow API key

## Step-by-Step Local Testing

### 1. Build the Local Image

```bash
docker build -t ragflow-mcp-server:local .
```

This creates a local Docker image tagged as `ragflow-mcp-server:local`.

### 2. Import the Local Catalog

```bash
docker mcp catalog import ragflow-mcp-catalog.yaml
```

This imports the local testing catalog into Docker Desktop's MCP Toolkit.

### 3. Configure in Docker Desktop UI

1. Open **Docker Desktop**
2. Navigate to **Settings** → **MCP Toolkit**
3. You should see **"RAGFlow MCP Server"** in the server list
4. Click on the server to configure it
5. Set the following parameters:
   - **ragflow_api_key**: Your RAGFlow API key (e.g., `ragflow-xxxxxxxxxxxxxxxx`)
   - **ragflow_base_url**: Your RAGFlow server URL
     - For local RAGFlow: `http://host.docker.internal:9380`
     - For remote RAGFlow: `http://your-server:9380`
6. Toggle the switch to **Enable** the server
7. Click **Apply & Restart**

### 4. Verify the Server is Running

After enabling, check in Docker Desktop:
- The server status should show as **Active/Running**
- You can view the server logs
- Tools should be listed (e.g., `ragflow_retrieval`)

### 5. Test with an MCP Client

Configure your MCP client (Claude Desktop, VS Code with Copilot, etc.) to use the Docker MCP Gateway:

**For Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

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

**For VS Code with GitHub Copilot** (`.vscode/mcp.json` or global settings):

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

### 6. Test a Query

In your MCP client, try using the RAGFlow retrieval tool:

```
Use the ragflow_retrieval tool to search for "machine learning" in my RAGFlow datasets.
```

The MCP client should:
1. Connect to the Docker MCP Gateway
2. Gateway routes the request to your local RAGFlow MCP Server
3. Server queries your RAGFlow instance
4. Results are returned to the MCP client

## Troubleshooting

### Server doesn't appear in Docker Desktop UI

- Verify MCP Toolkit is enabled: Docker Desktop → Settings → Features
- Check catalog was imported: `docker mcp catalog list`
- Validate the catalog file: `python3 -c "import yaml; yaml.safe_load(open('ragflow-mcp-catalog.yaml'))"`

### Server fails to start

- Check Docker Desktop logs for the MCP server
- Verify the image exists: `docker images ragflow-mcp-server:local`
- Try running manually: `docker run -it --rm -e RAGFLOW_API_KEY=test -e RAGFLOW_BASE_URL=http://host.docker.internal:9380 ragflow-mcp-server:local`

### Can't connect to RAGFlow backend

- **For local RAGFlow**: Use `http://host.docker.internal:9380` (not `localhost`)
- **For remote RAGFlow**: Ensure the URL is accessible from Docker containers
- Test connectivity: `docker run --rm curlimages/curl curl http://host.docker.internal:9380/api/v1/datasets`
- Check firewall rules allow Docker container network access

### MCP client can't see the tool

- Verify the server is enabled in Docker Desktop
- Check server status in Docker Desktop → MCP Toolkit
- Restart your MCP client after configuration changes
- Check MCP client logs for connection errors

## What's Different from Production?

**Local Testing (this guide)**:
- Uses `ragflow-mcp-catalog.yaml` → points to `ragflow-mcp-server:local`
- Image is built locally
- Configure via Docker Desktop UI
- For development and verification

**Production (after registry publication)**:
- Uses official Docker MCP Registry
- Image hosted at `mcp/ragflow-mcp-server` on Docker Hub
- Same Docker Desktop UI configuration
- Automatic updates and security scanning

## Next Steps

Once local testing is successful:

1. ✅ Verify all functionality works
2. ✅ Test with different RAGFlow datasets
3. ✅ Confirm UI configuration persists after Docker Desktop restart
4. 📤 Submit to Docker MCP Registry (see `CONTRIBUTING_DOCKER_MCP.md`)
5. 🎉 Enjoy enhanced discoverability!

## Need Help?

- **Local Testing Issues**: See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed troubleshooting
- **Docker MCP Toolkit**: [Docker MCP Documentation](https://docs.docker.com/mcp/)
- **Registry Submission**: See [CONTRIBUTING_DOCKER_MCP.md](CONTRIBUTING_DOCKER_MCP.md)
