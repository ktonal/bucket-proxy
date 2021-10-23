import io
from typing import Optional, List, Dict, AnyStr, Any
import os
import json
from uuid import uuid4

from google.cloud import storage
from google.oauth2 import id_token
from google.auth.transport import requests

from fastapi import FastAPI, Depends, HTTPException, status, Header, File, UploadFile, Body
from starlette.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

storage_client = storage.Client("ax6-Project")
GCP_BUCKET = os.environ.get("GCP_BUCKET", "axx-data")
bucket = storage_client.bucket(GCP_BUCKET)


def check_token(authorization: Optional[str] = Header(None)):
    try:
        user_id_token = authorization.split(" ")[-1]
        # Specify the CLIENT_ID of the app that accesses the backend:
        idinfo = id_token.verify_oauth2_token(user_id_token, requests.Request(),
                                              "955131018414-f46kce80kqakmpofouoief34050ni8e0.apps.googleusercontent.com")

        # ID token is valid. Get the user's Google Account ID from the decoded token.
        user_id = idinfo['sub']
        return user_id
    except (ValueError, AttributeError) as e:
        print(e)
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
def list_tables():
    storage_path = "tables/"
    tables = storage_client.list_blobs(bucket, prefix=storage_path, delimiter='/',
                                       include_trailing_delimiter=True)
    resp = [os.path.split(os.path.dirname(table.name))[1]
            for table in tables if table.name != storage_path]
    return resp


@app.post("/table/")
def create_table(table_id: str = Body(...)):
    view_path = f"tables/{table_id}/views/default.json"
    collections_path = f"table/{table_id}/collections"
    bucket.blob(view_path).upload_from_string(json.dumps(View()))
    bucket.blob(collections_path).upload_from_string('', content_type='application/x-www-form-urlencoded;charset=UTF-8')
    return "Ok"


@app.get("/table/{table_id}")
def get_table(table_id: str, view_name: Optional[str] = "default"):
    view_path = f"tables/{table_id}/views/{view_name}.json"
    collections_path = f"tables/{table_id}/collections"
    view = json.loads(bucket.blob(view_path).download_as_string())
    collections = [json.loads(bucket.blob(coll.name).download_as_string())
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
    storage_path = f"tables/{table_id}/views"
    return [{"id": blob.name, "data": json.loads(blob.download_as_string())}
            for blob in storage_client.list_blobs(bucket, prefix=storage_path)
            if "json" in blob.content_type]


@app.get("/table/{table_id}/view/{view_name}")
def get_view(table_id: str, view_name: str):
    storage_path = f"tables/{table_id}/views/{view_name}.json"
    return json.loads(bucket.blob(storage_path).download_as_string())


@app.put("/table/{table_id}/view")
def put_view(table_id: str, view: View):
    storage_path = f"table/{table_id}/views/{view.name}.json"
    response = bucket.blob(storage_path).upload_from_string(view.json())
    return response


# COLLECTIONS

class Collection(BaseModel):
    __root__: Dict[str, Any]

    class Config:
        arbitrary_types_allowed = True


class CollectionRequest(BaseModel):
    collection: Collection


@app.get("/table/{table_id}/collections")
def get_collections(table_id: str):
    storage_path = f"tables/{table_id}/collections"
    return [json.loads(blob.download_as_string())
            for blob in storage_client.list_blobs(bucket, prefix=storage_path)
            if "json" in blob.content_type]


@app.post("/table/{table_id}/collections")
def create_collection(table_id: str, collection: Dict[str, Any] = Body(...)):
    collection_uuid = str(uuid4())
    storage_path = f"tables/{table_id}/collections/{collection_uuid}.json"
    collection.setdefault("id", collection_uuid)
    collection.setdefault("blobs", [])
    bucket.blob(storage_path).upload_from_string(json.dumps(collection),
                                                 content_type="application/json")
    return collection


@app.put("/table/{table_id}/collections/{collection_id}")
def edit_collection(table_id: str, collection_id: str, collection: Dict[str, Any] = Body(...)):
    storage_path = f"tables/{table_id}/collections/{collection_id}.json"
    response = bucket.blob(storage_path).upload_from_string(json.dumps(collection),
                                                            content_type="application/json")
    return response


@app.get("/table/{table_id}/collections/{collection_id}")
def get_collection(table_id: str, collection_id: str):
    storage_path = f"tables/{table_id}/collections/{collection_id}.json"
    return json.loads(bucket.blob(storage_path).download_from_string())


@app.delete("/table/{table_id}/collections/{collection_id}")
def delete_collection(table_id: str, collection_id: str):
    storage_path = f"tables/{table_id}/collections/{collection_id}.json"


# BLOBS (in Collections)

class Blob(BaseModel):
    bucket: str
    name: str
    path: str

    @property
    def id(self):
        return f"{self.bucket}/{self.path}"


@app.post("/table/{table_id}/collections/{collection_id}/blobs")
def add_blob(table_id: str, collection_id: str, blob: Blob):
    storage_path = f"tables/{table_id}/collections/{collection_id}.json"
    collection = json.loads(bucket.blob(storage_path).download_as_string())
    collection["blobs"].append(blob.dict())
    bucket.blob(storage_path).upload_from_string(json.dumps(collection),
                                                 content_type="application/json")
    return blob.dict()


@app.put("/table/{table_id}/collections/{collection_id}/blobs")
def edit_blob(table_id: str, collection_id: str, blob: Blob):
    storage_path = f"tables/{table_id}/collections/{collection_id}.json"
    collection = json.loads(bucket.blob(storage_path).download_as_string())
    if blob.id not in set([b.id for b in collection['blobs']]):
        collection["blobs"].append(blob.dict())
    else:
        collection["blobs"] = [b for b in collection["blobs"] if b.id != blob.id]
        collection["blobs"].append(blob)
    response = bucket.blob(storage_path).upload_from_string(json.dumps(collection),
                                                            content_type="application/json")
    return response


@app.delete("/table/{table_id}/collections/{collection_id}/blobs")
def remove_blob_from_collection(
        table_id: str, collection_id: str, blob: Blob
):
    storage_path = f"tables/{table_id}/collections/{collection_id}.json"
    collection = json.loads(bucket.blob(storage_path).download_as_string())
    collection["blobs"] = [b for b in collection["blobs"] if Blob(**b).id != blob.id]
    response = bucket.blob(storage_path).upload_from_string(json.dumps(collection))
    return response


####################################################
#                BLOB ROUTES
####################################################

# because blobs are allowed to be outside of the apps data
# we instantiate a bucket if need be

def get_bucket(path):
    prefix = next(part for part in path.split('/') if part)
    if prefix != GCP_BUCKET:
        return storage_client.bucket(prefix)
    return bucket


@app.post("/bytes/{blob_path:path}")
def create_blob(
        blob_path: str,
        bucket: Optional[str] = "",
        file: UploadFile = File(...)):
    if not blob_path:
        blob_path = "blobs/"
    if not bucket:
        bucket = GCP_BUCKET
    blob_path += file.filename
    blob = storage_client.bucket(bucket).blob(blob_path)
    # TODO: convert (.wav, .aiff, .aif, ...) to .mp3
    blob.upload_from_string(file.file.read(),
                            content_type="audio/"+os.path.splitext(file.filename)[1].strip("."))
    return {"bucket": bucket, "path": blob_path, "name": file.filename}


@app.get("/bytes/{blob_path:path}")
def stream_bytes(blob_path: str, bucket: Optional[str] = ''):
    if not bucket:
        bucket = GCP_BUCKET
    blob = storage_client.bucket(bucket).blob(blob_path)
    raw = blob.download_as_bytes()
    return StreamingResponse(io.BytesIO(raw), media_type=blob.content_type)


@app.delete("/blob/{blob_path:path}")
def delete_blob(blob_path: str):
    return get_bucket(blob_path).blob(blob_path).delete()
