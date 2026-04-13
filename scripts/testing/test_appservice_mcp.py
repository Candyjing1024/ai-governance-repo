
import asyncio
from fastmcp.client import Client

async def test_appservice_mcp():
    print("🔍 Testing MCP server via APIM")
    try:
        # async with Client("http://localhost:8000/mcp") as client:
        async with Client("https://app-mcp-chubb-dev.azurewebsites.net/mcp") as client:
        # async with Client("https://apim-chubb.azure-api.net/domain-search-mcp/mcp") as client:
            print("✅ Connected to MCP server")
            
            # List available tools
            print("\n📋 Listing available tools...")
            tools = await client.list_tools()
            print(f"Available tools: {[tool.name for tool in tools]}")
            
            # Test list_tools tool
            print("\n🔧 Calling list_tools tool...")
            list_tools_result = await client.call_tool("list_tools", {})
            print(f"✅ list_tools call successful!")
            if hasattr(list_tools_result, 'content') and list_tools_result.content:
                for content in list_tools_result.content:
                    if hasattr(content, 'text'):
                        print(f"\n📄 list_tools JSON output:")
                        print(content.text)
                        break
            
            # Call domain_search tool
            print("\n🔧 Calling domain_search tool with query: 'What is Chubb?'")
            result = await asyncio.wait_for(
                client.call_tool("domain_search", {
                    "query": "What is Chubb?",
                    "top_results": 3
                }),
                timeout=60.0
            )
            
            print(f"\n✅ Tool call successful!")
            print(f"Result type: {type(result)}")
            
            # Extract text from result
            if hasattr(result, 'content') and result.content:
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(f"\n📄 Response ({len(content.text)} chars):")
                        print(content.text[:500])
                        break
            else:
                print(f"\n📄 Response: {str(result)[:500]}")
            
            print("\n✅ Test completed successfully!")
                
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_appservice_mcp())
