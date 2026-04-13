import asyncio
import os
from fastmcp.client import Client


async def main():
    base_url = os.environ.get(
        "APIM_MCP_URL",
        "https://apim-chubb.azure-api.net/astra-mcp/mcp",
    )
    print(f"Connecting to MCP at {base_url}")
    # APIM for this endpoint does not require a subscription key; connect directly.
    async with Client(base_url) as client:
        print("✅ Connected")

        print("\n📋 Listing tools...")
        tools = await client.list_tools()
        print(f"Available tools: {[t.name for t in tools]}")

        # Pick the right tool name (APIM may expose getDomainSearch instead of domain_search)
        tool_names = {t.name for t in tools}
        domain_tool_name = (
            "domain_search"
            if "domain_search" in tool_names
            else "getDomainSearch"
            if "getDomainSearch" in tool_names
            else None
        )
        if not domain_tool_name:
            print("No domain search tool found; skipping call.")
            return

        print(f"\n🔧 Calling {domain_tool_name}...")
        result = await asyncio.wait_for(
            client.call_tool(
                domain_tool_name,
                {"query": "What is Chubb?", "top_results": 3},
            ),
            timeout=60,
        )
        print("Result:", result)


if __name__ == "__main__":
    asyncio.run(main())
