# RAGFlow MCP Server
**Author: Philip Van de Walker | @trafflux |  https://github.com/trafflux**
A Model Context Protocol (MCP) server that provides GitHub Copilot and other MCP clients with access to RAGFlow's document retrieval capabilities.

## Overview

This MCP server enables AI assistants like GitHub Copilot to search and retrieve relevant documents from RAGFlow datasets using natural language queries. It implements the MCP protocol for seamless integration with supported clients.

## Features

- **Document Retrieval**: Search across RAGFlow datasets using natural language queries
- **Structured Results**: Returns formatted JSON with document chunks, metadata, and pagination
- **MCP Protocol Compliant**: Full compatibility with MCP 2024-11-05 specification
- **Production Ready**: Robust error handling, logging, and async operations
- **Cross-Platform**: Works on Windows, Linux, macOS, and Docker environments

## Quick Start

### Prerequisites

- Python 3.11+
- Access to a running RAGFlow instance
- RAGFlow API key

### Installation

1. Navigate to the MCP server directory:
   ```bash
   cd mcp/server
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your RAGFlow API key and base URL
   ```

### Configuration

Create a `.env` file with the following variables:

```bash
RAGFLOW_API_KEY=your-api-key-here
RAGFLOW_BASE_URL=http://localhost:9380
```

### Running the Server

For stdio mode (recommended for Copilot):
```bash
uv run python3 mcp_app.py --mode stdio
```

For HTTP mode:
```bash
uv run python3 mcp_app.py --mode http
```

## MCP Client Configuration

### GitHub Copilot (VS Code)

Add the following to your VS Code MCP configuration:

```json
{
  "mcpServers": {
    "ragflow": {
      "command": "uv",
      "args": ["run", "python3", "mcp_app.py", "--mode", "stdio"],
      "cwd": "/path/to/mcp/server",
      "env": {
        "RAGFLOW_API_KEY": "your-api-key",
        "RAGFLOW_BASE_URL": "http://localhost:9380"
      }
    }
  }
}
```
```json THIS IS WORKING:
		"ragflow": {
			"type": "stdio",
			"command": "uv",
			"args": [
				"run",
				"Z:\\home\\USER\\projects\\ragflow\\docker\\mcp\\server\\mcp_app.py",
				"--mode",
				"stdio"
			],
			"env": {
				"RAGFLOW_API_KEY": "ragflow-xxxxxx",
				"RAGFLOW_BASE_URL": "http://localhost:9380"
			}
		}
    ```
### Other MCP Clients

The server supports the standard MCP stdio transport protocol and can be configured with any MCP-compatible client.

## API Reference

### ragflow_retrieval Tool

Search RAGFlow datasets and retrieve relevant documents.

**Parameters:**
- `question` (string, required): The search query
- `dataset_ids` (array of strings, optional): Specific dataset IDs to search
- `document_ids` (array of strings, optional): Specific document IDs to filter
- `page` (integer, optional): Page number for pagination (default: 1)
- `page_size` (integer, optional): Results per page (default: 10)
- `similarity_threshold` (float, optional): Minimum similarity score (default: 0.2)
- `vector_similarity_weight` (float, optional): Weight for vector vs keyword search (default: 0.3)
- `keyword` (boolean, optional): Enable keyword-based search (default: false)
- `top_k` (integer, optional): Maximum candidates to consider (default: 1024)
- `rerank_id` (string, optional): Reranking model identifier
- `force_refresh` (boolean, optional): Force refresh cached metadata (default: false)

**Response Format:**
```json
{
  "chunks": [
    {
      "id": "chunk-id",
      "content": "Document content...",
      "content_ltks": "processed content...",
      "dataset_id": "dataset-id",
      "document_id": "document-id",
      "document_keyword": "filename.md",
      "highlight": "highlighted <em>content</em>...",
      "important_keywords": ["keyword1", "keyword2"],
      "positions": [[1, 2, 3]],
      "similarity": 0.85,
      "term_similarity": 0.8,
      "vector_similarity": 0.9
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total_chunks": 25,
    "total_pages": 3
  },
  "query_info": {
    "question": "your search query",
    "similarity_threshold": 0.2,
    "vector_weight": 0.3,
    "keyword_search": false,
    "dataset_count": 1
  }
}
```

## Architecture

The MCP server consists of:

- **mcp_app.py**: Main MCP server implementation with tool definitions and request handling
- **RAGFlowConnector**: Async HTTP client for communicating with RAGFlow API
- **MCP Protocol Layer**: Handles MCP protocol messages and tool execution

## Development

### Project Structure

```
mcp/
├── server/
│   ├── mcp_app.py          # Main MCP server
│   ├── pyproject.toml      # Python dependencies
│   ├── uv.lock            # Lock file
│   ├── Dockerfile         # Docker configuration
│   └── README.md          # This file
└── client/                # Optional client utilities
    ├── client.py
    └── streamable_http_client.py
```

### Testing

Run the MCP server in stdio mode and use MCP client tools to test:

```bash
# Test with MCP inspector
npx @modelcontextprotocol/inspector uv run python3 mcp_app.py --mode stdio
```

### Docker Deployment

Build and run with Docker:

```bash
docker build -t ragflow-mcp .
docker run -e RAGFLOW_API_KEY=your-key -e RAGFLOW_BASE_URL=http://host.docker.internal:9380 ragflow-mcp
```

## Troubleshooting

### Common Issues

1. **"Tool not found"**: Ensure the MCP server is running and properly configured in your client
2. **"Connection failed"**: Check RAGFlow API key and base URL in environment variables
3. **"No results"**: Verify datasets exist and contain searchable content
4. **"Timeout"**: Increase timeout values or check RAGFlow server performance

### Logs

The server provides detailed logging. Check your MCP client's logs for error messages and set `LOG_LEVEL=DEBUG` for verbose output.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is part of the RAGFlow ecosystem. See the main RAGFlow repository for licensing information.
         │   RAGFlow Backend          │
         │   Port 9380                │
         │   (REST API)               │
         └────────────────────────────┘
```

## Installation

### Option 1: Integrated with RAGFlow (Default)

The MCP server runs as part of the main ragflow container:

```bash
cd /home/USER/projects/ragflow/docker
docker-compose up -d
```

The server will be available at `http://localhost:9382/mcp/`

### Option 2: Standalone Container

Build and run the MCP server in its own container:

```bash
cd /home/USER/projects/ragflow/docker/mcp/server

# Build
docker build -t ragflow-mcp:latest .

# Run
docker run -d \
  --name ragflow-mcp \
  -p 9382:9382 \
  -e MCP_BASE_URL=http://ragflow:9380 \
  -e MCP_API_KEY=your-api-key \
  --network ragflow \
  ragflow-mcp:latest
```

### Option 3: Direct Python

```bash
cd /home/USER/projects/ragflow/docker/mcp/server

# Install dependencies
pip install -r requirements.txt

# Run
python mcp_app.py \
  --mode http \
  --host 0.0.0.0 \
  --port 9382 \
  --base-url http://127.0.0.1:9380 \
  --api-key your-api-key
```

## Configuration

### Environment Variables

```bash
# Transport mode: http (recommended) or stdio
MCP_MODE=http

# Server binding (HTTP mode only)
MCP_HOST=0.0.0.0
MCP_PORT=9382

# RAGFlow backend connection
MCP_BASE_URL=http://127.0.0.1:9380
MCP_API_KEY=ragflow-xxxxxxxx
```

### Docker Compose

In `docker-compose.yml`, add or update environment section:

```yaml
environment:
  - MCP_MODE=http
  - MCP_HOST=0.0.0.0
  - MCP_PORT=9382
  - MCP_BASE_URL=http://127.0.0.1:9380
  - MCP_API_KEY=your-api-key
```

## VS Code Copilot Configuration

Update `~/.config/Code/User/mcp.json` (or `%APPDATA%\Code\User\mcp.json` on Windows):

```json
{
  "servers": {
    "ragflow": {
      "type": "http",
      "url": "http://localhost:9382/mcp/",
      "env": {
        "Authorization": "Bearer ragflow-xxxxxxxx"
      }
    }
  }
}
```

**Important:** After updating the config:
1. Save the file
2. Close VS Code completely
3. Reopen VS Code
4. Copilot should now show RAGFlow tools available

## Testing

### From Windows PowerShell

```powershell
$headers = @{
    "Authorization" = "Bearer ragflow-xxxxxxxx"
    "Content-Type" = "application/json"
    "Accept" = "application/json, text/event-stream"
}

$body = @{
    jsonrpc = "2.0"
    id = 1
    method = "initialize"
    params = @{
        protocolVersion = "2024-11-05"
        capabilities = @{}
        clientInfo = @{
            name = "test"
            version = "1.0"
        }
    }
} | ConvertTo-Json

$response = Invoke-WebRequest -Uri "http://localhost:9382/mcp/" `
    -Method POST `
    -Headers $headers `
    -Body $body `
    -UseBasicParsing

$response.StatusCode  # Should be 202 Accepted
```

### Health Check

```bash
curl http://localhost:9382/health

# Response:
# {"status":"healthy","server":"ragflow-mcp-server","version":"2.0.0","protocol":"2024-11-05"}
```

### List Tools

```python
import json
import requests

headers = {
    "Authorization": "Bearer ragflow-xxxxxxxx",
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
}

response = requests.post(
    "http://localhost:9382/mcp/",
    headers=headers,
    json=request,
)

print(response.status_code)  # 202
print(response.text)  # SSE stream with tool list
```

## Available Tools

### ragflow_retrieval

Search RAGFlow datasets and retrieve relevant documents.

**Parameters:**

- `question` (string, required): The search query
- `dataset_ids` (array, optional): Specific datasets to search
- `document_ids` (array, optional): Specific documents to search within
- `page` (integer, default: 1): Results page number
- `page_size` (integer, default: 10, max: 100): Results per page
- `similarity_threshold` (number, default: 0.2): Minimum match similarity
- `vector_similarity_weight` (number, default: 0.3): Vector vs keyword weight
- `keyword` (boolean, default: false): Enable keyword search
- `top_k` (integer, default: 1024): Candidate pool size
- `rerank_id` (string, optional): Reranking model
- `force_refresh` (boolean, default: false): Skip cache

**Example Response:**

```
Search Results:

1. RAGFlow is a sophisticated document analysis platform...
   Source: documentation/overview.md
   Relevance: 0.95

2. It supports various document formats including PDF...
   Source: documentation/features.md
   Relevance: 0.87
```

## Troubleshooting

### Copilot can't find the server

1. **Verify server is running:**
   ```bash
   curl http://localhost:9382/health
   ```

2. **Check firewall:**
   Windows Firewall might block port 9382. Allow it in Windows Defender.

3. **Check configuration:**
   - Verify `mcp.json` has correct URL with trailing slash: `/mcp/`
   - Verify Bearer token matches exactly
   - Close and reopen VS Code after changes

4. **Check logs:**
   ```bash
   docker logs ragflow-server | grep -i mcp
   ```

### Connection timeout

- Ensure RAGFlow backend is running and accessible
- Check `MCP_BASE_URL` setting
- Verify API key is valid

### Wrong response format

If getting JSON directly instead of SSE stream:
- Ensure `json_response=False` in server code
- Container might be using old image; rebuild: `docker-compose build --no-cache ragflow`

## Performance Tuning

### For High Load

```yaml
environment:
  - MCP_MODE=http
  - MCP_HOST=0.0.0.0  # Don't restrict to localhost
  - MCP_PORT=9382
```

### For Production

- Run behind a reverse proxy (nginx)
- Use proper SSL/TLS certificates
- Set up monitoring and alerting
- Configure resource limits in Docker

## Development

### Adding New Tools

Edit `mcp_app.py` and add to the `list_tools()` handler:

```python
@self.mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # ... existing tools
        Tool(
            name="my_tool",
            description="Tool description",
            inputSchema={ ... }
        )
    ]
```

Then handle in `call_tool()`:

```python
@self.mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "my_tool":
        # Implement tool logic
        pass
```

### Building from Source

```bash
cd mcp/server
pip install -e .  # Install in development mode
python -m pytest   # Run tests
```

## Migration from Old Server

The new server is **fully backward compatible** but requires:

1. Update `docker-compose.yml` (command section removed)
2. Ensure environment variables are set
3. Restart containers: `docker-compose restart`
4. Reload VS Code

## Support & Issues

- MCP Specification: https://spec.modelcontextprotocol.io/
- RAGFlow: https://github.com/infiniflow/ragflow
- GitHub Issues: [Report issues here]

## License

Same as RAGFlow (Apache 2.0)

---

**Version:** 2.0.0  
**Protocol:** MCP 2024-11-05  
**Last Updated:** October 2025
