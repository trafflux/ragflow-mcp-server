# Contributing RAGFlow MCP Server to Docker MCP Registry

This guide explains how to submit the RAGFlow MCP Server to the official [Docker MCP Registry](https://github.com/docker/mcp-servers).

## Prerequisites

The RAGFlow MCP Server is already Docker MCP Toolkit compliant and includes all required files:

- ✅ `server.yaml` - Server definition with metadata, configuration, and tools
- ✅ `tools.json` - Tool definitions for validation (used when server can't list tools without configuration)
- ✅ `Dockerfile` - Production-ready container image
- ✅ `docker-entrypoint.sh` - Compliant entrypoint script
- ✅ Apache-2.0 License

## Submission Process

### Option A: Docker-Built Image (Recommended)

Have Docker build and maintain the server image with enhanced security features.

**Steps:**

1. Fork the [docker/mcp-servers](https://github.com/docker/mcp-servers) repository

2. Create a new directory under `servers/`:
   ```bash
   mkdir servers/ragflow-mcp-server
   ```

3. Copy the `server.yaml` and `tools.json` to the new directory:
   ```bash
   cp server.yaml servers/ragflow-mcp-server/
   cp tools.json servers/ragflow-mcp-server/
   ```

4. Update `server.yaml` to remove the `image` field (Docker will build it):
   ```yaml
   name: ragflow-mcp-server
   # image: mcp/ragflow-mcp-server  # Remove this line
   type: server
   # ... rest of the configuration
   ```

5. Create a pull request with:
   - Title: "Add RAGFlow MCP Server"
   - Description: Brief overview of what RAGFlow MCP Server does
   - Link to this repository

6. Docker will:
   - Build the image from your Dockerfile
   - Sign it with cryptographic signatures
   - Add provenance tracking and SBOM
   - Publish to `mcp/ragflow-mcp-server` on Docker Hub
   - Add to the MCP catalog within 24 hours

**Benefits:**
- Enhanced security features (signatures, provenance, SBOM)
- Automatic security updates
- Official Docker Hub hosting
- Full integration with Docker Desktop MCP Toolkit

### Option B: Self-Provided Pre-Built Image

Provide an already-built image (e.g., from your own Docker Hub account or registry).

**Steps:**

1. Build and push your image:
   ```bash
   docker build -t your-org/ragflow-mcp-server:latest .
   docker push your-org/ragflow-mcp-server:latest
   ```

2. Fork the [docker/mcp-servers](https://github.com/docker/mcp-servers) repository

3. Create directory and copy files:
   ```bash
   mkdir servers/ragflow-mcp-server
   cp server.yaml servers/ragflow-mcp-server/
   cp tools.json servers/ragflow-mcp-server/
   ```

4. Update `server.yaml` with your image:
   ```yaml
   name: ragflow-mcp-server
   image: your-org/ragflow-mcp-server:latest
   type: server
   # ... rest of the configuration
   ```

5. Create a pull request

**Note:** Self-built images still benefit from container isolation but won't include the enhanced security features of Docker-built images.

## Using task create (Alternative)

The Docker MCP Registry includes automation tools. If you have Go and Task installed:

```bash
cd /path/to/docker/mcp-servers

# Generate configuration automatically
task create -- \
  --category knowledge-retrieval \
  https://github.com/trafflux/ragflow-mcp-server \
  -e RAGFLOW_API_KEY=test \
  -e RAGFLOW_BASE_URL=http://ragflow:9380
```

This will:
1. Clone the repository
2. Build the Docker image
3. Run it to list tools
4. Generate `server.yaml` automatically

Then review and adjust the generated files as needed.

## Testing Before Submission

### Local Testing with Docker MCP Toolkit

1. Import your local catalog:
   ```bash
   docker mcp catalog import ./server.yaml
   ```

2. Enable the server:
   ```bash
   docker mcp server enable ragflow-mcp-server
   ```

3. Configure secrets:
   ```bash
   docker mcp secret set ragflow-mcp-server.api_key="ragflow-test"
   ```

4. Test in Docker Desktop MCP Toolkit or with your MCP client

5. Reset catalog when done:
   ```bash
   docker mcp catalog reset
   ```

## Review Process

1. Submit your PR to docker/mcp-servers
2. Automated CI checks will run:
   - YAML syntax validation
   - JSON schema validation
   - Dockerfile best practices check
   - Tool listing verification (using tools.json)
3. Docker team reviews the submission
4. Upon approval, server is published to catalog
5. Available in Docker Desktop MCP Toolkit within 24 hours

## Requirements Checklist

Before submitting, ensure:

- [ ] `server.yaml` follows the correct schema
- [ ] `tools.json` accurately describes all tools
- [ ] Dockerfile follows best practices (non-root user, minimal layers)
- [ ] Server uses stdio transport (required for MCP Gateway)
- [ ] License allows redistribution (Apache-2.0, MIT, etc.)
- [ ] Documentation is clear and comprehensive
- [ ] Environment variables are properly documented
- [ ] Server handles missing configuration gracefully

## Maintenance

After acceptance:

- **Updates**: Submit new PRs to update server.yaml or request rebuilds
- **Issues**: Open issues in the docker/mcp-servers repository for catalog-related problems
- **Source Changes**: Keep this repository updated; Docker will rebuild periodically if using Option A

## Resources

- [Docker MCP Registry](https://github.com/docker/mcp-servers)
- [Contributing Guide](https://github.com/docker/mcp-servers/blob/main/CONTRIBUTING.md)
- [Docker MCP Gateway Documentation](https://github.com/theNetworkChuck/docker-mcp-tutorial/blob/main/docs/docker-gateway.md)
- [MCP Specification](https://modelcontextprotocol.io/)
- [Docker Desktop MCP Toolkit](https://docs.docker.com/mcp/)

## Support

For questions or issues:

1. **Registry Submission**: Open an issue in [docker/mcp-servers](https://github.com/docker/mcp-servers)
2. **Server Issues**: Open an issue in this repository
3. **MCP Protocol**: See [MCP Specification](https://modelcontextprotocol.io/)
