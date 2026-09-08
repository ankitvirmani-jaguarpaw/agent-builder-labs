"""main.py

100% Dynamic A2A Server for Cloud Run.
- Zero static files in source control or Docker image.
- Zero hardcoded URLs or project IDs.
- Generates runtime AgentCard dynamically on boot matching the live environment.
"""

from __future__ import annotations

import json
import os
from urllib.parse import urlparse
import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from agent import judge_agent

PORT = int(os.getenv("PORT", "8080"))
PUBLIC_URL = os.getenv("A2A_PUBLIC_URL", "http://0.0.0.0:8080").rstrip("/")

# 1. Dynamically compute the canonical origin (scheme + netloc without internal ports)
parsed = urlparse(PUBLIC_URL)
canonical_origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else PUBLIC_URL

# 2. Dynamically construct the A2A AgentCard dictionary at boot
card_payload = {
    "name": judge_agent.name,
    "description": "Remote Judge Agent evaluating query efficiency, semantic alignment, and accuracy over A2A.",
    "supportedInterfaces": [
        {
            "url": canonical_origin,
            "protocolBinding": "JSONRPC",
            "protocolVersion": "1.0",
        }
    ],
    "version": "0.0.1",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
    },
    "defaultInputModes": ["text/plain"],
    "defaultOutputModes": ["text/plain"],
    "skills": [
        {
            "id": judge_agent.name,
            "name": "governance_evaluation",
            "description": "Evaluates SQL efficiency and analytical accuracy.",
            "tags": ["llm", "governance", "sql"],
        }
    ],
}

# 3. Write to temporary ephemeral storage at container startup (zero static repo files)
runtime_card_path = "/tmp/dynamic_agent_card.json"
with open(runtime_card_path, "w", encoding="utf-8") as f:
    json.dump(card_payload, f)

# 4. Initialize standard ADK A2A app using the dynamic card
a2a_app = to_a2a(
    agent=judge_agent,
    agent_card=runtime_card_path,
)

if __name__ == "__main__":
    uvicorn.run(a2a_app, host="0.0.0.0", port=PORT)