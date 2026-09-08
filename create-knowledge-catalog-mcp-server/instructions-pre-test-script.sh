export PROJECT_ID=$(gcloud config get-value project)
export PROJECT_NUM=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

# Grant Dataplex Viewer to Cloud Run's default runtime service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
    --role="roles/dataplex.viewer"