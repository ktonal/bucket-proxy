#!/bin/bash

docker build -t gcr.io/ax6-project/bucket-proxy .

gcloud builds submit --tag gcr.io/ax6-project/bucket-proxy

gcloud run deploy bucket-proxy --image gcr.io/ax6-project/bucket-proxy --region europe-west6