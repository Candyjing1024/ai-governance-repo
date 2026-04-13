import requests
from azure.identity import DefaultAzureCredential
cred = DefaultAzureCredential()
token = cred.get_token("https://management.azure.com/.default").token
h = {"Authorization": f"Bearer {token}"}
url = "https://management.azure.com/subscriptions/a3223db3-76f2-4a7c-8684-57b835dc77e7/resourceGroups/rg-chubb-mcp-poc/providers/Microsoft.Search/searchServices/srch-chubb-mcp-9342?api-version=2023-11-01"
r = requests.get(url, headers=h)
d = r.json()
print("SKU:", d["sku"])
print("Status:", d["properties"]["status"])
print("Replicas:", d["properties"]["replicaCount"])
print("Partitions:", d["properties"]["partitionCount"])
