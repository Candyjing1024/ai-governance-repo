# MCP Server Scripts

Model Context Protocol (MCP) server implementation and client scripts for AI governance.

## Overview

MCP (Model Context Protocol) is a protocol for connecting AI models with external tools and data sources. This folder contains:
- MCP server implementation
- MCP client implementations (standalone and APIM-integrated)
- RAG (Retrieval-Augmented Generation) tool
- Docker deployment files

## Scripts

### Server

#### `mcp_server.py`
Main MCP server implementation.

**Features:**
- Exposes tools for AI agents
- Handles tool invocations
- Integrates with Azure services
- Provides RAG capabilities

**Usage:**
```bash
python mcp_server.py
```

**Environment variables:**
```bash
export PORT=8000
export AZURE_OPENAI_ENDPOINT="https://..."
export AZURE_OPENAI_KEY="..."
```

#### `mcp_server_test.py`
Test suite for MCP server.

**What it tests:**
- Tool registration
- Tool invocation
- Error handling
- Response formatting

**Usage:**
```bash
python mcp_server_test.py
```

### Clients

#### `mcp_client.py`
Standalone MCP client for testing.

**Usage:**
```bash
python mcp_client.py
```

**Example:**
```python
from mcp_client import MCPClient

client = MCPClient("http://localhost:8000")
result = client.invoke_tool("search", {"query": "AI governance"})
print(result)
```

#### `mcp_client_apim.py`
MCP client integrated with Azure API Management.

**Features:**
- APIM authentication
- Token management
- Rate limiting
- Request routing

**Usage:**
```bash
python mcp_client_apim.py
```

**Configuration:**
```python
APIM_ENDPOINT = "https://<apim-service-name>.azure-api.net"
SUBSCRIPTION_KEY = "..."
```

### Tools

#### `rag_tool.py`
Retrieval-Augmented Generation (RAG) tool implementation.

**Features:**
- Document search via Azure AI Search
- Context retrieval
- Chunk management
- Relevance scoring

**Usage:**
```python
from rag_tool import RAGTool

rag = RAGTool()
context = rag.search("AI governance policies")
```

## Docker Deployment

### `Dockerfile`
Production Dockerfile for MCP server.

**Build:**
```bash
docker build -t mcp-server:latest -f Dockerfile .
```

**Run:**
```bash
docker run -p 8000:8000 \
  -e AZURE_OPENAI_ENDPOINT="..." \
  -e AZURE_OPENAI_KEY="..." \
  mcp-server:latest
```

### `Dockerfile.test`
Test Dockerfile with additional testing tools.

**Build:**
```bash
docker build -t mcp-server:test -f Dockerfile.test .
```

**Run tests:**
```bash
docker run mcp-server:test pytest
```

### `startup.sh`
Container startup script.

**What it does:**
1. Sets up environment variables
2. Runs database migrations (if any)
3. Starts MCP server
4. Health check endpoint

## Dependencies

```bash
pip install -r requirements.txt
```

**Key dependencies:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `azure-ai-projects` - Azure AI integration
- `azure-search-documents` - Azure AI Search
- `pydantic` - Data validation

## Configuration

### `requirements.txt`
Python dependencies for MCP server.

**Installation:**
```bash
pip install -r requirements.txt
```

## API Endpoints

### Health Check
```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### List Tools
```
GET /tools
```

Response:
```json
{
  "tools": [
    {"name": "search", "description": "Search documents"},
    {"name": "rag", "description": "Retrieve context"}
  ]
}
```

### Invoke Tool
```
POST /tools/{tool_name}
```

Request body:
```json
{
  "parameters": {
    "query": "AI governance"
  }
}
```

Response:
```json
{
  "result": {...},
  "status": "success"
}
```

## Testing

### Run all tests
```bash
python mcp_server_test.py
```

### Run with coverage
```bash
pytest --cov=mcp_server --cov-report=html
```

### Integration tests
```bash
python mcp_client.py --test
```

## Deployment

### Local Development
```bash
python mcp_server.py
```

### Docker Container
```bash
docker build -t mcp-server .
docker run -p 8000:8000 mcp-server
```

### Azure App Service
```bash
# See ../deployment/deploy-appservice-westus2.ps1
```

### Azure Container Apps
```bash
# See ../deployment/deploy-container.ps1
```

## Monitoring

### Logs
```bash
# Docker logs
docker logs -f <container-id>

# App Service logs
az webapp log tail --name <app-name> --resource-group <rg>
```

### Metrics
- Request count
- Response time
- Error rate
- Tool usage

## Security

### Authentication
- Token-based authentication
- APIM subscription keys
- Managed Identity for Azure services

### Environment Variables
Never commit these:
```bash
AZURE_OPENAI_KEY
AZURE_SEARCH_KEY
COSMOS_CONNECTION_STRING
```

Use Azure Key Vault:
```bash
export AZURE_KEY_VAULT_NAME="kv-chubb-mcp-poc"
```

## Troubleshooting

### Server Won't Start
Check:
1. Port 8000 not in use
2. Environment variables set
3. Dependencies installed

### Tool Invocation Fails
Check:
1. Tool registered correctly
2. Parameters valid
3. Azure service credentials

### APIM Integration Issues
Check:
1. Subscription key valid
2. APIM endpoint correct
3. Network connectivity

## References

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Azure AI Search Python SDK](https://pypi.org/project/azure-search-documents/)
