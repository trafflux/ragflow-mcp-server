# RAGFlow MCP Server
**Author: Philip Van de Walker | @trafflux |  https://github.com/trafflux**

A Model Context Protocol (MCP) server that provides GitHub Copilot and other MCP clients with access to RAGFlow's document retrieval capabilities.

### Local Testing with Docker Desktop

**Step 1: Build locally**
```bash
docker build -t ragflow-mcp-server:local .
```

### Production Deployment (After Registry Publication)

```bash
# Add from Docker MCP Registry
docker mcp server add ragflow-mcp-server
```

Configure via Docker Desktop UI (Settings → MCP Toolkit → RAGFlow MCP Server).

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

- Python 3.12+
- Access to a running RAGFlow instance
- RAGFlow API key

### Installation

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Configure environment variables:
   ```bash
   cp .env .env.local
   # Edit .env.local with your RAGFlow API key and base URL
   ```

### Configuration

Set the following environment variables:

```bash
RAGFLOW_API_KEY=your-api-key-here
RAGFLOW_BASE_URL=http://localhost:9380
```

### Running the Server

The server uses stdio transport for MCP compliance:

```bash
# Using environment variables
python3 -m mcp_app

# Or with explicit CLI options
python3 -m mcp_app --ragflow-api-key your-key --ragflow-base-url http://localhost:9380
```

## MCP Client Configuration

### GitHub Copilot (VS Code) - Docker-based Setup

For a containerized deployment that doesn't require a separate running server, add the following to your VS Code MCP configuration. This approach runs the MCP server as an ephemeral Docker container for each request:

```json
{
  "mcpServers": {
    "ragflow-mcp": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "RAGFLOW_API_KEY=ragflow-xxxxxxxxx",
        "-e",
        "RAGFLOW_BASE_URL=http://host.docker.internal:9380",
        "--add-host=host.docker.internal:host-gateway",
        "--network",
        "devnet",
        "ragflow-mcp-server:local"
      ]
    }
  }
}
```

#### Environment Variables

- `RAGFLOW_API_KEY`: Your RAGFlow API key (replace `ragflow-xxxxxxxxx` with your actual key)
- `RAGFLOW_BASE_URL`: URL of your RAGFlow instance (default: `http://host.docker.internal:9380` for local Docker setups)

#### Docker Arguments Explained

- `--rm`: Automatically remove the container when it exits
- `-i`: Keep STDIN open for interactive communication
- `--add-host=host.docker.internal:host-gateway`: Maps host.docker.internal to the Docker host (for accessing services on the host machine)
- `--network devnet`: Connects to the specified Docker network where RAGFlow is running

#### Prerequisites

1. **Build the Docker image**:
   ```bash
   docker build -t ragflow-mcp-server:local .
   ```

2. **Ensure RAGFlow is accessible**: The container needs to reach your RAGFlow instance via the configured `RAGFLOW_BASE_URL`

3. **Network configuration**: Make sure the `--network` argument matches the Docker network where your RAGFlow instance is running

### GitHub Copilot (VS Code) - Direct Python Setup

For development or when Docker is not preferred, use the direct Python execution:

```json
{
  "mcpServers": {
    "ragflow": {
      "command": "python3",
      "args": ["-m", "mcp_app"],
      "cwd": "/path/to/ragflow-mcp-server",
      "env": {
        "RAGFLOW_API_KEY": "your-api-key",
        "RAGFLOW_BASE_URL": "http://localhost:9380"
      }
    }
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

## Technical Implementation

### Async Event Loop Management

**Important**: This server uses lazy initialization of the aiohttp session within FastMCP's managed event loop. This is critical for compatibility:

- ❌ **DON'T**: Pre-initialize the aiohttp session before `FastMCP.run()` (creates wrong event loop)
- ✅ **DO**: Use `_ensure_connector_initialized()` to initialize on first tool invocation (uses correct event loop)

**Why this matters**: aiohttp's timeout context manager must be created in the same event loop where tools execute. Initializing in a different loop causes:
```
RuntimeError: Timeout context manager should be used inside a task
```

See [TIMEOUT_FIX_FINAL.md](TIMEOUT_FIX_FINAL.md) for detailed technical explanation.

### Connection Pooling

- **Max Connections**: 100 total, 10 per host
- **DNS TTL**: 300 seconds
- **Session Reuse**: Connections pooled and reused across tool invocations
- **Cleanup**: Automatic on server shutdown

### Caching Strategy

- **Datasets Cache**: LRU with 32 max items, 300s TTL
- **Documents Cache**: LRU with 128 max items, 300s TTL
- **Cache Key**: Dataset/document ID + parameters

## Development

### Project Structure

```
ragflow-mcp-server/
├── mcp_app.py              # Main MCP server (FastMCP)
├── pyproject.toml          # Python project configuration
├── uv.lock                 # Dependency lock file
├── Dockerfile              # Docker container configuration
├── docker-entrypoint.sh    # Docker entrypoint script
├── tools.json              # MCP tool definitions
├── .env                    # Environment variables (example)
├── README.md               # This documentation
└── IMPLEMENTATION.md       # Technical implementation details
```

### Testing

Run the MCP server and use MCP client tools to test:

```bash
# Test with MCP inspector
npx @modelcontextprotocol/inspector python3 -m mcp_app

# Or test directly with environment variables set
RAGFLOW_API_KEY=your-key RAGFLOW_BASE_URL=http://localhost:9380 \
npx @modelcontextprotocol/inspector python3 -m mcp_app
```

### Docker Deployment

#### Building the Image

Build the Docker image for local use or deployment:

```bash
# Build with local tag
docker build -t ragflow-mcp-server:local .

# Or build with a specific version tag
docker build -t ragflow-mcp-server:v1.0.0 .
```

#### Environment Variables for Docker

When running the container, configure these environment variables:

```bash
# Required: RAGFlow API credentials
RAGFLOW_API_KEY=your-ragflow-api-key-here
RAGFLOW_BASE_URL=http://host.docker.internal:9380

# Optional: Logging and debugging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

#### Running as Standalone Container

For testing or development:

```bash
docker run -i --rm \
  -e RAGFLOW_API_KEY=ragflow-xxxxxxxxx \
  -e RAGFLOW_BASE_URL=http://host.docker.internal:9380 \
  --add-host=host.docker.internal:host-gateway \
  --network devnet \
  ragflow-mcp-server:local
```

#### Production Deployment

For production use, consider:

```bash
# Run with resource limits
docker run -d \
  --name ragflow-mcp-server \
  --restart unless-stopped \
  --memory 512m \
  --cpus 0.5 \
  -e RAGFLOW_API_KEY=ragflow-xxxxxxxxx \
  -e RAGFLOW_BASE_URL=http://your-ragflow-host:9380 \
  ragflow-mcp-server:local
```

#### Docker Compose Integration

Add to your `docker-compose.yml`:

```yaml
services:
  ragflow-mcp:
    build: .
    environment:
      - RAGFLOW_API_KEY=ragflow-xxxxxxxxx
      - RAGFLOW_BASE_URL=http://ragflow:9380
    networks:
      - ragflow-network
    depends_on:
      - ragflow
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

### Contributing to RAGFlow MCP Server

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Contributing to Docker MCP Registry

This server is designed to be listed in the [Official Docker MCP Registry](https://github.com/docker/mcp-servers). To contribute this server to the registry:

1. Review the [Docker MCP Registry Contributing Guide](https://github.com/docker/mcp-servers/blob/main/CONTRIBUTING.md)
2. This repository includes a compliant `server.yaml` file that can be submitted
3. The `tools.json` file provides tool metadata for the registry
4. Submit a pull request to the Docker MCP Registry with the server metadata

For more details, see the [Docker MCP Toolkit Documentation](https://docs.docker.com/mcp/).

## License

This project is part of the RAGFlow ecosystem. Licensed under Apache License 2.0.
         │   RAGFlow Backend          │
         │   Port 9380                │
         │   (REST API)               │
         └────────────────────────────┘
```

## Installation

### Option 1: Docker Container (Recommended)

Build and run the MCP server in a Docker container:

```bash
# Build the image
docker build -t ragflow-mcp-server:local .

# Run with environment variables
docker run -i --rm \
  -e RAGFLOW_API_KEY=your-api-key \
  -e RAGFLOW_BASE_URL=http://host.docker.internal:9380 \
  --add-host=host.docker.internal:host-gateway \
  --network devnet \
  ragflow-mcp-server:local
```

### Option 2: Direct Python Installation

Install and run directly with Python:

```bash
# Install dependencies
uv sync

# Set environment variables
export RAGFLOW_API_KEY=your-api-key
export RAGFLOW_BASE_URL=http://localhost:9380

# Run the server
python3 -m mcp_app
```

## Configuration

### Environment Variables

```bash
# Required: RAGFlow API credentials
RAGFLOW_API_KEY=your-ragflow-api-key-here
RAGFLOW_BASE_URL=http://localhost:9380

# Optional: Logging level
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Docker Compose

For containerized deployment, add to your `docker-compose.yml`:

```yaml
services:
  ragflow-mcp:
    build: .
    environment:
      - RAGFLOW_API_KEY=your-api-key
      - RAGFLOW_BASE_URL=http://ragflow:9380
    networks:
      - ragflow-network
    depends_on:
      - ragflow
```

## VS Code Copilot Configuration

Update your VS Code MCP settings to include the RAGFlow server:

**For Docker-based setup:**
```json
{
  "mcpServers": {
    "ragflow-mcp": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "RAGFLOW_API_KEY=your-api-key",
        "-e",
        "RAGFLOW_BASE_URL=http://host.docker.internal:9380",
        "--add-host=host.docker.internal:host-gateway",
        "--network",
        "devnet",
        "ragflow-mcp-server:local"
      ]
    }
  }
}
```

**For direct Python setup:**
```json
{
  "mcpServers": {
    "ragflow": {
      "command": "python3",
      "args": ["-m", "mcp_app"],
      "cwd": "/path/to/ragflow-mcp-server",
      "env": {
        "RAGFLOW_API_KEY": "your-api-key",
        "RAGFLOW_BASE_URL": "http://localhost:9380"
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

### Using MCP Inspector

Test the server using the official MCP inspector:

```bash
# Install MCP inspector if not already installed
npm install -g @modelcontextprotocol/inspector

# Test with environment variables
RAGFLOW_API_KEY=your-key RAGFLOW_BASE_URL=http://localhost:9380 \
mcp-inspector python3 -m mcp_app
```

### Manual Testing

You can also test the server manually by piping JSON-RPC messages:

```bash
# Initialize the server
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}' | \
RAGFLOW_API_KEY=your-key RAGFLOW_BASE_URL=http://localhost:9380 \
python3 -m mcp_app

# List available tools
echo '{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}' | \
RAGFLOW_API_KEY=your-key RAGFLOW_BASE_URL=http://localhost:9380 \
python3 -m mcp_app
```

### Integration Testing

For integration testing with actual RAGFlow data:

```bash
# Set your actual environment variables
export RAGFLOW_API_KEY="your-actual-api-key"
export RAGFLOW_BASE_URL="http://your-ragflow-host:9380"

# Test a retrieval query
echo '{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "ragflow_retrieval",
    "arguments": {
      "question": "What is RAGFlow?",
      "page_size": 5
    }
  }
}' | python3 -m mcp_app
```

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
# Install in development mode
uv sync

# Run tests (if available)
python -m pytest

# Run the server
python3 -m mcp_app
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
