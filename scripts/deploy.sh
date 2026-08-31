#!/usr/bin/env bash
# CLEARFRAME Cloud Run Deployment Script (Bash)
set -euo pipefail

PROJECT_ID="${1:-${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null)}}"
REGION="${2:-us-central1}"
SERVICE_NAME="clearframe"

echo -e "\n=== CLEARFRAME Cloud Run Deployment ==="

if [[ -z "$PROJECT_ID" || "$PROJECT_ID" == "(unset)" ]]; then
    echo "[FAIL] No Google Cloud Project ID detected."
    echo "Please set your project ID via: gcloud config set project <PROJECT_ID>"
    exit 1
fi

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)" 2>/dev/null || true)
if [[ -n "$PROJECT_NUMBER" ]]; then
    echo "Configuring IAM permissions for Cloud Build, Vertex AI & Secret Manager..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" --role="roles/aiplatform.user" --quiet >/dev/null 2>&1 || true
    gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" --role="roles/storage.objectViewer" --quiet >/dev/null 2>&1 || true
    gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" --role="roles/secretmanager.secretAccessor" --quiet >/dev/null 2>&1 || true
    gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" --role="roles/storage.objectViewer" --quiet >/dev/null 2>&1 || true
fi

# Check or create secrets in Secret Manager
if ! gcloud secrets describe parallel-api-key --project="$PROJECT_ID" >/dev/null 2>&1; then
    if [[ -n "${PARALLEL_API_KEY:-}" ]]; then
        echo "Creating 'parallel-api-key' secret in Secret Manager..."
        echo -n "$PARALLEL_API_KEY" | gcloud secrets create parallel-api-key --data-file=- --project="$PROJECT_ID"
    fi
fi

if ! gcloud secrets describe gemini-api-key --project="$PROJECT_ID" >/dev/null 2>&1; then
    if [[ -n "${GEMINI_API_KEY:-}" ]]; then
        echo "Creating 'gemini-api-key' secret in Secret Manager..."
        echo -n "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=- --project="$PROJECT_ID"
    fi
fi

# Deploy to Cloud Run from source
echo "Submitting Cloud Run build..."
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_LOCATION=$REGION,ENABLE_PARALLEL_MONITORS=true" \
    --set-secrets "PARALLEL_API_KEY=parallel-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest"

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --project "$PROJECT_ID" --region "$REGION" --format="value(status.url)")
echo -e "\n======================================================="
echo "  DEPLOYMENT SUCCESSFUL!"
echo "  Public Hosted URL: $SERVICE_URL"
echo "  Set PUBLIC_BASE_URL=$SERVICE_URL for Parallel Monitor webhooks"
echo -e "=======================================================\n"
