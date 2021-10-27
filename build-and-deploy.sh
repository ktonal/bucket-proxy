#!/bin/bash

set -e

docker build -t gcr.io/ax6-project/bucket-proxy:latest .

gcloud builds submit --tag gcr.io/ax6-project/bucket-proxy:latest

gcloud run deploy bucket-proxy --image gcr.io/ax6-project/bucket-proxy:latest --region europe-west6