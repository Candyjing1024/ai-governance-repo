
"""
FastMCP Server - STATELESS MODE
================================
Uses Streamable HTTP with stateless mode for potential APIM compatibility.
Still uses SSE internally but eliminates session management.

Deploy to Azure App Service with:
    az webapp up --runtime PYTHON:3.11 --sku B1
"""

import os
import logging
from typing import Dict, Any, List

from fastmcp import FastMCP
from rag_tool import domain_search_retrieval

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp-server")

# Create MCP server with STATELESS HTTP mode
mcp = FastMCP("ASTRA MCP Server", stateless_http=True)


@mcp.tool(
    name="domain_search",
    description="Search the knowledge base for relevant information"
)
def domain_search(query: str, top_results: int = 3) -> Dict[str, List[Dict[str, Any]]]:
    """
    Search Azure AI Search for domain knowledge and return relevant chunks.
    
    Args:
        query: The search query text
        top_results: Number of results to return (1-20, default: 3)
        
    Returns:
        Dictionary containing list of search results with content and metadata
    """
    logger.info(f"domain_search called: query='{query[:50]}...', top={top_results}")
    
    try:
        results = domain_search_retrieval(query, top_results)
        logger.info(f"Retrieved {len(results)} results")
        return {"results": results}
    except Exception as e:
        logger.error(f"Error in domain_search: {e}")
        return {"results": [], "error": str(e)}


@mcp.tool(
    name="list_tools",
    description="List all available tools on this MCP server"
)
def list_tools() -> Dict[str, Any]:
    """Return metadata about available tools."""
    return {
        "tools": [
            {
                "name": "domain_search",
                "description": "Search the knowledge base for relevant information",
                "parameters": {
                    "query": {"type": "string", "required": True},
                    "top_results": {"type": "integer", "default": 3}
                }
            }
        ]
    }


# Health check endpoint for App Service
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "healthy", "service": "mcp-stateless"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", os.environ.get("MCP_PORT", 8000)))
    logger.info(f"Starting MCP Server (STATELESS) on port {port}")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
 