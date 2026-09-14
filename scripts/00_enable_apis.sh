#!/usr/bin/env bash
# One-time project setup. Run this first.
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID to your GCP project id}"
REGION="${REGION:-us-central1}"

gcloud config set project "$PROJECT_ID"

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  dialogflow.googleapis.com \
  discoveryengine.googleapis.com \
  storage.googleapis.com \
  aiplatform.googleapis.com

echo "APIs enabled on $PROJECT_ID (region $REGION)."
