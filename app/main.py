import io
from typing import Optional
import os
import json
import re

from google.cloud import storage
from google.oauth2 import id_token
from google.auth.transport import requests

from fastapi import FastAPI, Depends, HTTPException, status, Header
from starlette.responses import StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
origins = [
    os.environ.get("AXX_CLIENT_URL", "https://confident-mestorf-42e03b.netlify.app"),
    "http://192.168.0.26:3000",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage_client = storage.Client("ax6-Project")
GCP_BUCKET = os.environ.get("GCP_BUCKET", "ax6-train-data")
bucket = storage_client.bucket(GCP_BUCKET)

AUDIOS_REGEX = re.compile(r"wav$|aif$|aiff$|mp3$|mp4$|m4a$", re.IGNORECASE)


def check_token(authorization: Optional[str] = Header(None)):
    try:
        user_id_token = authorization.split(" ")[-1]
        # Specify the CLIENT_ID of the app that accesses the backend:
        idinfo = id_token.verify_oauth2_token(user_id_token, requests.Request(),
                                              "955131018414-f46kce80kqakmpofouoief34050ni8e0.apps.googleusercontent.com")

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        user_id = idinfo['sub']
        return user_id
    except (ValueError, AttributeError):
        # Invalid token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get(
    "/list/",
    dependencies=[Depends(check_token)]
)
def list_all_blobs(
        prefix: Optional[str] = None, content_type: Optional[str] = None,
):
    return {"prefix": prefix,
            "blobs": [(blob.name, blob.content_type)
                      for blob in storage_client.list_blobs(bucket, prefix=prefix)
                      if content_type is None or content_type in blob.content_type]}


@app.get(
    "/table/",
    dependencies=[Depends(check_token)]
)
def get_table():
    # each json in the bucket is a row
    table = {}
    for blob in storage_client.list_blobs(bucket):
        if "text" not in blob.content_type:
            dirname = os.path.dirname(blob.name)
            if blob.content_type == "application/json":
                table.setdefault(dirname, {}).setdefault("json", json.loads(blob.download_as_string()))
                for sub_blob in storage_client.list_blobs(bucket, prefix=dirname):
                    if "audio" in sub_blob.content_type or re.search(AUDIOS_REGEX, os.path.splitext(sub_blob.name)[1]):
                        table.setdefault(dirname, {}).setdefault("audios", []).append(sub_blob.name)
    return table


@app.get(
    "/bytes/{blob_path:path}",
    dependencies=[Depends(check_token)]
)
def stream_bytes(blob_path: str):
    blob = bucket.blob(blob_path)
    raw = blob.download_as_bytes()
    return StreamingResponse(io.BytesIO(raw), media_type=blob.content_type)


@app.delete(
    "/blob/{blob_path:path}",
    dependencies=[Depends(check_token)]
)
def delete_blob(blob_path: str):
    return bucket.blob(blob_path).delete()
