import os
from h5mapper import FileWalker
import re
from google.cloud import storage

storage_client = storage.Client("ax6-Project")
GCP_BUCKET = os.environ.get("GCP_BUCKET", "ax6-outputs")
bucket = storage_client.bucket(GCP_BUCKET)
AUDIOS_REGEX = re.compile(r"wav$|aif$|aiff$|mp3$|mp4$|m4a$", re.IGNORECASE)


if __name__ == '__main__':
    TARGET_PREFIX = "sounds/raw/wn-small-pol"

    to_upload = {f: os.path.join(TARGET_PREFIX, f.strip("./"))
                 for f in FileWalker(r"mp3|json", "./")}

    for i, (src, target) in enumerate(to_upload.items()):
        # if i < 1:
        print(f"{i} -- uploading {src} to {target}")
        bucket.blob(target).upload_from_filename(src)
