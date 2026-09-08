#!/usr/bin/env bash
set -e

echo "==================================================================="
echo " Google Cloud Knowledge Catalog MCP - Prerequisites & Setup"
echo "==================================================================="

# -----------------------------------------------------------------------------
# 1. Project & Account Detection
# -----------------------------------------------------------------------------
export PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
export USER_EMAIL=$(gcloud config get-value account 2>/dev/null)
export REGION="us-central1"

if [ -z "$PROJECT_ID" ]; then
    echo "❌ ERROR: No active Google Cloud project configured."
    echo "Run 'gcloud config set project <your-project-id>' first."
    exit 1
fi

if [ -z "$USER_EMAIL" ]; then
    echo "❌ ERROR: No active Google account found."
    echo "Run 'gcloud auth login' first."
    exit 1
fi

echo "Active Project: ${PROJECT_ID}"
echo "Active User:    ${USER_EMAIL}"
echo "Target Region:  ${REGION}"

# -----------------------------------------------------------------------------
# 2. Enable Required Google Cloud APIs
# -----------------------------------------------------------------------------
echo -e "\n=== Step 1: Enabling Required Google Cloud APIs ==="
gcloud services enable \
    dataplex.googleapis.com \
    datacatalog.googleapis.com \
    bigquery.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com

echo "[✓] APIs enabled successfully."

# -----------------------------------------------------------------------------
# 3. Grant Required IAM Permissions
# -----------------------------------------------------------------------------
echo -e "\n=== Step 2: Granting IAM Roles to ${USER_EMAIL} ==="

ROLES=(
    "roles/dataplex.admin"           # Manage Entry Groups, Entries, and search Dataplex Catalog
    "roles/bigquery.dataViewer"      # Read schema and metadata from BigQuery tables
    "roles/bigquery.jobUser"         # Run BigQuery queries/jobs
    "roles/run.admin"                # Deploy and manage Cloud Run services
    "roles/iam.serviceAccountUser"   # Authorize Cloud Run service account execution
)

for role in "${ROLES[@]}"; do
    echo "Assigning ${role}..."
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="user:${USER_EMAIL}" \
        --role="${role}" \
        --condition=None >/dev/null
done

echo "[✓] IAM roles assigned successfully."

# -----------------------------------------------------------------------------
# 4. Install Python Dependencies
# -----------------------------------------------------------------------------
echo -e "\n=== Step 3: Installing Python Packages ==="

pip install --upgrade \
    fastmcp \
    starlette \
    uvicorn \
    google-cloud-dataplex \
    google-cloud-bigquery

echo "[✓] Python dependencies installed successfully."

# -----------------------------------------------------------------------------
# 5. Summary & Next Steps
# -----------------------------------------------------------------------------
echo -e "\n==================================================================="
echo " 🎉 Environment Setup Complete!"
echo "==================================================================="
echo "Next Steps to run the server:"
echo "1. Set environment variables:"
echo "   export GOOGLE_CLOUD_PROJECT=\"${PROJECT_ID}\""
echo "   export GOOGLE_CLOUD_REGION=\"${REGION}\""
echo "   export PORT=8080"
echo ""
echo "2. Run the server:"
echo "   python catalog_mcp_server.py"
echo "==================================================================="
