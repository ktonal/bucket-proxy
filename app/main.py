import io
from typing import Optional
import os
import json
import secrets
from fastapi import FastAPI, Depends, HTTPException, status, Header
from google.cloud import storage
from starlette.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

storage_client = storage.Client("ax6-Project")
GCP_BUCKET = os.environ.get("GCP_BUCKET", "ax6-train-data")
bucket = storage_client.bucket(GCP_BUCKET)


def check_token(authorization: str = Header(...)):
    correct_password = secrets.compare_digest(authorization, "Bearer " + os.environ.get("APP_SECRET", ""))
    if not correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return correct_password


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


@app.get("/table/")
def get_table():
    # each json in the bucket is a row
    table = {}
    for blob in storage_client.list_blobs(bucket):
        if "text" not in blob.content_type:
            dirname = os.path.dirname(blob.name)
            if blob.content_type == "application/json":
                table.setdefault(dirname, {}).setdefault("json", json.loads(blob.download_as_string()))
            elif "audio" in blob.content_type:
                table.setdefault(dirname, {}).setdefault("audios", []).append(blob.name)
    return table


@app.get("/bytes/{blob_path:path}")
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
