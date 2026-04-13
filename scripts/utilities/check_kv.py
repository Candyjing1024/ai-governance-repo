"""Quick check: List Key Vault secrets"""
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

cred = DefaultAzureCredential()
kv = SecretClient(vault_url="https://kv-chubb-mcp-9342.vault.azure.net", credential=cred)

print("Key Vault secrets:")
for s in kv.list_properties_of_secrets():
    print(f"  {s.name}")
