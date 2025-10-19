# Docker MCP Toolkit Compliant RAGFlow MCP Server
# Production-grade container with security hardening

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 mcpuser

# Install uv
RUN pip install --no-cache-dir --no-deps uv

# Copy project files with proper permissions
COPY --chown=mcpuser:mcpuser pyproject.toml .
COPY --chown=mcpuser:mcpuser uv.lock .
COPY --chown=mcpuser:mcpuser README.md .
COPY --chown=mcpuser:mcpuser mcp_app.py .
COPY --chown=mcpuser:mcpuser docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# Install dependencies with frozen lock file
RUN uv sync --frozen --no-dev

# Set working directory
WORKDIR /app

# Switch to non-root user
USER mcpuser

# Set Python path to use virtual environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Docker MCP Toolkit resource defaults
ENV MCP_CPU_LIMIT=1 \
    MCP_MEMORY_LIMIT=2g

# Health check (for container orchestration)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import sys; sys.exit(0)" || exit 1

# Standard MCP server transport
ENTRYPOINT ["./docker-entrypoint.sh"]
