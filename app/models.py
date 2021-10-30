from typing import List
import os
from pydantic.main import BaseModel


class Column(BaseModel):
    key: str
    is_visible: bool
    is_grouped_by: bool


class View(BaseModel):
    name: str
    columns: List[Column]


# BLOBS (in Collections)

class Blob(BaseModel):
    bucket: str
    name: str
    path: str

    @property
    def id(self):
        return f"{self.bucket}/{self.path}"

    def __hash__(self):
        return hash(self.id)


class BlobsList(BaseModel):
    blobs: List[Blob]


class Table:

    def __init__(self, name: str, view: str = "default"):
        self.name = name
        self.view = view
        self.collections = []

    def import_outputs(self, bucket, prefix):
        pass

    def upload_collections(self):
        pass
