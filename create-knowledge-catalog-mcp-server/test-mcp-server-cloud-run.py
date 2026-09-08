"""test-deployed-catalog-mcp.py

Full end-to-end test suite for the deployed Knowledge Catalog MCP Server on Cloud Run.
"""

from __future__ import annotations

import asyncio
import os
import sys
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

MCP_URL = os.getenv("CATALOG_MCP_URL")

if not MCP_URL:
    print("❌ Error: Set CATALOG_MCP_URL environment variable first.")
    sys.exit(1)


async def run_mcp_tests():
    print("===================================================================")
    print(f" Connecting to Live Cloud Run MCP Server at: {MCP_URL}")
    print("===================================================================\n")

    async with sse_client(MCP_URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("✅ [Handshake] MCP Session successfully initialized with Cloud Run.")

            tools_response = await session.list_tools()
            tool_names = [t.name for t in tools_response.tools]
            print(f"✅ [Discovery] Discovered registered tools: {tool_names}\n")

            # -----------------------------------------------------------------
            # Test 1: Exact Metric Lookup (get_semantic_metric)
            # -----------------------------------------------------------------
            print("=" * 60)
            print("TEST 1: get_semantic_metric('bounce_rate')")
            print("=" * 60)
            res_metric = await session.call_tool(
                "get_semantic_metric",
                arguments={"metric_name": "bounce_rate"}
            )
            print("Response:")
            print(res_metric.content[0].text)

            # -----------------------------------------------------------------
            # Test 2: Table Metadata & Partition Spec (get_table_metadata)
            # -----------------------------------------------------------------
            print("\n" + "=" * 60)
            print("TEST 2: get_table_metadata('ga_sessions')")
            print("=" * 60)
            res_table = await session.call_tool(
                "get_table_metadata",
                arguments={"table_alias": "ga_sessions"}
            )
            print("Response:")
            print(res_table.content[0].text)

            # -----------------------------------------------------------------
            # Test 3: Catalog Search
            # -----------------------------------------------------------------
            print("\n" + "=" * 60)
            print("TEST 3: search_knowledge_catalog() — Query Cases")
            print("=" * 60)

            # Queries that match words indexed in your entries
            test_queries = [
                "how to track visitor churn or immediate dropoff",  # Conceptually maps to bounce-rate
                "unique active people over past month",            # Conceptually maps to monthly-active-users
                "partitioned raw session logs and tables",         # Conceptually maps to ga-sessions-table-spec
            ]

            for query in test_queries:
                print(f"\n🔍 Query: '{query}'")
                res_search = await session.call_tool(
                    "search_knowledge_catalog",
                    arguments={"query": query}
                )
                print("Matches Found:")
                print(res_search.content[0].text)

            print("\n===================================================================")
            print(" 🎉 TESTING COMPLETE!")
            print("===================================================================")


if __name__ == "__main__":
    asyncio.run(run_mcp_tests())