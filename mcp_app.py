#!/usr/bin/env python3
"""
RAGFlow MCP Server - Docker MCP Toolkit Compliant

A production-ready Model Context Protocol server for RAGFlow document retrieval
with proper error handling, connection pooling, and full Docker MCP Toolkit integration.

Protocol Version: 2024-11-05

Author: Philip Van de Walker | @trafflux |  https://github.com/trafflux
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any

import aiohttp
import click
from mcp.server import Server
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server as mcp_stdio_server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool

# Configure logging - write to stderr (Docker best practice)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


class RAGFlowConnector:
    """Async connector to RAGFlow backend with connection pooling"""

    def __init__(self, base_url: str, api_key: str):
        """Initialize connector with validation"""
        if not base_url:
            raise ValueError("RAGFlow base_url is required")
        if not api_key:
            raise ValueError("RAGFlow api_key is required")
        
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_url = f"{self.base_url}/api/v1"
        self.session: aiohttp.ClientSession | None = None
        logger.info(f"Connector initialized for {self.base_url}")

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    async def initialize(self):
        """Initialize connection pool"""
        if self.session:
            return
        
        # Connection pool with reasonable limits
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=10,
            ttl_dns_cache=300,
            ssl=False,
        )
        timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=15)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        logger.info("RAGFlow connection pool initialized")

    async def cleanup(self):
        """Close connection pool"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("RAGFlow connection pool closed")

    async def _request(
        self, method: str, path: str, **kwargs
    ) -> dict[str, Any]:
        """Make authenticated request to RAGFlow API"""
        if not self.session:
            raise RuntimeError("Connector not initialized - call initialize() first")

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.api_key}"
        headers["Content-Type"] = "application/json"

        url = f"{self.api_url}{path}"
        
        try:
            async with self.session.request(
                method, url, headers=headers, timeout=aiohttp.ClientTimeout(total=30), **kwargs
            ) as response:
                text = await response.text()
                
                if response.status >= 400:
                    logger.error(
                        f"RAGFlow API error {response.status} at {url}: {text}"
                    )
                    raise RuntimeError(
                        f"RAGFlow API error {response.status}: {text}"
                    )
                
                if response.status == 204:  # No content
                    return {}
                
                try:
                    return await response.json()
                except json.JSONDecodeError:
                    logger.warning(f"Non-JSON response from {url}: {text}")
                    return {"data": text}
                    
        except asyncio.TimeoutError:
            raise RuntimeError("RAGFlow API request timeout")
        except aiohttp.ClientError as e:
            raise RuntimeError(f"RAGFlow API connection error: {str(e)}")

    async def list_datasets(self) -> list[dict[str, Any]]:
        """List all available datasets"""
        try:
            result = await self._request("GET", "/datasets")
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Error listing datasets: {e}")
            return []

    async def retrieval(
        self,
        question: str,
        dataset_ids: list[str] | None = None,
        document_ids: list[str] | None = None,
        page: int = 1,
        page_size: int = 10,
        similarity_threshold: float = 0.2,
        vector_similarity_weight: float = 0.3,
        keyword: bool = False,
        top_k: int = 1024,
        rerank_id: str | None = None,
        force_refresh: bool = False,
    ) -> list[TextContent]:
        """Search RAGFlow datasets and return results as MCP TextContent"""
        try:
            # If no datasets specified, get all
            if not dataset_ids:
                datasets = await self.list_datasets()
                dataset_ids = [d["id"] for d in datasets]

            if not dataset_ids:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": "No datasets available for search."})
                )]

            # Prepare request payload
            payload = {
                "question": question,
                "dataset_ids": dataset_ids,
                "page": page,
                "page_size": page_size,
                "similarity_threshold": similarity_threshold,
                "vector_similarity_weight": vector_similarity_weight,
                "keyword": keyword,
                "top_k": top_k,
                "force_refresh": force_refresh,
            }

            if document_ids:
                payload["document_ids"] = document_ids
            if rerank_id:
                payload["rerank_id"] = rerank_id

            result = await self._request("POST", "/retrieval", json=payload)
            logger.info(f"Retrieval successful. Result type: {type(result)}")

            # Validate response structure
            if not isinstance(result, dict):
                logger.error(f"Unexpected response type: {type(result)}")
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unexpected response type: {type(result)}"})
                )]
            
            # Check API response code
            if result.get("code") != 0:
                error_msg = result.get("message", "Unknown error")
                logger.error(f"RAGFlow API error: {error_msg}")
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": error_msg})
                )]
            
            # Extract chunks from RAGFlow response
            data = result.get("data", {})
            if not isinstance(data, dict):
                logger.error(f"Invalid data format: {type(data)}")
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": "Invalid response format from RAGFlow"})
                )]
            
            chunks = data.get("chunks", [])
            
            if not chunks:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "chunks": [],
                        "message": "No relevant documents found.",
                        "pagination": {
                            "page": page,
                            "page_size": page_size,
                            "total_chunks": 0,
                            "total_pages": 0,
                        }
                    })
                )]

            # Build structured response with metadata
            response = {
                "chunks": chunks,
                "pagination": {
                    "page": data.get("page", page),
                    "page_size": data.get("page_size", page_size),
                    "total_chunks": data.get("total", len(chunks)),
                    "total_pages": (data.get("total", len(chunks)) + page_size - 1) // page_size,
                },
                "query_info": {
                    "question": question,
                    "similarity_threshold": similarity_threshold,
                    "vector_weight": vector_similarity_weight,
                    "keyword_search": keyword,
                    "dataset_count": len(dataset_ids),
                },
            }

            return [TextContent(type="text", text=json.dumps(response, ensure_ascii=False))]

        except Exception as e:
            logger.error(f"Error during retrieval: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Error during search: {str(e)}"})
            )]


class RAGFlowMCPServer:
    """Production-ready MCP Server for RAGFlow"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        server_name: str = "ragflow-mcp-server",
        server_version: str = "2.0.0",
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.server_name = server_name
        self.server_version = server_version
        self.connector = RAGFlowConnector(base_url, api_key)
        self.mcp_server = Server(self.server_name)
        self._setup_handlers()
        logger.info(f"RAGFlowMCPServer initialized: {server_name} v{server_version}")

    def _setup_handlers(self):
        """Setup MCP request handlers"""
        logger.info("Setting up MCP request handlers...")

        @self.mcp_server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools for client discovery"""
            logger.info("list_tools() HANDLER CALLED")
            try:
                tool = Tool(
                    name="ragflow_retrieval",
                    description="Search RAGFlow datasets and retrieve relevant documents for a given question. Supports filtering by dataset/document IDs and advanced search parameters.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The question or query to search for in RAGFlow datasets",
                            },
                            "dataset_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional list of dataset IDs to search in. If omitted, searches all available datasets",
                            },
                            "document_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional list of specific document IDs to filter search results",
                            },
                            "page": {
                                "type": "integer",
                                "description": "Page number for pagination (1-indexed)",
                                "default": 1,
                                "minimum": 1,
                            },
                            "page_size": {
                                "type": "integer",
                                "description": "Number of results per page (recommended: 5-20 to avoid token limits)",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 100,
                            },
                            "similarity_threshold": {
                                "type": "number",
                                "description": "Minimum similarity score threshold for results (0.0-1.0)",
                                "default": 0.2,
                                "minimum": 0.0,
                                "maximum": 1.0,
                            },
                            "vector_similarity_weight": {
                                "type": "number",
                                "description": "Weight balance between vector and keyword similarity (0.0=keyword only, 1.0=vector only)",
                                "default": 0.3,
                                "minimum": 0.0,
                                "maximum": 1.0,
                            },
                            "keyword": {
                                "type": "boolean",
                                "description": "Enable keyword-based search in addition to vector search",
                                "default": False,
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Maximum number of candidates to consider before final ranking",
                                "default": 1024,
                                "minimum": 1,
                                "maximum": 1024,
                            },
                            "rerank_id": {
                                "type": "string",
                                "description": "Optional reranking model identifier for result ordering",
                            },
                            "force_refresh": {
                                "type": "boolean",
                                "description": "Force refresh cached metadata (use sparingly for performance)",
                                "default": False,
                            },
                        },
                        "required": ["question"],
                    },
                )
                logger.info(f"Tool created successfully: {tool.name}")
                return [tool]
            except Exception as e:
                logger.error(f"Error in list_tools: {e}", exc_info=True)
                raise

        @self.mcp_server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool execution requests"""
            logger.info(f"call_tool() HANDLER CALLED - name={name}")
            if name != "ragflow_retrieval":
                logger.warning(f"Unknown tool requested: {name}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error: Unknown tool '{name}'",
                    )
                ]

            try:
                logger.info(f"Executing ragflow_retrieval with question: {arguments.get('question', '')[:100]}")
                
                result = await self.connector.retrieval(
                    question=arguments.get("question", ""),
                    dataset_ids=arguments.get("dataset_ids"),
                    document_ids=arguments.get("document_ids"),
                    page=arguments.get("page", 1),
                    page_size=arguments.get("page_size", 10),
                    similarity_threshold=arguments.get("similarity_threshold", 0.2),
                    vector_similarity_weight=arguments.get("vector_similarity_weight", 0.3),
                    keyword=arguments.get("keyword", False),
                    top_k=arguments.get("top_k", 1024),
                    rerank_id=arguments.get("rerank_id"),
                    force_refresh=arguments.get("force_refresh", False),
                )

                logger.info(f"Tool execution successful, result type: {type(result)}, returning {len(result) if isinstance(result, list) else 'unknown'} items")
                if result and isinstance(result, list):
                    logger.info(f"Result[0] type: {type(result[0])}")
                    if hasattr(result[0], 'text'):
                        logger.info(f"Result[0].text length: {len(result[0].text)}")
                return result

            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}", exc_info=True)
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error executing tool: {str(e)}",
                    )
                ]
        
        logger.info("_setup_handlers() COMPLETED - Both @list_tools and @call_tool registered")

    async def run_stdio(self):
        """Run server using stdio transport (Docker MCP Toolkit compliant)"""
        logger.info("Starting with stdio transport")
        
        async with self.connector:
            async with mcp_stdio_server() as (read_stream, write_stream):
                await self.mcp_server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name=self.server_name,
                        server_version=self.server_version,
                        capabilities=self.mcp_server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={},
                        ),
                    ),
                )


@click.command()
@click.option(
    "--ragflow-base-url",
    type=str,
    required=True,
    help="RAGFlow backend base URL (e.g., http://ragflow:9380)",
    envvar="RAGFLOW_BASE_URL",
)
@click.option(
    "--ragflow-api-key",
    type=str,
    required=True,
    help="RAGFlow API key for authentication",
    envvar="RAGFLOW_API_KEY",
)
def main(ragflow_base_url: str, ragflow_api_key: str):
    """
    Start RAGFlow MCP Server (Docker MCP Toolkit compliant)
    
    Uses stdio transport for compatibility with MCP Gateway.
    
    Configuration:
        RAGFLOW_BASE_URL: RAGFlow backend URL (e.g., http://ragflow:9380)
        RAGFLOW_API_KEY: RAGFlow API key for authentication
    """
    
    try:
        server = RAGFlowMCPServer(
            base_url=ragflow_base_url,
            api_key=ragflow_api_key,
        )
        
        logger.info(f"Starting RAGFlow MCP Server")
        logger.info(f"  Backend: {ragflow_base_url}")
        logger.info(f"  Protocol: 2024-11-05")
        logger.info(f"  Transport: stdio")
        
        asyncio.run(server.run_stdio())
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
