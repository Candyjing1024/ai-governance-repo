"""Fix Key Vault: Update the aisearch-* secrets that config.py actually reads"""
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

cred = DefaultAzureCredential()
kv = SecretClient(vault_url="https://kv-chubb-mcp-9342.vault.azure.net", credential=cred)

# Read the fresh values from the search-* keys (set by restore script)
search_key = kv.get_secret("search-key").value
search_endpoint = kv.get_secret("search-endpoint").value

# Update the aisearch-* keys that config.py reads
kv.set_secret("aisearch-key", search_key)
print(f"Updated aisearch-key")
kv.set_secret("aisearch-endpoint", search_endpoint)
print(f"Updated aisearch-endpoint = {search_endpoint}")

# Verify aisvc-* also correct
oai_endpoint = kv.get_secret("aisvc-endpoint").value
print(f"aisvc-endpoint = {oai_endpoint}")
print("Done - Key Vault secrets aligned")
