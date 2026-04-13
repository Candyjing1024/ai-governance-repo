#!/bin/bash
# Startup script for Azure App Service

# Start the MCP server with gunicorn
gunicorn mcp_server:mcp.app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120
