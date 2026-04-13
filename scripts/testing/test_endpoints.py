import requests

BASE_URL = "http://aci-mcp-test.westus2.azurecontainer.io:8000"
endpoints = ["/", "/health", "/sse", "/mcp", "/mcp/sse"]

print(f"\nTesting endpoints on {BASE_URL}...\n")

for endpoint in endpoints:
    url = BASE_URL + endpoint
    try:
        response = requests.get(url, timeout=5)
        print(f"✓ {endpoint:15} - Status: {response.status_code} - {response.text[:100]}")
    except Exception as e:
        print(f"✗ {endpoint:15} - Error: {str(e)[:80]}")

print("\n" + "="*60)
