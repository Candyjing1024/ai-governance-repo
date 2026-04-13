# Testing Scripts

Scripts for testing Azure services, MCP server endpoints, and Foundry agents.

## Overview

Testing scripts to validate:
- OpenAI connection and deployments
- MCP server endpoints
- App Service deployments
- Model deployments and inference
- End-to-end flows

## Scripts

### `testOAIconnection.py`
Tests Azure OpenAI connection and deployment.

**What it tests:**
1. Endpoint reachability
2. Authentication (API key or Managed Identity)
3. Model deployment exists
4. Completions API works
5. Response quality

**Usage:**
```bash
python testOAIconnection.py
```

**Configuration:**
```python
OPENAI_ENDPOINT = "https://<openai-resource-name>.openai.azure.com/"
OPENAI_KEY = "..."  # Or use DefaultAzureCredential
DEPLOYMENT_NAME = "gpt-4o"
```

**Tests:**
```python
# 1. List deployments
deployments = client.deployments.list()

# 2. Test completion
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}]
)

# 3. Verify response
assert response.choices[0].message.content
```

**Expected output:**
```
✓ Connection successful
✓ Model deployment found: gpt-4o
✓ Completion API working
✓ Response: "Hello! How can I help you today?"
```

### `test_appservice_mcp.py`
Tests MCP server deployed to App Service.

**What it tests:**
1. Health endpoint (`/health`)
2. Tools listing (`/tools`)
3. Tool invocation (`/tools/{name}`)
4. Error handling
5. Response times

**Usage:**
```bash
python test_appservice_mcp.py
```

**Configuration:**
```python
APP_SERVICE_URL = "https://<app-name>.azurewebsites.net"
SUBSCRIPTION_KEY = "..."  # If using APIM
```

**Test cases:**
```python
# Test 1: Health check
response = requests.get(f"{APP_SERVICE_URL}/health")
assert response.status_code == 200

# Test 2: List tools
response = requests.get(f"{APP_SERVICE_URL}/tools")
tools = response.json()["tools"]
assert len(tools) > 0

# Test 3: Invoke tool
response = requests.post(
    f"{APP_SERVICE_URL}/tools/search",
    json={"parameters": {"query": "AI governance"}}
)
assert response.status_code == 200

# Test 4: Error handling
response = requests.post(
    f"{APP_SERVICE_URL}/tools/invalid",
    json={}
)
assert response.status_code == 404
```

**Performance tests:**
```python
# Response time test
import time
start = time.time()
response = requests.post(f"{APP_SERVICE_URL}/tools/search", json=...)
duration = time.time() - start
assert duration < 2.0  # Less than 2 seconds
```

### `test_endpoints.py`
Tests various Azure service endpoints.

**What it tests:**
- Azure OpenAI endpoints
- Foundry endpoints
- Cosmos DB endpoints
- Key Vault endpoints
- Azure Search endpoints

**Usage:**
```bash
python test_endpoints.py
```

**Tests:**
```python
# Azure OpenAI
test_openai()  # Chat completions
test_embeddings()  # Embedding generation

# Foundry
test_foundry_agent()  # Agent invocation
test_foundry_thread()  # Thread creation

# Cosmos DB
test_cosmos_connection()  # Database access
test_cosmos_query()  # Query operations

# Key Vault
test_keyvault_secret()  # Secret retrieval

# Azure Search
test_search_query()  # Search query
test_vector_search()  # Vector search
```

**Output:**
```
Testing Azure OpenAI...
  ✓ Chat completion: 1.2s
  ✓ Embeddings: 0.8s

Testing Foundry...
  ✓ Agent invocation: 2.5s
  ✓ Thread creation: 0.5s

Testing Cosmos DB...
  ✓ Connection: 0.3s
  ✓ Query: 0.4s

Testing Key Vault...
  ✓ Secret retrieval: 0.6s

Testing Azure Search...
  ✓ Search query: 1.1s
  ✓ Vector search: 1.8s

All tests passed!
```

### `deploy_model_and_test.py`
Deploys model to Foundry and runs tests.

**What it does:**
1. Deploys model to Foundry account
2. Waits for deployment to complete
3. Runs inference tests
4. Validates responses
5. Tests rate limits
6. Checks error handling

**Usage:**
```bash
python deploy_model_and_test.py
```

**Configuration:**
```python
ACCOUNT_NAME = "<foundry-account-name>"
MODEL_NAME = "gpt-4o"
DEPLOYMENT_NAME = "gpt-4o-deployment"
CAPACITY = 10  # TPM in thousands
```

**Deployment:**
```python
# 1. Deploy model
deployment = create_deployment(
    account_name=ACCOUNT_NAME,
    model="gpt-4o",
    deployment_name="gpt-4o-deployment",
    sku={"name": "Standard", "capacity": 10}
)

# 2. Wait for provisioning
while deployment["properties"]["provisioningState"] != "Succeeded":
    time.sleep(10)
    deployment = get_deployment(...)

# 3. Test inference
response = test_inference(deployment_name="gpt-4o-deployment")
```

**Tests:**
```python
# Test 1: Basic completion
response = client.chat.completions.create(
    model="gpt-4o-deployment",
    messages=[{"role": "user", "content": "Hello"}]
)

# Test 2: Streaming
stream = client.chat.completions.create(
    model="gpt-4o-deployment",
    messages=[...],
    stream=True
)

# Test 3: Function calling
response = client.chat.completions.create(
    model="gpt-4o-deployment",
    messages=[...],
    functions=[...]
)

# Test 4: Rate limit handling
for i in range(100):
    try:
        response = client.chat.completions.create(...)
    except RateLimitError as e:
        print(f"Rate limited at request {i}")
```

**Expected output:**
```
Deploying model...
✓ Deployment created: gpt-4o-deployment
✓ Provisioning state: Creating
✓ Provisioning state: Succeeded

Testing inference...
✓ Basic completion: Working
✓ Streaming: Working
✓ Function calling: Working
✓ Rate limiting: 10,000 TPM

All tests passed!
```

## Dependencies

```bash
pip install pytest requests azure-identity azure-ai-projects openai
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test
```bash
python test_appservice_mcp.py
```

### Run with coverage
```bash
pytest --cov=. --cov-report=html
```

### Run in CI/CD
```bash
pytest --junitxml=test-results.xml
```

## Test Configuration

### Environment Variables
```bash
export AZURE_OPENAI_ENDPOINT="https://..."
export AZURE_OPENAI_KEY="..."
export APP_SERVICE_URL="https://..."
export FOUNDRY_ENDPOINT="https://..."
export TEST_MODE="integration"  # or "unit"
```

### Configuration File
Create `test_config.json`:
```json
{
  "endpoints": {
    "openai": "https://...",
    "foundry": "https://...",
    "appservice": "https://..."
  },
  "timeouts": {
    "health_check": 5,
    "api_call": 30,
    "deployment": 600
  },
  "retry": {
    "max_attempts": 3,
    "backoff": 2
  }
}
```

## Test Suites

### Unit Tests
Test individual functions in isolation:
```bash
pytest tests/unit/
```

### Integration Tests
Test interactions between components:
```bash
pytest tests/integration/
```

### End-to-End Tests
Test complete workflows:
```bash
pytest tests/e2e/
```

### Performance Tests
Test response times and throughput:
```bash
pytest tests/performance/
```

## Continuous Integration

### GitHub Actions
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest
```

### Azure DevOps
```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.11'
  - script: |
      pip install -r requirements.txt
      pytest --junitxml=test-results.xml
    displayName: 'Run tests'
  - task: PublishTestResults@2
    inputs:
      testResultsFiles: 'test-results.xml'
```

## Troubleshooting

### Tests Fail Intermittently
- Add retries with exponential backoff
- Check network connectivity
- Verify service availability

### Timeout Errors
- Increase timeout values
- Check service performance
- Verify resource capacity

### Authentication Errors
- Check API keys/credentials
- Verify RBAC assignments
- Test with DefaultAzureCredential

## Best Practices

1. **Use fixtures** for setup/teardown
2. **Mock external dependencies** in unit tests
3. **Use real services** in integration tests
4. **Parameterize tests** for multiple scenarios
5. **Assert specific values**, not just success
6. **Clean up resources** after tests
7. **Log test failures** with context
8. **Monitor test execution time**

## References

- [pytest Documentation](https://docs.pytest.org/)
- [Azure OpenAI Testing](https://docs.microsoft.com/azure/cognitive-services/openai/)
- [Azure App Service Testing](https://docs.microsoft.com/azure/app-service/deploy-best-practices)
