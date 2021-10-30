import os
import json
import re
from google.cloud import storage

MAPPING = {
    "network_class": "network_type",
    "network/feature": "input_type",
}

VALUES_TRANSFORMS = {
    "files": lambda files: f"Verdi_X_{os.path.split(files[0])[-1].split('_')[2]}"
}

storage_client = storage.Client("ax6-Project")
GCP_BUCKET = os.environ.get("GCP_BUCKET", "axx-data")
AUDIOS_REGEX = re.compile(r"wav$|aif$|aiff$|mp3$|mp4$|m4a$", re.IGNORECASE)


def flatten_dict(dd, separator='/', prefix=''):
    return {prefix + separator + k if prefix else k: v
            for kk, vv in dd.items()
            for k, v in flatten_dict(vv, separator, kk).items()
            } if isinstance(dd, dict) else {prefix: dd}


def list_audio_blobs(bucket, dirname):
    return [
        {"bucket": bucket, "path": sub_blob.name, "name": os.path.split(sub_blob.name)[-1]}
        for sub_blob in storage_client.list_blobs(storage_client.bucket(bucket), prefix=dirname)
        if "audio" in sub_blob.content_type or re.search(AUDIOS_REGEX, os.path.splitext(sub_blob.name)[1])
    ]


if __name__ == '__main__':
    SRC_BUCKET = "ax6-outputs"
    SRC_PREFIX = "sounds/raw/srnn-verdi-x"
    TRG_NAME = "verdiX"

    src_bucket = storage_client.bucket(SRC_BUCKET)
    # each json in the bucket is a row
    table = {}
    for blob in storage_client.list_blobs(src_bucket, prefix=SRC_PREFIX):
        if "text" not in blob.content_type:
            dirname = os.path.dirname(blob.name)
            if blob.content_type == "application/json":
                data = json.loads(blob.download_as_string())
                table.setdefault(data["id"], {}).update(flatten_dict(data))
                # apply key mapping
                for old_k, new_k in MAPPING.items():
                    table[data['id']][new_k] = table[data['id']][old_k]
                    table[data['id']].pop(old_k)
                # apply values transform
                for key, transform in VALUES_TRANSFORMS.items():
                    table[data['id']][key] = transform(table[data['id']][key])
                table.setdefault(data["id"], {}).setdefault("blobs", list_audio_blobs(SRC_BUCKET, dirname))

    trg_bucket = storage_client.bucket("axx-data")

    # print(table)

    # trg_bucket.blob(f"tables/{TRG_NAME}/").upload_from_string('', content_type='application/x-www-form-urlencoded;charset=UTF-8')

    for id, data in table.items():
        trg_bucket.blob(f"tables/{TRG_NAME}/collections/{id}.json").upload_from_string(json.dumps(data),
                                                                                       content_type="application/json")

    # trg_bucket.blob(f"tables/{TRG_NAME}/views/default.json").upload_from_string(
    #     json.dumps([{"key": k, "visible": True, "grouped": True} for k in ["files"]] +
    #                [{"key": k, "visible": True, "grouped": False} for k in ["network_type", "input_type", "id"]])
    # )
