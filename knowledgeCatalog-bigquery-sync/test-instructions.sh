#!/usr/bin/env bash
set -e

# Automatically resolve the active Google Cloud project
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project 2>/dev/null)
export GOOGLE_CLOUD_REGION="us-central1"

# Validate that a project ID is present
if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "❌ ERROR: No active GCP project configured in gcloud."
    echo "Run 'gcloud config set project <your-project-id>' first."
    exit 1
fi

echo "=========================================="
echo " Running Knowledge Catalog Verification"
echo " Project: ${GOOGLE_CLOUD_PROJECT}"
echo " Region:  ${GOOGLE_CLOUD_REGION}"
echo "=========================================="

# Run the test script
python test-knowledge-catalog-setup.py