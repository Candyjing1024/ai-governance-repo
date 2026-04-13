"""
Test MCP Server - WITHOUT Key Vault dependency
For debugging container deployment
"""

import os
import logging
from typing import Dict, Any, List

from fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp-server-test")

# Create MCP server with STATELESS HTTP mode
mcp = FastMCP("Test MCP Server", stateless_http=True)


@mcp.tool(
    name="healthcheck",
    description="Simple health check tool"
)
def healthcheck() -> Dict[str, str]:
    """Simple health check."""
    logger.info("healthcheck called")
    return {"status": "healthy", "message": "MCP server is running"}


@mcp.tool(
    name="echo",
    description="Echo back the input message"
)
def echo(message: str) -> Dict[str, str]:
    """Echo back a message."""
    logger.info(f"echo called with: {message}")
    return {"message": message, "echoed": "true"}


# Health check endpoint for App Service
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "healthy", "service": "mcp-test"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", os.environ.get("MCP_PORT", 8000)))
    logger.info(f"Starting TEST MCP Server on port {port}")
    logger.info("This version does NOT use Key Vault - for testing only")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
