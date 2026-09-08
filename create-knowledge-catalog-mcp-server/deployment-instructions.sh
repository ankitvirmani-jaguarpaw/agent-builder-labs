#!/usr/bin/env bash
set -e

echo "=== Configuring IAM Roles for Cloud Run & Cloud Build ==="

export PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
export PROJECT_NUM=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
export REGION="us-central1"

if [ -z "$PROJECT_ID" ]; then
    echo "❌ ERROR: No active project found. Run 'gcloud config set project <your-project>' first."
    exit 1
fi

echo "Project ID:     ${PROJECT_ID}"
echo "Project Number: ${PROJECT_NUM}"

# Enable Artifact Registry API
gcloud services enable artifactregistry.googleapis.com

# Create Artifact Registry docker repository if it doesn't already exist
gcloud artifacts repositories create cloud-run-source-deploy \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Cloud Run source deployments" 2>/dev/null || true

# 1. Grant Dataplex Viewer to Cloud Run runtime service account
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
    --role="roles/dataplex.viewer" \
    --condition=None >/dev/null

# 2. Grant Storage Admin for Cloud Build source tarballs
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
    --role="roles/storage.admin" \
    --condition=None >/dev/null

# 3. Grant Cloud Build builder permissions
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${PROJECT_NUM}@cloudbuild.gserviceaccount.com" \
    --role="roles/cloudbuild.builds.builder" \
    --condition=None >/dev/null

# 4. Grant Artifact Registry write permissions
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
    --role="roles/artifactregistry.writer" \
    --condition=None >/dev/null

# 5. Grant Cloud Logging write permissions
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
    --role="roles/logging.logWriter" \
    --condition=None >/dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
    --role="roles/dataplex.catalogViewer"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
    --role="roles/dataplex.catalogEditor"

echo "[✓] All Cloud Build and Cloud Run permissions configured successfully!"