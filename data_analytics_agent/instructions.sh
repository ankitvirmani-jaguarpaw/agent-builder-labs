#!/usr/bin/env bash
set -e

echo "==================================================================="
echo " Data Analytics Worker Agent - Complete Prerequisites Setup"
echo "==================================================================="

# -----------------------------------------------------------------------------
# 1. Project, Account & Region Detection
# -----------------------------------------------------------------------------
export PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
export USER_EMAIL=$(gcloud config get-value account 2>/dev/null)
export REGION="us-central1"
export CATALOG_MCP_URL="https://knowledge-catalog-mcp-34m7rs7eva-uc.a.run.app/sse"

if [ -z "$PROJECT_ID" ]; then
    echo "❌ ERROR: No active Google Cloud project set in gcloud."
    echo "Run 'gcloud config set project <your-project-id>' first."
    exit 1
fi

if [ -z "$USER_EMAIL" ]; then
    echo "❌ ERROR: No active Google account found."
    echo "Run 'gcloud auth login' first."
    exit 1
fi

export PROJECT_NUM=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')

echo "Active Project:  ${PROJECT_ID} (Number: ${PROJECT_NUM})"
echo "Active Account:  ${USER_EMAIL}"
echo "Catalog MCP URL: ${CATALOG_MCP_URL}"

# -----------------------------------------------------------------------------
# 2. Enable Required APIs (BigQuery & Vertex AI Agent Engine)
# -----------------------------------------------------------------------------
echo -e "\n=== Step 1: Enabling Required APIs ==="
gcloud services enable \
    bigquery.googleapis.com \
    aiplatform.googleapis.com \
    run.googleapis.com

echo "[✓] APIs enabled successfully."

# -----------------------------------------------------------------------------
# 3. Grant IAM Roles to User & Agent Engine Service Accounts
# -----------------------------------------------------------------------------
echo -e "\n=== Step 2: Configuring IAM Permissions ==="

# User permissions to run BigQuery and manage Vertex AI Agent Engine
USER_ROLES=(
    "roles/bigquery.jobUser"
    "roles/bigquery.dataViewer"
    "roles/aiplatform.user"
)

for role in "${USER_ROLES[@]}"; do
    echo "Assigning ${role} to ${USER_EMAIL}..."
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="user:${USER_EMAIL}" \
        --role="${role}" \
        --condition=None >/dev/null
done

# Ensure Vertex AI service identity exists and has BigQuery permissions
echo "Ensuring Vertex AI service account has BigQuery access..."
gcloud beta services identity create --service=aiplatform.googleapis.com --project="${PROJECT_ID}" 2>/dev/null || true

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:service-${PROJECT_NUM}@gcp-sa-aiplatform.iam.gserviceaccount.com" \
    --role="roles/bigquery.jobUser" \
    --condition=None >/dev/null 2>&1 || true

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:service-${PROJECT_NUM}@gcp-sa-aiplatform.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataViewer" \
    --condition=None >/dev/null 2>&1 || true

echo "[✓] IAM roles configured successfully."

# -----------------------------------------------------------------------------
# 4. Install Python Dependencies
# -----------------------------------------------------------------------------
echo -e "\n=== Step 3: Installing Python Libraries ==="
pip install --upgrade \
    "google-adk[mcp]>=2.6.0" \
    fastmcp \
    google-cloud-bigquery

echo "[✓] Python dependencies installed successfully."

# -----------------------------------------------------------------------------
# 5. Summary & Export Instructions
# -----------------------------------------------------------------------------
echo -e "\n==================================================================="
echo " 🎉 Prerequisites Setup Completed!"
echo "==================================================================="
echo "Run this command to load the environment variables into your shell:"
echo ""
echo "  export GOOGLE_CLOUD_PROJECT=\"${PROJECT_ID}\""
echo "  export GOOGLE_CLOUD_REGION=\"${REGION}\""
echo "  export CATALOG_MCP_URL=\"${CATALOG_MCP_URL}\""
echo ""
echo "Then you can run your agent test script:"
echo "  python test_worker_agent.py"
echo "==================================================================="
