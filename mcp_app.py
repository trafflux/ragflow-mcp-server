#!/usr/bin/env python3
"""
RAGFlow MCP Server - FastMCP Best Practices Edition

A production-ready Model Context Protocol server for RAGFlow document retrieval
with FastMCP, comprehensive error handling, connection pooling, and caching.

Features:
  - FastMCP for simplified MCP server development
  - Async/await with proper lifecycle management
  - LRU caching for datasets and documents
  - Connection pooling and timeout handling
  - Docker MCP Toolkit compliant (stdio transport)
  - Comprehensive error handling and logging

Protocol Version: 2025-06-18
Author: Philip Van de Walker | @trafflux | https://github.com/trafflux
"""

import asyncio
import json
import logging
import os
import sys
import time
from collections import OrderedDict
from typing import Any

import aiohttp
import click
from fastmcp import FastMCP

# Configure logging - write to stderr (Docker best practice)
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for better diagnostics
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


class LRUCache:
    """Simple LRU cache with TTL support"""

    def __init__(self, max_size: int = 32, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        """Get value from cache if valid"""
        if key not in self.cache:
            return None

        value, expiry_time = self.cache[key]
        if time.time() > expiry_time:
            del self.cache[key]
            return None

        # Move to end (most recently used)
        self.cache.move_to_end(key)
        return value

    def set(self, key: str, value: Any) -> None:
        """Set value in cache with TTL"""
        expiry_time = time.time() + self.ttl_seconds
        self.cache[key] = (value, expiry_time)
        self.cache.move_to_end(key)

        # Evict oldest if over capacity
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()


class RAGFlowConnector:
    """Async connector to RAGFlow backend with connection pooling and caching"""

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

        # Initialize caches
        self.dataset_cache = LRUCache(max_size=32, ttl_seconds=300)
        self.document_cache = LRUCache(max_size=128, ttl_seconds=300)

        logger.info(f"RAGFlowConnector initialized for {self.base_url}")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
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
        # NOTE: Don't set timeout at session level - FastMCP's async context requires per-request timeout
        self.session = aiohttp.ClientSession(connector=connector)
        logger.info("RAGFlow connection pool initialized")

    async def cleanup(self):
        """Close connection pool and clear caches"""
        if self.session:
            await self.session.close()
            self.session = None
        self.dataset_cache.clear()
        self.document_cache.clear()
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

        # If path starts with /api/, use base_url directly, otherwise use api_url
        if path.startswith("/api/"):
            url = f"{self.base_url}{path}"
        else:
            url = f"{self.api_url}{path}"

        try:
            logger.debug(f"Making {method} request to {url} with params: {kwargs.get('params', {})}")
            logger.debug(f"[_request] Headers being sent: Authorization={headers.get('Authorization', 'MISSING')} Content-Type={headers.get('Content-Type', 'MISSING')}")
            
            # Don't use timeout - FastMCP's async context is incompatible with aiohttp timeout objects
            # aiohttp will use its default timeout (5 minutes total)
            async with self.session.request(
                method, url, headers=headers, **kwargs
            ) as response:
                logger.debug(f"Response status: {response.status}")
                
                if response.status >= 400:
                    text = await response.text()
                    logger.error(
                        f"RAGFlow API error {response.status} at {url}: {text}"
                    )
                    raise RuntimeError(
                        f"RAGFlow API error {response.status}: {text}"
                    )

                if response.status == 204:  # No content
                    return {}

                try:
                    result = await response.json()
                    logger.debug(f"Response body (first 500 chars): {str(result)[:500]}")
                    return result
                except json.JSONDecodeError:
                    text = await response.text()
                    logger.warning(f"Non-JSON response from {url}: {text}")
                    return {"data": text}

        except asyncio.TimeoutError:
            logger.error(f"RAGFlow API request timeout to {url}")
            raise RuntimeError("RAGFlow API request timeout")
        except aiohttp.ClientError as e:
            logger.error(f"RAGFlow API connection error to {url}: {str(e)}")
            raise RuntimeError(f"RAGFlow API connection error: {str(e)}")

    async def list_datasets(
        self,
        page: int = 1,
        page_size: int = 100,
        orderby: str = "create_time",
        desc: bool = True,
    ) -> list[dict[str, Any]]:
        """List all available datasets from RAGFlow"""
        try:
            full_url = f"{self.api_url}/datasets"
            logger.info(f"🔍 [list_datasets] Fetching from: {full_url}")
            logger.info(f"🔍 [list_datasets] Full api_url: {self.api_url}")
            logger.info(f"🔍 [list_datasets] Auth key (first 20 chars): {self.api_key[:20]}")
            
            result = await self._request(
                "GET",
                "/datasets",
                params={
                    "page": page,
                    "page_size": page_size,
                    "orderby": orderby,
                    "desc": "true" if desc else "false",  # Convert bool to string for aiohttp
                },
            )

            logger.info(f"📦 [list_datasets] RAW RESPONSE TYPE: {type(result)}")
            logger.info(f"📦 [list_datasets] RAW RESPONSE: {str(result)[:500]}")
            
            # If result is not a dict, something went wrong
            if not isinstance(result, dict):
                logger.error(f"❌ [list_datasets] Response is not dict! Type: {type(result)}, Value: {result}")
                return []

            if result.get("code") != 0:
                error_msg = result.get("message", "Unknown error")
                logger.error(f"❌ [list_datasets] API error (code={result.get('code')}): {error_msg}")
                logger.error(f"❌ [list_datasets] Full response on error: {result}")
                return []

            datasets = result.get("data", [])
            logger.info(f"📦 [list_datasets] Data type: {type(datasets)}, value: {str(datasets)[:200]}")
            
            # Handle None case
            if datasets is None:
                logger.warning("⚠️  [list_datasets] Data is None, using empty list")
                datasets = []
            elif isinstance(datasets, dict):
                logger.warning("⚠️  [list_datasets] Data is dict, converting to list")
                datasets = list(datasets.values()) if datasets else []
            
            logger.info(f"✅ [list_datasets] SUCCESS: Returning {len(datasets)} datasets")
            return datasets

        except Exception as e:
            logger.error(f"❌ [list_datasets] EXCEPTION: {type(e).__name__}: {e}", exc_info=True)
            import traceback
            logger.error(f"❌ [list_datasets] Full traceback: {traceback.format_exc()}")
            return []

    async def get_dataset_info(self, dataset_id: str) -> dict[str, Any] | None:
        """Get dataset metadata from cache or API"""
        cached = self.dataset_cache.get(dataset_id)
        if cached:
            logger.debug(f"Dataset {dataset_id} retrieved from cache")
            return cached

        try:
            result = await self._request(
                "GET",
                "/datasets",
                params={"id": dataset_id, "page_size": 1},
            )

            if result.get("code") != 0:
                logger.warning(f"Failed to get dataset {dataset_id}: {result.get('message')}")
                return None

            datasets = result.get("data", [])
            if datasets:
                dataset_info = {
                    "id": datasets[0].get("id"),
                    "name": datasets[0].get("name", "Unknown"),
                    "description": datasets[0].get("description", ""),
                }
                self.dataset_cache.set(dataset_id, dataset_info)
                return dataset_info

            return None

        except Exception as e:
            logger.error(f"Error getting dataset {dataset_id}: {e}")
            return None

    async def get_documents(
        self, dataset_id: str
    ) -> dict[str, dict[str, Any]]:
        """Get document list for a dataset, with caching"""
        cached = self.document_cache.get(dataset_id)
        if cached:
            logger.debug(f"Documents for dataset {dataset_id} retrieved from cache")
            return cached

        try:
            result = await self._request("GET", f"/datasets/{dataset_id}/documents")

            if result.get("code") != 0:
                logger.warning(
                    f"Failed to get documents for {dataset_id}: {result.get('message')}"
                )
                return {}

            docs_list = result.get("data", {}).get("docs", [])
            docs_dict = {}

            for doc in docs_list:
                doc_id = doc.get("id")
                if not doc_id:
                    continue

                doc_meta = {
                    "id": doc_id,
                    "name": doc.get("name", ""),
                    "location": doc.get("location", ""),
                    "type": doc.get("type", ""),
                    "size": doc.get("size"),
                    "chunk_count": doc.get("chunk_count"),
                    "create_date": doc.get("create_date", ""),
                    "update_date": doc.get("update_date", ""),
                    "token_count": doc.get("token_count"),
                    "thumbnail": doc.get("thumbnail", ""),
                }
                docs_dict[doc_id] = doc_meta

            self.document_cache.set(dataset_id, docs_dict)
            logger.info(f"Cached {len(docs_dict)} documents for dataset {dataset_id}")
            return docs_dict

        except Exception as e:
            logger.error(f"Error getting documents for {dataset_id}: {e}")
            return {}

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
    ) -> dict[str, Any]:
        """Search RAGFlow datasets and return results as structured data"""
        try:
            logger.info(f"📥 retrieval() called: question={question[:50]}, dataset_ids={dataset_ids}")
            
            # Filter dataset_ids: only keep non-empty strings
            valid_dataset_ids = None
            if dataset_ids:
                valid_ids = [d for d in dataset_ids if d and isinstance(d, str) and d.strip()]
                if valid_ids:
                    valid_dataset_ids = valid_ids
                    logger.info(f"📋 Using provided dataset_ids: {valid_dataset_ids}")
            
            # If no valid dataset_ids provided, get all available datasets
            if not valid_dataset_ids:
                logger.info("📋 No valid dataset_ids, fetching all datasets...")
                all_datasets = await self.list_datasets()
                logger.info(f"📋 Found {len(all_datasets)} total datasets")
                
                # DEBUG: If empty, include detailed info in response
                if not all_datasets:
                    logger.error("❌ No datasets available!")
                    return {
                        "error": "No datasets available in RAGFlow backend",
                        "debug": {
                            "question": question,
                            "api_url": self.api_url,
                            "message": "list_datasets() returned empty. Check that RAGFLOW_BASE_URL is correct and RAGFlow backend is running.",
                        },
                        "chunks": [],
                        "query": question,
                    }
                
                valid_dataset_ids = [ds.get("id") for ds in all_datasets if ds.get("id")]
                logger.info(f"📋 Using all datasets: {valid_dataset_ids}")

            # Filter document_ids similarly
            valid_document_ids = None
            if document_ids:
                valid_ids = [d for d in document_ids if d and isinstance(d, str) and d.strip()]
                if valid_ids:
                    valid_document_ids = valid_ids
                    logger.info(f"📋 Using provided document_ids: {valid_document_ids}")
            
            # Clear caches if force refresh requested
            if force_refresh:
                self.dataset_cache.clear()
                self.document_cache.clear()
                logger.info("🔄 Caches cleared due to force_refresh")

            # Prepare request payload
            payload = {
                "question": question,
                "page": page,
                "page_size": page_size,
                "similarity_threshold": similarity_threshold,
                "vector_similarity_weight": vector_similarity_weight,
                "keyword": keyword,
                "top_k": top_k,
                "dataset_ids": valid_dataset_ids,
            }

            if valid_document_ids:
                payload["document_ids"] = valid_document_ids
            if rerank_id:
                payload["rerank_id"] = rerank_id

            logger.info("🔍 Calling /retrieval endpoint")
            logger.debug(f"   Payload: {json.dumps(payload, indent=2)}")
            
            result = await self._request("POST", "/retrieval", json=payload)

            logger.info(f"📦 Retrieval response code: {result.get('code')}")

            # Check API response code
            if result.get("code") != 0:
                error_msg = result.get("message", "Unknown error from RAGFlow")
                logger.error(f"❌ RAGFlow API error: {error_msg}")
                return {
                    "error": error_msg,
                    "chunks": [],
                    "query": question,
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_chunks": 0,
                        "total_pages": 0,
                    },
                }

            # Extract chunks from RAGFlow response
            data = result.get("data", {})
            chunks = data.get("chunks", [])

            if not chunks:
                logger.info("ℹ️  Retrieval returned no chunks (no matching documents found)")
                return {
                    "chunks": [],
                    "message": "No relevant documents found for your question.",
                    "query": question,
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_chunks": 0,
                        "total_pages": 0,
                    },
                    "query_info": {
                        "question": question,
                        "similarity_threshold": similarity_threshold,
                        "vector_weight": vector_similarity_weight,
                        "keyword_search": keyword,
                        "dataset_count": len(valid_dataset_ids) if valid_dataset_ids else 0,
                    },
                }

            # Enrich chunks with metadata
            enriched_chunks = []
            for chunk in chunks:
                enriched_chunk = dict(chunk)

                # Add dataset info
                dataset_id = chunk.get("dataset_id") or chunk.get("kb_id")
                if dataset_id:
                    dataset_info = await self.get_dataset_info(dataset_id)
                    if dataset_info:
                        enriched_chunk["dataset_name"] = dataset_info.get("name", "Unknown")

                # Add document info
                doc_id = chunk.get("document_id")
                if dataset_id and doc_id:
                    docs = await self.get_documents(dataset_id)
                    if doc_id in docs:
                        enriched_chunk["document_name"] = docs[doc_id].get("name", "")
                        enriched_chunk["document_metadata"] = docs[doc_id]

                enriched_chunks.append(enriched_chunk)

            # Build structured response
            total_chunks = data.get("total", len(chunks))
            total_pages = (total_chunks + page_size - 1) // page_size

            response = {
                "chunks": enriched_chunks,
                "pagination": {
                    "page": data.get("page", page),
                    "page_size": data.get("page_size", page_size),
                    "total_chunks": total_chunks,
                    "total_pages": total_pages,
                },
                "query": question,
                "query_info": {
                    "question": question,
                    "similarity_threshold": similarity_threshold,
                    "vector_weight": vector_similarity_weight,
                    "keyword_search": keyword,
                    "dataset_count": len(valid_dataset_ids) if valid_dataset_ids else 0,
                },
            }

            logger.info(f"✅ Retrieval successful: {len(enriched_chunks)} chunks returned")
            return response

        except Exception as e:
            logger.error(f"❌ Error during retrieval: {e}", exc_info=True)
            return {
                "error": f"Retrieval failed: {str(e)}",
                "chunks": [],
                "query": question,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_chunks": 0,
                    "total_pages": 0,
                },
            }


class RAGFlowMCPServer:
    """Production-ready MCP Server for RAGFlow using FastMCP"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.connector: RAGFlowConnector | None = None
        self.mcp = FastMCP(
            name="ragflow-mcp-server",
            instructions="Access RAGFlow document retrieval and search capabilities through the MCP protocol.",
        )
        self._setup_handlers()
        logger.info("RAGFlowMCPServer initialized")
    
    async def _ensure_connector_initialized(self) -> None:
        """Lazy initialize connector within FastMCP's event loop
        
        This MUST be called from within an async tool function so it's
        initialized in FastMCP's managed event loop, not a separate one.
        This fixes the "Timeout context manager should be used inside a task" error.
        """
        if self.connector and self.connector.session:
            return
            
        logger.info(f"Initializing connector for {self.base_url} in FastMCP event loop")
        
        self.connector = RAGFlowConnector(self.base_url, self.api_key)
        await self.connector.initialize()
        logger.info("Connector initialized in FastMCP event loop")

    def _setup_handlers(self):
        """Setup MCP request handlers using FastMCP decorators"""
        logger.info("Setting up MCP request handlers...")

        @self.mcp.tool()
        async def ragflow_health_check() -> str:
            """Check if the RAGFlow backend is reachable and return diagnostic information.
            
            Returns JSON with connection status, URL, and error details if applicable.
            """
            try:
                await self._ensure_connector_initialized()
                logger.info("Health check requested")
                
                # Try to list datasets as a connectivity test
                datasets = await self.connector.list_datasets(page_size=1)
                
                return json.dumps({
                    "status": "ok",
                    "backend": self.connector.base_url,
                    "api_url": self.connector.api_url,
                    "connection": "working",
                    "datasets_count": len(datasets),
                    "message": "RAGFlow backend is reachable"
                }, ensure_ascii=False)
                
            except Exception as e:
                logger.error(f"Health check failed: {e}", exc_info=True)
                return json.dumps({
                    "status": "error",
                    "backend": self.base_url,
                    "api_url": f"{self.base_url}/api/v1",
                    "error": str(e),
                    "message": "Failed to connect to RAGFlow backend"
                }, ensure_ascii=False)

        @self.mcp.tool()
        async def list_datasets() -> str:
            """List all available RAGFlow datasets with their IDs and descriptions.
            
            Returns a JSON string containing dataset information including:
            - id: Unique dataset identifier
            - name: Human-readable dataset name
            - description: Dataset description
            """
            try:
                await self._ensure_connector_initialized()
                logger.info("list_datasets() called")
                datasets = await self.connector.list_datasets()

                response = {
                    "datasets": [
                        {
                            "id": ds.get("id"),
                            "name": ds.get("name", "Unknown"),
                            "description": ds.get("description", ""),
                        }
                        for ds in datasets
                    ],
                    "total": len(datasets),
                }

                logger.info(f"Returning {len(datasets)} datasets")
                return json.dumps(response, ensure_ascii=False)

            except Exception as e:
                logger.error(f"Error in list_datasets: {e}", exc_info=True)
                return json.dumps({"error": str(e), "datasets": []})

        @self.mcp.tool()
        async def search_documents(
            question: str,
            dataset_ids: list[str] | str | None = None,
            document_ids: list[str] | str | None = None,
            page: int = 1,
            page_size: int = 10,
            similarity_threshold: float = 0.2,
            vector_similarity_weight: float = 0.3,
            keyword: bool = False,
            top_k: int = 1024,
            rerank_id: str | None = None,
            force_refresh: bool = False,
        ) -> str:
            """Search your knowledge base to answer a question. Returns relevant document chunks with citations.

            This is a semantic search tool that finds the most relevant information from your RAGFlow knowledge base
            to answer the given question. All parameters except 'question' are optional and can be any value.

            Parameters:
            - question: The question or query to search for (required, always used)
            - dataset_ids: Optional dataset filter (can be list, string, or anything - will auto-validate)
            - document_ids: Optional document filter (can be list, string, or anything - will auto-validate)
            - page: Page number for results (default: 1)
            - page_size: Results per page (default: 10, max recommended 50)
            - similarity_threshold: Minimum relevance score (default: 0.2)
            - vector_similarity_weight: Balance between semantic and keyword matching (default: 0.3)
            - keyword: Enable keyword-based search (default: false)
            - top_k: Maximum candidates to consider before ranking (default: 1024)
            - rerank_id: Optional reranking model (rarely used)
            - force_refresh: Force fresh data from backend (default: false)

            Returns: JSON with search results containing document chunks, relevance scores, and citations
            """
            try:
                await self._ensure_connector_initialized()
                logger.info(f"🔍 search_documents() called: question={question[:80]}")

                # Normalize dataset_ids: accept anything and try to make sense of it
                normalized_dataset_ids: list[str] | None = None
                if dataset_ids:
                    # Handle various input types
                    if isinstance(dataset_ids, str):
                        # Single dataset ID as string
                        if dataset_ids.strip():  # Only if non-empty
                            normalized_dataset_ids = [dataset_ids.strip()]
                    elif isinstance(dataset_ids, list):
                        # List of IDs - filter out empty strings
                        normalized_dataset_ids = [
                            str(d).strip() for d in dataset_ids if d and str(d).strip()
                        ]
                    else:
                        # Try to convert to string and use if valid
                        str_val = str(dataset_ids).strip()
                        if str_val and str_val.lower() not in ("none", "null", "[]", ""):
                            normalized_dataset_ids = [str_val]

                # Normalize document_ids similarly
                normalized_document_ids: list[str] | None = None
                if document_ids:
                    if isinstance(document_ids, str):
                        if document_ids.strip():
                            normalized_document_ids = [document_ids.strip()]
                    elif isinstance(document_ids, list):
                        normalized_document_ids = [
                            str(d).strip() for d in document_ids if d and str(d).strip()
                        ]
                    else:
                        str_val = str(document_ids).strip()
                        if str_val and str_val.lower() not in ("none", "null", "[]", ""):
                            normalized_document_ids = [str_val]

                logger.info(f"📋 Normalized dataset_ids: {normalized_dataset_ids}")
                logger.info(f"📋 Normalized document_ids: {normalized_document_ids}")

                result = await self.connector.retrieval(
                    question=question,
                    dataset_ids=normalized_dataset_ids,
                    document_ids=normalized_document_ids,
                    page=page,
                    page_size=page_size,
                    similarity_threshold=similarity_threshold,
                    vector_similarity_weight=vector_similarity_weight,
                    keyword=keyword,
                    top_k=top_k,
                    rerank_id=rerank_id,
                    force_refresh=force_refresh,
                )

                logger.info(f"✅ Search returned {len(result.get('chunks', []))} chunks")
                return json.dumps(result, ensure_ascii=False)

            except Exception as e:
                logger.error(f"❌ Error in search_documents: {e}", exc_info=True)
                return json.dumps({
                    "error": f"Search failed: {str(e)}",
                    "chunks": [],
                })

        logger.info("MCP tools registered successfully")


@click.command()
@click.option(
    "--ragflow-base-url",
    type=str,
    required=False,
    help="RAGFlow backend base URL (e.g., http://ragflow:9380)",
    envvar="RAGFLOW_BASE_URL",
)
@click.option(
    "--ragflow-api-key",
    type=str,
    required=False,
    help="RAGFlow API key for authentication",
    envvar="RAGFLOW_API_KEY",
)
def main(ragflow_base_url: str | None = None, ragflow_api_key: str | None = None):
    """
    Start RAGFlow MCP Server (Docker MCP Toolkit compliant)

    Uses stdio transport for compatibility with MCP Gateway.

    Configuration:
        RAGFLOW_BASE_URL: RAGFlow backend URL (e.g., http://ragflow:9380)
        RAGFLOW_API_KEY: RAGFlow API key for authentication
    """

    try:
        # Get from environment if not provided via CLI
        if not ragflow_base_url:
            ragflow_base_url = os.environ.get("RAGFLOW_BASE_URL")
        if not ragflow_api_key:
            ragflow_api_key = os.environ.get("RAGFLOW_API_KEY")

        if not ragflow_base_url or not ragflow_api_key:
            raise click.UsageError(
                "Both --ragflow-base-url and --ragflow-api-key must be provided "
                "(or set RAGFLOW_BASE_URL and RAGFLOW_API_KEY env vars)"
            )

        server = RAGFlowMCPServer(
            base_url=ragflow_base_url,
            api_key=ragflow_api_key,
        )

        logger.info("Starting RAGFlow MCP Server")
        logger.info(f"  Backend: {ragflow_base_url}")
        logger.info("  Protocol: 2025-06-18")
        logger.info("  Transport: stdio (FastMCP)")

        # Run the server - FastMCP.run() manages the event loop internally
        # Connector will be lazy-initialized on first tool call within FastMCP's event loop
        server.mcp.run()

    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
