"""worker_agent.py

Data Analytics Worker Agent with strict Tokenomics Governance:
- Consults Knowledge Catalog MCP Server first.
- Strict Circuit Breaker: Does NOT hit BigQuery if the question can be resolved
  via metadata, metric definitions, or canonical formulas.
- Only hits BigQuery when concrete row-level data or live metrics are requested.
"""

from __future__ import annotations

import json
import logging
import os
import google.auth
from fastmcp import Client

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.tools.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# =====================================================================
# Configuration (Container-Safe: Loaded from Env / ADC)
# =====================================================================
credentials, auth_project = google.auth.default()

# 1. Resolve Project ID
PROJECT_ID = (
    os.getenv("GOOGLE_CLOUD_PROJECT")
    or auth_project
    or os.getenv("DEVSHELL_PROJECT_ID")
)
if not PROJECT_ID:
    raise ValueError(
        "GOOGLE_CLOUD_PROJECT environment variable is required and could not be detected."
    )

# 2. Location & Model Backend
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"] = LOCATION

# 3. Resolve URLs
CATALOG_MCP_URL = os.getenv("CATALOG_MCP_URL")
if not CATALOG_MCP_URL:
    raise ValueError(
        "CATALOG_MCP_URL environment variable is required. Ensure it is defined in .env before deployment."
    )

JUDGE_AGENT_URL = os.getenv("JUDGE_AGENT_URL")
if not JUDGE_AGENT_URL:
    raise ValueError(
        "JUDGE_AGENT_URL environment variable is required. Ensure it is defined in .env before deployment."
    )

agent_engine_id = os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_ID")

logger.info(f"Target Project ID: {PROJECT_ID}")
logger.info(f"Knowledge Catalog SSE URL: {CATALOG_MCP_URL}")
logger.info(f"Judge Agent URL: {JUDGE_AGENT_URL}")


# =====================================================================
# Tool 1: Knowledge Catalog MCP Connector (Tokenomics Layer)
# =====================================================================
async def query_knowledge_catalog(search_query: str) -> str:
    """Primary tool for discovering available datasets, tables, schemas, metrics,
    business formulas, and partition rules.

    You MUST invoke this tool first to locate the project, dataset names, and
    table references before performing any BigQuery operations.

    Args:
        search_query: Query string such as 'available datasets', table name, or
          metric concept.
    """
    logger.info(f"--- 🛠️ Calling Knowledge Catalog MCP: '{search_query}' ---")
    try:
        async with Client(CATALOG_MCP_URL) as mcp_client:
            # 1. Search semantic catalog
            search_res = await mcp_client.call_tool(
                "search_knowledge_catalog",
                arguments={"query": search_query},
            )
            raw_text = search_res.content[0].text if search_res.content else ""

            if "results" in raw_text:
                return raw_text

            # 2. Fallback to direct metric lookup
            metric_res = await mcp_client.call_tool(
                "get_semantic_metric",
                arguments={"metric_name": search_query},
            )
            return metric_res.content[0].text if metric_res.content else raw_text

    except Exception as e:
        logger.error(f"Error querying Knowledge Catalog MCP: {e}")
        return f"Knowledge Catalog error: {str(e)}"


# =====================================================================
# Tool 2: BigQuery Toolset (Execution Layer)
# =====================================================================
bq_toolset = BigQueryToolset(
    credentials_config=BigQueryCredentialsConfig(credentials=credentials)
)


# =====================================================================
# Memory Callback
# =====================================================================
async def _save_memory(callback_context: CallbackContext) -> None:
    """Persists user session and preferences to Agent Engine Memory Bank."""
    if agent_engine_id:
        try:
            await callback_context.add_session_to_memory()
        except Exception as e:
            logger.warning(f"Memory persistence bypassed: {e}")


# =====================================================================
# Agent Instruction with Strict Tokenomics Governance Rules
# =====================================================================
TOKENOMICS_GOVERNANCE_INSTRUCTION = f"""You are an elite Data Analytics Worker Agent with strict Tokenomics & Governance.

CRITICAL OPERATIONAL SEQUENCE:

1. MANDATORY CATALOG DISCOVERY (Step 1 - STRICT):
   - You are STRICTLY FORBIDDEN from invoking any BigQuery tools (including listing datasets/tables or running SQL) without FIRST calling `query_knowledge_catalog`.
   - If the user asks general questions like "What datasets are available?" or asks about schemas/metrics:
     --> Call `query_knowledge_catalog(search_query="available datasets")`.
     --> Do NOT call BigQuery `list_datasets`.

2. BIGQUERY EXECUTION (Step 2):
   - Only query BigQuery when live rows or values are requested that cannot be answered by the catalog.
   - Use `{PROJECT_ID}` as the billing project.

3. MANDATORY A2A JUDGE REVIEW (Step 3):
   - Transfer to `judge_agent` before returning analytical answers to the user.
"""

# =====================================================================
# Sub-Agent: Remote Judge Agent via A2A Protocol
# =====================================================================
judge_proxy = RemoteA2aAgent(
    name="judge_agent",
    description="Remote Judge Agent evaluating query efficiency, semantic alignment, and accuracy over A2A.",
    agent_card=f"{JUDGE_AGENT_URL}/.well-known/agent-card.json",
    use_legacy=False,
)

root_agent = LlmAgent(
    name="data_analytics_worker_agent",
    model="gemini-2.5-pro",
    instruction=TOKENOMICS_GOVERNANCE_INSTRUCTION,
    tools=[
        query_knowledge_catalog,
        bq_toolset,
        PreloadMemoryTool(),
    ],
    sub_agents=[judge_proxy],
    after_agent_callback=_save_memory,
)

app = App(
    name="data_analytics_agent",
    root_agent=root_agent,
)
