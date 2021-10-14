#!/bin/bash
# this simulates passing the google credentials to the container for developing
docker run -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/creds.json \
        -v ~/.config/gcloud/application_default_credentials.json:/tmp/keys/creds.json:ro \
        -e APP_SECRET=1234++secret \
        -p 80:80 \
         bucket-proxy