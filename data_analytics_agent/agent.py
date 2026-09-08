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
# Configuration
# =====================================================================
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
if not PROJECT_ID:
    raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is required.")

CATALOG_MCP_URL = os.getenv(
    "CATALOG_MCP_URL",
    "https://knowledge-catalog-mcp-34m7rs7eva-uc.a.run.app/sse",
)
agent_engine_id = os.getenv("GOOGLE_CLOUD_AGENT_ENGINE_ID")

credentials, _ = google.auth.default()

# Enforce Vertex AI backend for all Google LLM calls
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
JUDGE_AGENT_URL = os.getenv("JUDGE_AGENT_URL",
"https://judge-agent-34m7rs7eva-uc.a.run.app")
if not JUDGE_AGENT_URL:
    raise ValueError("JUDGE_AGENT_URL environment variable is required.")



# =====================================================================
# Tool 1: Knowledge Catalog MCP Connector (Tokenomics Layer)
# =====================================================================
async def query_knowledge_catalog(search_query: str) -> str:
    """Consults the Knowledge Catalog MCP server to discover business formulas,
    metric definitions, and BigQuery table partition rules.

    Args:
        search_query: Concept, metric name, or table name (e.g. 'bounce rate', 'active users', 'ga_sessions').
    """
    logger.info(f"--- 🛠️ Calling Knowledge Catalog MCP: '{search_query}' ---")
    try:
        async with Client(CATALOG_MCP_URL) as mcp_client:
            # 1. Search semantic catalog
            search_res = await mcp_client.call_tool(
                "search_knowledge_catalog",
                arguments={"query": search_query}
            )
            raw_text = search_res.content[0].text if search_res.content else ""

            if "results" in raw_text:
                return raw_text

            # 2. Fallback to direct metric lookup
            metric_res = await mcp_client.call_tool(
                "get_semantic_metric",
                arguments={"metric_name": search_query}
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

CRITICAL OPERATIONAL RULES:

1. MANDATORY KNOWLEDGE CATALOG DISCOVERY (Phase 1):
   - You MUST call `query_knowledge_catalog` FIRST on every user request.
   - If the user asks for a formula, metric definition, or table schema:
     --> Answer immediately from the catalog.
     --> YOU ARE STRICTLY FORBIDDEN FROM RUNNING BIGQUERY JOBS for conceptual/definition questions.

2. BIGQUERY EXECUTION (Phase 2):
   - Only run SQL queries when actual rows, counts, or live aggregations are requested.
   - Use `{PROJECT_ID}` as the billing project.
   - Always enforce partition filters (_TABLE_SUFFIX) learned from the catalog.

3. MANDATORY A2A JUDGE REVIEW (Phase 3 - CRITICAL):
   - Whenever you execute a BigQuery query or produce analytical data, **YOU MUST NOT RETURN THE FINAL ANSWER DIRECTLY TO THE USER**.
   - You MUST call `transfer_to_agent` with agent_name='judge_agent' to submit your generated SQL and findings for quality review.
   - Only after `judge_agent` approves the submission should the final response be presented to the user.

4. USER PREFERENCES:
   - Remember user preferences (preferred date ranges, standard filters, default groupings) across conversation sessions.
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