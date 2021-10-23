#!/bin/bash
# this simulates passing the google credentials to the container for developing
docker build -t bucket-proxy . && \
docker run \
        -e GCP_BUCKET=axx-data \
        -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/creds.json \
        -v ~/.config/gcloud/application_default_credentials.json:/tmp/keys/creds.json:ro \
        -p 80:80 \
         bucket-proxy