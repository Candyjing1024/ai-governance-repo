import asyncio
from fastmcp.client import Client
 
async def test_appservice_mcp():
    print("Testing MCP server on App Service")
    try:
        async with Client("https://app-chubb-mcp-poc.azurewebsites.net/mcp") as client:
            print("✓ Connected to MCP server")
           
            # List available tools
            print("\n📋 Listing available tools...")
            tools = await client.list_tools()
            print(f"Available tools: {[tool.name for tool in tools]}")
           
            # Call domain_search tool with a test query
            print("\n🔧 Calling domain_search tool (timeout=120s)...")
            result = await asyncio.wait_for(
                client.call_tool("domain_search", {"query": "What are the project objectives?"}),
                timeout=120.0
            )
           
            print(f"\n✓ Tool call successful!")
            print(f"Result type: {type(result)}")
           
            # Extract text from result
            if hasattr(result, 'content') and result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(f"📄 Response ({len(content.text)} chars):")
                        print(content.text[:500])
                        break
            else:
                print(f"📄 Response: {str(result)[:500]}")
           
            print("\n✅ Test completed successfully!")
               
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
 
if __name__ == "__main__":
    asyncio.run(test_appservice_mcp())