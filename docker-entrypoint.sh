#!/bin/bash
#
# RAGFlow MCP Server - Docker MCP Toolkit Compliant Entry Point
# FastMCP - Standard MCP Protocol Implementation
#
# This script validates required environment variables and starts the
# RAGFlow MCP server using the stdio transport (Docker MCP Toolkit standard)
#

set -e

# Load configuration with proper precedence:
# 1. Environment variables (highest priority - set by Docker Desktop MCP Toolkit)
# 2. Defaults

RAGFLOW_BASE_URL="${RAGFLOW_BASE_URL:-}"
RAGFLOW_API_KEY="${RAGFLOW_API_KEY:-}"

# Validate required configuration
if [ -z "$RAGFLOW_API_KEY" ]; then
    echo "❌ Error: RAGFLOW_API_KEY environment variable not set" >&2
    echo "   Required by: MCP Server for RAGFlow authentication" >&2
    echo "   Set via: export RAGFLOW_API_KEY=<your-api-key>" >&2
    exit 1
fi

if [ -z "$RAGFLOW_BASE_URL" ]; then
    echo "❌ Error: RAGFLOW_BASE_URL environment variable not set" >&2
    echo "   Required by: MCP Server for RAGFlow backend connection" >&2
    echo "   Set via: export RAGFLOW_BASE_URL=<ragflow-api-url>" >&2
    exit 1
fi

# Start the FastMCP server with stdio transport
# The MCP protocol uses stdin/stdout for bidirectional communication
exec python3 -m mcp_app
