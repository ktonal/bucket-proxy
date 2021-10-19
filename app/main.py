import io
from typing import Optional, List, Dict
import os
import json
import re
from uuid import uuid4

from google.cloud import storage
from google.oauth2 import id_token
from google.auth.transport import requests

from fastapi import FastAPI, Depends, HTTPException, status, Header, File, UploadFile, Body
from starlette.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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


app = FastAPI(dependencies=[Depends(check_token)])
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


@app.get("/list/")
def list_all_blobs(
        prefix: Optional[str] = None, content_type: Optional[str] = None,
):
    return {"prefix": prefix,
            "blobs": [(blob.name, blob.content_type)
                      for blob in storage_client.list_blobs(bucket, prefix=prefix)
                      if content_type is None or content_type in blob.content_type]}


####################################################
#                TABLE ROUTES
####################################################

@app.get("/table/")
def discover_table():
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


@app.post("/table/")
def create_table(table_id: str = Body(...)):
    view_path = f"table/{table_id}/views/default.json"
    collections_path = f"table/{table_id}/collections"
    bucket.blob(view_path).upload_from_string(json.dumps(View()))
    bucket.blob(collections_path).upload_from_string('', content_type='application/x-www-form-urlencoded;charset=UTF-8')
    return "Ok"


@app.get("/table/{table_id}")
def get_table(table_id: str, view_name: Optional[str]):
    view_path = f"table/{table_id}/views/{'default' if view_name is None else view_name}.json"
    collections_path = f"table/{table_id}/collections"
    view = json.loads(bucket.blob(view_path).download_as_string())
    collections = [json.loads(bucket.blob(coll).download_as_string())
                   for coll in storage_client.list_blobs(bucket, prefix=collections_path)
                   if "json" in coll.content_type]
    return {"view": view, "collections": collections}


# Views

class Column(BaseModel):
    key: str
    is_visible: bool
    is_grouped_by: bool


class View(BaseModel):
    name: str
    columns: List[Column]


@app.get("/table/{table_id}/view")
def list_views(table_id: str):
    storage_path = f"table/{table_id}/views"
    return [{"id": blob.name, "data": json.loads(blob.download_as_string())}
            for blob in storage_client.list_blobs(bucket, prefix=storage_path)
            if "json" in blob.content_type]


@app.get("/table/{table_id}/view/{view_name}")
def get_view(table_id: str, view_name: str):
    storage_path = f"table/{table_id}/views/{view_name}.json"
    return json.loads(bucket.blob(storage_path).download_as_string())


@app.put("/table/{table_id}/view")
def put_view(table_id: str, view: View):
    storage_path = f"table/{table_id}/views/{view.name}.json"
    response = bucket.blob(storage_path).upload_from_string(view.json())
    return response


# COLLECTIONS

@app.get("/table/{table_id}/collections")
def get_collections(table_id: str):
    storage_path = f"table/{table_id}/collections"
    return [json.loads(blob.download_as_string())
            for blob in storage_client.list_blobs(bucket, prefix=storage_path)
            if "json" in blob.content_type]


@app.post("/table/{table_id}/collections")
def create_collection(table_id: str, collection: Dict[str, str]):
    collection_uuid = str(uuid4())
    storage_path = f"table/{table_id}/collections/{collection_uuid}.json"
    collection.setdefault("blobs", [])
    response = bucket.blob(storage_path).upload_from_string(json.dumps(collection))
    return response


@app.put("/table/{table_id}/collections/{collection_id}")
def edit_collection(table_id: str, collection_id: str, collection: Dict[str, str]):
    storage_path = f"table/{table_id}/collections/{collection_id}.json"
    response = bucket.blob(storage_path).upload_from_string(collection.json())
    return response


@app.get("/table/{table_id}/collections/{collection_id}")
def get_collection(table_id: str, collection_id: str):
    storage_path = f"table/{table_id}/collections/{collection_id}.json"
    return json.loads(bucket.blob(storage_path).download_from_string())


# BLOBS (in Collections)

class Blob(BaseModel):
    name: str
    url: str


@app.post("/table/{table_id}/collections/{collection_id}/blobs")
def add_blob(table_id: str, collection_id: str, blob: Blob):
    storage_path = f"table/{table_id}/collections/{collection_id}.json"
    collection = json.loads(bucket.blob(storage_path).download_as_string())
    collection["blobs"].append(blob.dict())
    response = bucket.blob(storage_path).upload_from_string(json.dumps(collection))
    return response


@app.put("/table/{table_id}/collections/{collection_id}/blobs")
def edit_blob(table_id: str, collection_id: str, blob: Blob):
    storage_path = f"table/{table_id}/collections/{collection_id}.json"
    collection = json.loads(bucket.blob(storage_path).download_as_string())
    if blob.url not in set([b["url"] for b in collection['blobs']]):
        collection["blobs"].append(blob.dict())
    else:
        collection["blobs"] = [b for b in collection["blobs"] if b["url"] != blob.url]
        collection["blobs"].append(blob)
    response = bucket.blob(storage_path).upload_from_string(json.dumps(collection))
    return response


@app.delete("/table/{table_id}/collections/{collection_id}/blobs/{url:path}")
def remove_blob_from_collection(
        table_id: str, collection_id: str, blob_url: str
):
    storage_path = f"table/{table_id}/collections/{collection_id}.json"
    collection = json.loads(bucket.blob(storage_path).download_as_string())
    collection["blobs"] = [b for b in collection["blobs"] if b["url"] != blob_url]
    response = bucket.blob(storage_path).upload_from_string(json.dumps(collection))
    return response


####################################################
#                BLOB ROUTES
####################################################

@app.post("/bytes/{blob_path:path}")
def create_blob(blob_path: str, file: UploadFile = File(...)):
    response = bucket.blob(blob_path).upload_from_bytes(file.read())
    return response


@app.get("/bytes/{blob_path:path}")
def stream_bytes(blob_path: str):
    blob = bucket.blob(blob_path)
    raw = blob.download_as_bytes()
    return StreamingResponse(io.BytesIO(raw), media_type=blob.content_type)


@app.delete("/blob/{blob_path:path}")
def delete_blob(blob_path: str):
    return bucket.blob(blob_path).delete()
