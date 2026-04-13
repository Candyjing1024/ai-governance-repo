"""Update App Service environment variables with fresh keys from Key Vault"""
import requests
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

SUB_ID = "a3223db3-76f2-4a7c-8684-57b835dc77e7"
RG = "rg-chubb-mcp-poc"
ARM = "https://management.azure.com"

cred = DefaultAzureCredential()
token = cred.get_token("https://management.azure.com/.default").token
h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Get fresh secrets from Key Vault
kv = SecretClient(vault_url="https://kv-chubb-mcp-9342.vault.azure.net", credential=cred)
oai_key = kv.get_secret("aisvc-key").value
oai_endpoint = kv.get_secret("aisvc-endpoint").value
search_key = kv.get_secret("aisearch-key").value
search_endpoint = kv.get_secret("aisearch-endpoint").value

for app_name in ["app-chubb-backend-poc", "app-chubb-mcp-poc"]:
    print(f"\n{'='*50}")
    print(f"Updating: {app_name}")
    print(f"{'='*50}")

    # Get current app settings
    url = f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/Microsoft.Web/sites/{app_name}/config/appsettings/list?api-version=2022-09-01"
    r = requests.post(url, headers=h)
    if r.status_code != 200:
        print(f"  ERROR getting settings: HTTP {r.status_code}: {r.text[:300]}")
        continue

    current = r.json().get("properties", {})
    print(f"  Current env vars: {len(current)}")
    for k in sorted(current.keys()):
        v = current[k]
        display = v[:30] + "..." if v and len(v) > 30 else v
        print(f"    {k} = {display}")

    # Update with fresh values
    updates = {}
    if "AZURE_OPENAI_API_KEY" in current:
        updates["AZURE_OPENAI_API_KEY"] = oai_key
    if "AZURE_OPENAI_ENDPOINT" in current:
        updates["AZURE_OPENAI_ENDPOINT"] = oai_endpoint
    if "AZURE_SEARCH_KEY" in current:
        updates["AZURE_SEARCH_KEY"] = search_key
    if "AZURE_SEARCH_ENDPOINT" in current:
        updates["AZURE_SEARCH_ENDPOINT"] = search_endpoint

    if updates:
        current.update(updates)
        put_url = f"{ARM}/subscriptions/{SUB_ID}/resourceGroups/{RG}/providers/Microsoft.Web/sites/{app_name}/config/appsettings?api-version=2022-09-01"
        body = {"properties": current}
        r = requests.put(put_url, headers=h, json=body)
        print(f"\n  Updated {len(updates)} env vars: HTTP {r.status_code}")
        for k in updates:
            print(f"    {k} -> updated")
    else:
        print("\n  No matching env vars to update (may use Key Vault refs)")
        print("  App may be reading secrets directly from Key Vault at runtime")

print("\nDone! App Services may need a restart for changes to take effect.")
