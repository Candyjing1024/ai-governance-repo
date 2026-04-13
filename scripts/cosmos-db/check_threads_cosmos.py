"""Check if Foundry agent threads are stored in Cosmos DB."""
import json
from azure.identity import DefaultAzureCredential
from azure.cosmos import CosmosClient

COSMOS_NAME = "cosmos-chubb-mcp-poc"
KNOWN_THREADS = [
    "thread_8UaMatlU75vsi5xZEGxmPNTD",  # first test (failed)
    "thread_fQxv9hyt02nDXOLCF51X7QnT",  # retry attempt 1 (failed)
    # attempt 2 thread (succeeded) - not captured but same run
]

cred = DefaultAzureCredential()
client = CosmosClient(f"https://{COSMOS_NAME}.documents.azure.com:443/", credential=cred)

print("=" * 60)
print("COSMOS DB: All databases and containers")
print("=" * 60)

databases = list(client.list_databases())
print(f"Databases: {[d['id'] for d in databases]}")

for db in databases:
    db_client = client.get_database_client(db["id"])
    containers = list(db_client.list_containers())
    print(f"\n{db['id']} ({len(containers)} containers):")
    for cont in containers:
        cont_client = db_client.get_container_client(cont["id"])
        # Count items
        count = list(cont_client.query_items(
            "SELECT VALUE COUNT(1) FROM c", enable_cross_partition_query=True))[0]
        print(f"  {cont['id']}: {count} items")

        # Search for thread IDs
        for tid in KNOWN_THREADS:
            results = list(cont_client.query_items(
                f"SELECT TOP 3 c.id, c.threadId, c.type FROM c WHERE CONTAINS(c.id, '{tid}') OR c.threadId = '{tid}'",
                enable_cross_partition_query=True))
            if results:
                print(f"    FOUND thread {tid}:")
                for r in results:
                    print(f"      {json.dumps(r, default=str)[:200]}")

        # Look for any items containing "thread_" to find agent thread data
        thread_items = list(cont_client.query_items(
            "SELECT TOP 5 c.id, c.threadId, c.type, c._ts FROM c WHERE STARTSWITH(c.id, 'thread_') OR IS_DEFINED(c.threadId)",
            enable_cross_partition_query=True))
        if thread_items:
            print(f"    Thread-related items ({len(thread_items)}):")
            for item in thread_items:
                print(f"      {json.dumps(item, default=str)[:200]}")

        # Sample latest items from each container
        latest = list(cont_client.query_items(
            "SELECT TOP 3 c.id, c.type, c._ts FROM c ORDER BY c._ts DESC",
            enable_cross_partition_query=True))
        if latest:
            print(f"    Latest 3 items:")
            for item in latest:
                print(f"      {json.dumps(item, default=str)[:200]}")

# Also search broadly for "asst_" (agent IDs) or "run_" patterns
print("\n" + "=" * 60)
print("SEARCH: Agent/Run/Thread patterns across all containers")
print("=" * 60)
for db in databases:
    db_client = client.get_database_client(db["id"])
    containers = list(db_client.list_containers())
    for cont in containers:
        cont_client = db_client.get_container_client(cont["id"])
        for pattern in ["asst_", "run_", "thread_"]:
            results = list(cont_client.query_items(
                f"SELECT TOP 3 c.id, c.type, c._ts FROM c WHERE STARTSWITH(c.id, '{pattern}')",
                enable_cross_partition_query=True))
            if results:
                print(f"  {db['id']}/{cont['id']} - '{pattern}' matches: {len(results)}")
                for r in results:
                    print(f"    {json.dumps(r, default=str)[:200]}")
