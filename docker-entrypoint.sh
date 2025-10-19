#!/bin/bash
#
# RAGFlow MCP Server - Docker MCP Toolkit Compliant Entry Point
# Supports standard Docker environment configuration
#

set -e

# Load configuration with proper precedence:
# 1. Environment variables (highest priority)
# 2. Config file at /mcp/config.yaml (if mounted by MCP Gateway)
# 3. Defaults

RAGFLOW_BASE_URL="${RAGFLOW_BASE_URL:-http://ragflow:9380}"
RAGFLOW_API_KEY="${RAGFLOW_API_KEY:-}"

# Validate required configuration
if [ -z "$RAGFLOW_API_KEY" ]; then
    echo "❌ Error: RAGFLOW_API_KEY not configured"
    echo "   Set via environment variable: export RAGFLOW_API_KEY=your-key"
    exit 1
fi

if [ -z "$RAGFLOW_BASE_URL" ]; then
    echo "❌ Error: RAGFLOW_BASE_URL not configured"
    echo "   Set via environment variable or default to http://ragflow:9380"
    exit 1
fi

echo "🚀 Starting RAGFlow MCP Server"
echo "   Backend: $RAGFLOW_BASE_URL"
echo "   Transport: stdio (Docker MCP Toolkit compliant)"

# Run with properly parsed arguments
exec python3 -m mcp_app \
    --ragflow-base-url "$RAGFLOW_BASE_URL" \
    --ragflow-api-key "$RAGFLOW_API_KEY"
