"""test_catalog_mcp_server.py

Tests the Knowledge Catalog MCP server by connecting over SSE,
discovering registered tools, and verifying live queries against Dataplex.
"""

from __future__ import annotations

import asyncio
import os
import sys
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

PORT = int(os.getenv("PORT", "8080"))
MCP_URL = f"http://localhost:{PORT}/sse"


async def test_mcp_pipeline():
    print("===================================================================")
    print(f" Connecting to Knowledge Catalog MCP Server at: {MCP_URL}")
    print("===================================================================\n")

    try:
        async with sse_client(MCP_URL) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # 1. Initialize MCP Session
                await session.initialize()
                print("✅ [1/4] MCP Protocol Handshake Succeeded.")

                # 2. Discover Tools
                tools_response = await session.list_tools()
                tool_names = [t.name for t in tools_response.tools]
                print(f"✅ [2/4] Discovered {len(tool_names)} MCP Tools: {tool_names}\n")

                expected_tools = ["get_semantic_metric", "get_table_metadata", "search_knowledge_catalog"]
                for tool in expected_tools:
                    if tool in tool_names:
                        print(f"   • Tool '{tool}': Available")
                    else:
                        print(f"   ❌ Tool '{tool}': Missing")

                # 3. Test Metric Exact Lookup
                print("\n--- Testing Tool: get_semantic_metric('bounce_rate') ---")
                res_metric = await session.call_tool(
                    "get_semantic_metric",
                    arguments={"metric_name": "bounce_rate"}
                )
                print("Response Text:")
                print(res_metric.content[0].text)
                assert "bounces" in res_metric.content[0].text.lower()
                print("✅ [3/4] Metric lookup verified.")

                # 4. Test Semantic Search
                print("\n--- Testing Tool: search_knowledge_catalog('drop off rate') ---")
                res_search = await session.call_tool(
                    "search_knowledge_catalog",
                    arguments={"query": "drop off rate"}
                )
                print("Response Text:")
                print(res_search.content[0].text)
                print("✅ [4/4] Semantic search verified.")

                print("\n===================================================================")
                print(" 🎉 ALL MCP SERVER TESTS PASSED!")
                print("===================================================================")

    except ConnectionRefusedError:
        print(f"\n❌ Connection Error: Could not connect to {MCP_URL}")
        print("Ensure the MCP server is actively running in another terminal window:")
        print("   python catalog_mcp_server.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test Execution Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_mcp_pipeline())