#!/usr/bin/env bash
set -e

export PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
export REGION="us-central1"
export SERVICE_NAME="knowledge-catalog-mcp"

# Safety check: exit immediately if gcloud has no active project
if [ -z "$PROJECT_ID" ]; then
    echo "❌ ERROR: No active project found in gcloud config."
    echo "Set your project with: gcloud config set project <YOUR_PROJECT_ID>"
    exit 1
fi

echo "========================================================================="
echo " Deploying Knowledge Catalog MCP Server to Cloud Run"
echo " Project: ${PROJECT_ID}"
echo " Region:  ${REGION}"
echo " Service: ${SERVICE_NAME}"
echo "========================================================================="

# Deploy directly from source (Builds container in Artifact Registry and deploys)
gcloud run deploy "${SERVICE_NAME}" \
    --source . \
    --platform managed \
    --region "${REGION}" \
    --set-env-vars GOOGLE_CLOUD_PROJECT="${PROJECT_ID}",GOOGLE_CLOUD_REGION="${REGION}" \
    --allow-unauthenticated

# Retrieve and print the live URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --platform managed --region "${REGION}" --format 'value(status.url)')

echo -e "\n========================================================================="
echo " 🎉 Knowledge Catalog MCP Server Deployed Successfully!"
echo " Live SSE Endpoint: ${SERVICE_URL}/sse"
echo " Export this for your Agent: export CATALOG_MCP_URL=\"${SERVICE_URL}/sse\""
echo "========================================================================="