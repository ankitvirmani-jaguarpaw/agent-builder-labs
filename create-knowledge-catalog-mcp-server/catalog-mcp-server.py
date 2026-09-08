"""catalog_mcp_server.py

Knowledge Catalog MCP Server aligned with production FastMCP standards.
Includes Cloud Run health check probes, structured logging, and Dataplex Universal Catalog tools.
"""

from __future__ import annotations

import asyncio
import logging
import os

from fastmcp import FastMCP
from google.cloud import dataplex_v1
from google.api_core.exceptions import NotFound
from starlette.requests import Request
from starlette.responses import Response

# -----------------------------------------------------------------------------
# 1. Logging & Server Initialization
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

mcp = FastMCP("Knowledge-Catalog-MCP")

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
ENTRY_GROUP_ID = "google-analytics-catalog"
ENTRY_GROUP_NAME = f"projects/{PROJECT_ID}/locations/{LOCATION}/entryGroups/{ENTRY_GROUP_ID}"

# Initialize Dataplex client
dataplex_client = dataplex_v1.CatalogServiceClient()


# -----------------------------------------------------------------------------
# 2. Cloud Run & A2A Health Check Probe
# -----------------------------------------------------------------------------
@mcp.custom_route("/", methods=["GET"])
async def handle_root(request: Request) -> Response:
    """Handles GET requests to '/' for Cloud Run startup/liveness and A2A health checks."""
    return Response(content="OK", media_type="text/plain", status_code=200)


# -----------------------------------------------------------------------------
# 3. Tool: Semantic Search (Scoped to Entry Group + Semantic Search Enabled)
# -----------------------------------------------------------------------------
@mcp.tool()
def search_knowledge_catalog(query: str) -> dict:
    """Performs semantic search across Dataplex Knowledge Catalog and returns full business definitions."""
    logger.info(f"--- 🛠️ Tool: search_knowledge_catalog called with: '{query}' ---")
    try:
        # Scope the query directly to our GA entry group
        clean_query = query.replace(f"entry_group:{ENTRY_GROUP_ID}", "").strip()
        scoped_query = f"entry_group:{ENTRY_GROUP_ID} {clean_query}".strip()

        # Execute search with semantic_search=True
        search_request = dataplex_v1.SearchEntriesRequest(
            name=f"projects/{PROJECT_ID}/locations/{LOCATION}",
            query=scoped_query,
            page_size=5,
            semantic_search=True,  # 👈 Enables semantic intent understanding
        )
        search_response = dataplex_client.search_entries(request=search_request)

        matches = []
        for result in search_response.results:
            entry_name = result.dataplex_entry.name
            entry_id = entry_name.split("/")[-1]

            # Hydrate search results with full description & SQL
            try:
                entry = dataplex_client.get_entry(
                    request=dataplex_v1.GetEntryRequest(
                        name=entry_name,
                        view=dataplex_v1.EntryView.FULL,
                    )
                )
                title = entry.entry_source.display_name if entry.entry_source else entry_id
                desc = entry.entry_source.description if entry.entry_source else "No description"
            except Exception:
                title = entry_id
                desc = "Available in catalog"

            matches.append({
                "entry_id": entry_id,
                "display_name": title,
                "definition_and_sql": desc,
            })

        if not matches:
            return {"status": "not_found", "message": f"No catalog matches found for '{query}'."}

        logger.info(f"✅ Found {len(matches)} semantic matches.")
        return {
            "status": "success",
            "source": "Dataplex Universal Catalog Semantic Search",
            "query": query,
            "results": matches,
        }

    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        return {"error": f"Search failed: {e}"}


# -----------------------------------------------------------------------------
# 4. Tool: Exact Metric Lookup
# -----------------------------------------------------------------------------
@mcp.tool()
def get_semantic_metric(metric_name: str) -> dict:
    """Fetch official business definition, formula, and canonical SQL for a metric.

    Args:
        metric_name: Metric identifier (e.g., 'bounce_rate', 'monthly_active_users').
    """
    logger.info(f"--- 🛠️ Tool: get_semantic_metric called for: '{metric_name}' ---")
    entry_id = metric_name.lower().strip().replace("_", "-")
    entry_name = f"{ENTRY_GROUP_NAME}/entries/{entry_id}"
    try:
        request = dataplex_v1.GetEntryRequest(
            name=entry_name,
            view=dataplex_v1.EntryView.FULL,
        )
        entry = dataplex_client.get_entry(request=request)
        desc = entry.entry_source.description if entry.entry_source else "No description available."
        display_name = entry.entry_source.display_name if entry.entry_source else entry_id

        logger.info(f"✅ Retrieved metric: {display_name}")
        return {
            "status": "success",
            "source": "Dataplex Universal Catalog",
            "metric_name": display_name,
            "definition_and_sql": desc,
        }
    except NotFound:
        logger.error(f"❌ Metric not found: {entry_id}")
        return {"status": "not_found", "message": f"Metric '{metric_name}' not found."}
    except Exception as e:
        logger.error(f"❌ Error fetching metric: {e}")
        return {"error": str(e)}


# -----------------------------------------------------------------------------
# 5. Tool: Table Metadata & Partition Guidelines
# -----------------------------------------------------------------------------
@mcp.tool()
def get_table_metadata(table_alias: str) -> dict:
    """Retrieve partitioning requirements, cost warnings, and schema guidelines for a table.

    Args:
        table_alias: Logical table name (e.g., 'ga_sessions').
    """
    logger.info(f"--- 🛠️ Tool: get_table_metadata called for: '{table_alias}' ---")
    normalized = table_alias.lower().strip().replace("_", "-")
    entry_id = f"{normalized}-table-spec" if not normalized.endswith("-table-spec") else normalized
    entry_name = f"{ENTRY_GROUP_NAME}/entries/{entry_id}"
    try:
        request = dataplex_v1.GetEntryRequest(
            name=entry_name,
            view=dataplex_v1.EntryView.FULL,
        )
        entry = dataplex_client.get_entry(request=request)
        desc = entry.entry_source.description if entry.entry_source else "No spec available."
        display_name = entry.entry_source.display_name if entry.entry_source else entry_id

        logger.info(f"✅ Retrieved table spec: {display_name}")
        return {
            "status": "success",
            "source": "Dataplex Universal Catalog",
            "table_alias": table_alias,
            "display_name": display_name,
            "guidelines": desc,
        }
    except NotFound:
        logger.error(f"❌ Table spec not found: {entry_id}")
        return {"status": "not_found", "message": f"Table spec for '{table_alias}' not found."}
    except Exception as e:
        logger.error(f"❌ Error fetching table metadata: {e}")
        return {"error": str(e)}


# -----------------------------------------------------------------------------
# 6. Server Runner
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 Knowledge Catalog MCP server started on port {port} (SSE Transport)")

    asyncio.run(
        mcp.run_async(
            transport="sse",
            host="0.0.0.0",
            port=port,
        )
    )