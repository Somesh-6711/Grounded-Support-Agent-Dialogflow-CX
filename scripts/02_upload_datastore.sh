#!/usr/bin/env bash
# Push the knowledge base HTML into a GCS bucket so the Conversational Agents
# data store can index it.
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID to your GCP project id}"
BUCKET="${BUCKET:-${PROJECT_ID}-ces-kb}"

cd "$(dirname "$0")/.."

if ! gcloud storage buckets describe "gs://$BUCKET" --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://$BUCKET" \
    --project "$PROJECT_ID" --location us-central1 --uniform-bucket-level-access
fi

gcloud storage cp datastore/*.html "gs://$BUCKET/kb/" --project "$PROJECT_ID"

echo
echo "Knowledge base uploaded. In the data store creation flow, choose"
echo "Cloud Storage, unstructured documents, and point it at:"
echo "  gs://$BUCKET/kb/*"
