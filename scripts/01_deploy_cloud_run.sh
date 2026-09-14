#!/usr/bin/env bash
# Build and deploy the tool service to Cloud Run, then print the URL you
# need to paste into openapi/tools.yaml.
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID to your GCP project id}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-ces-tool-service}"

cd "$(dirname "$0")/.."

# --allow-unauthenticated is for the demo only. See README section 7 for the
# service-agent auth setup you would actually ship.
gcloud run deploy "$SERVICE" \
  --source . \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --timeout 30s \
  --quiet

URL=$(gcloud run services describe "$SERVICE" \
  --project "$PROJECT_ID" --region "$REGION" \
  --format 'value(status.url)')

echo
echo "=================================================================="
echo " Service URL: $URL"
echo
echo " Next: open openapi/tools.yaml and replace"
echo "   https://REPLACE-WITH-YOUR-CLOUD-RUN-URL"
echo " with the URL above."
echo "=================================================================="
