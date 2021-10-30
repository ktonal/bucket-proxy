#!/bin/bash

set -e

docker build --no-cache -t gcr.io/ax6-project/bucket-proxy:latest .

gcloud container images delete gcr.io/ax6-project/bucket-proxy:latest --force-delete-tags

docker push gcr.io/ax6-project/bucket-proxy:latest

gcloud run deploy bucket-proxy --image gcr.io/ax6-project/bucket-proxy:latest --region europe-west6