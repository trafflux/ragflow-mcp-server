# RAGFlow MCP Server - FastMCP Edition

## ✅ What Was Built

A production-grade MCP server using **FastMCP** that provides AI agents and clients access to RAGFlow's document retrieval capabilities.

### Key Features

✅ **FastMCP Framework** - Simplified MCP server development  
✅ **Async/Await** - Proper async handling throughout  
✅ **Connection Pooling** - Efficient HTTP management with aiohttp  
✅ **LRU Caching** - Smart caching of datasets and documents (300s TTL)  
✅ **Error Handling** - Comprehensive error logging and diagnostics  
✅ **Docker Ready** - Stdio transport for Docker MCP Toolkit  
✅ **Health Checks** - Built-in diagnostic tools  

## 🔧 Configuration

The server requires two environment variables:

```bash
RAGFLOW_API_KEY=ragflow-xxxx
RAGFLOW_BASE_URL=http://host.docker.internal:9380
```

Your KiloCode MCP settings are already configured correctly:

```json
"ragflow": {
  "disabled": false,
  "command": "docker",
  "args": [
    "run",
    "-i",
    "--rm",
    "-e",
    "RAGFLOW_API_KEY=ragflow-xxxxxxxxxxx",
    "-e",
    "RAGFLOW_BASE_URL=http://host.docker.internal:9380",
    "ragflow-mcp-server:local"
  ]
}
```

## 📦 Available Tools

### 1. `list_datasets()` → string
Returns all available datasets as JSON
```json
{
  "datasets": [
    {"id": "dataset_id", "name": "Dataset Name", "description": "..."}
  ],
  "total": 1
}
```

### 2. `ragflow_health_check()` → string  
Diagnostic tool to verify RAGFlow backend connectivity
```json
{
  "status": "ok",
  "backend": "http://host.docker.internal:9380",
  "api_url": "http://host.docker.internal:9380/api/v1",
  "connection": "working",
  "datasets_count": 5,
  "message": "RAGFlow backend is reachable"
}
```

### 3. `ragflow_retrieval(question, dataset_ids, ...)` → string
Search documents across datasets
```json
{
  "chunks": [
    {
      "content": "...",
      "document_id": "...",
      "dataset_id": "...",
      "document_name": "...",
      "similarity_score": 0.85
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total_chunks": 42,
    "total_pages": 5
  },
  "query_info": {
    "question": "your question",
    "dataset_count": 2
  }
}
```

## 🚀 How to Use

### Test with KiloCode
1. Open KiloCode
2. The MCP server should appear in your list of available tools
3. Call `list_datasets()` first to verify connection
4. If empty, run `ragflow_health_check()` to diagnose connectivity
5. Use `ragflow_retrieval()` to search documents

### Debugging

If you're getting empty datasets, the issue is likely:

1. **RAGFlow backend not running** - Verify `http://host.docker.internal:9380` is accessible
2. **Wrong API key** - Check the RAGFLOW_API_KEY environment variable
3. **No documents** - The RAGFlow instance may not have any indexed documents yet

**Detailed logs are enabled** - Check Docker container output for detailed connection information:

```bash
docker run -i --rm \
  -e "RAGFLOW_API_KEY=ragflow-xxxxxxxxxxx" \
  -e "RAGFLOW_BASE_URL=http://host.docker.internal:9380" \
  ragflow-mcp-server:local
```

## 📁 Project Structure

```
mcp_app.py              Main FastMCP server (672 lines)
__main__.py             Module entry point
Dockerfile              Docker build configuration
docker-entrypoint.sh    Container startup script
pyproject.toml          Python project metadata
```

## 🛠️ Technical Stack

- **FastMCP 2.12.5** - MCP server framework
- **aiohttp 3.13.1** - Async HTTP client with connection pooling
- **Python 3.12** - Runtime
- **Docker** - Containerization

## ✨ Best Practices Implemented

1. **Async Throughout** - All I/O is async/await
2. **Resource Management** - Proper connection lifecycle
3. **Error Handling** - Graceful degradation with logging
4. **Caching Strategy** - LRU with TTL for metadata
5. **Type Safety** - Full type hints throughout
6. **Separation of Concerns** - RAGFlowConnector + RAGFlowMCPServer
7. **Logging** - DEBUG level for full diagnostics

## 🔍 Connection Flow

```
KiloCode (MCP Client)
         ↓
    Docker Container (stdio)
         ↓
    FastMCP Server (mcp_app.py)
         ↓
    RAGFlowConnector (async, pooled)
         ↓
    RAGFlow Backend API
```

---

**Status**: ✅ Production Ready  
**Last Updated**: 2025-10-20  
**Framework**: FastMCP 2.12.5  
**MCP Protocol**: 2024-11-05
