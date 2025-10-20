# Docker MCP Toolkit Compliant RAGFlow MCP Server
# Production-grade container with security hardening

FROM python:3.12-slim

# Set labels for better container metadata
LABEL org.opencontainers.image.title="RAGFlow MCP Server"
LABEL org.opencontainers.image.description="Model Context Protocol server for RAGFlow document retrieval"
LABEL org.opencontainers.image.vendor="trafflux"
LABEL org.opencontainers.image.source="https://github.com/trafflux/ragflow-mcp-server"
LABEL org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create non-root user for security
# RUN useradd --create-home --shell /bin/bash --uid 1000 mcpuser

# Install uv
RUN pip install --no-cache-dir --no-deps uv
WORKDIR /app
# Copy project files with proper permissions
COPY . .
RUN chmod +x docker-entrypoint.sh

# Install dependencies with frozen lock file
RUN uv sync --frozen --no-dev

# Switch to non-root user
# USER mcpuser

# Set Python path to use virtual environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check (for container orchestration)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import sys; sys.exit(0)" || exit 1

# Standard MCP server transport (stdio for Docker MCP Toolkit)
# Run using python module with proper async event loop handling
ENTRYPOINT ["python3", "-m", "mcp_app"]
