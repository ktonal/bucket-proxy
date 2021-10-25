import os
from h5mapper import FileWalker
import re
from google.cloud import storage

storage_client = storage.Client("ax6-Project")
GCP_BUCKET = os.environ.get("GCP_BUCKET", "ax6-outputs")
bucket = storage_client.bucket(GCP_BUCKET)
AUDIOS_REGEX = re.compile(r"wav$|aif$|aiff$|mp3$|mp4$|m4a$", re.IGNORECASE)


if __name__ == '__main__':
    files = FileWalker(r"mp3|json", "./")
    TARGET_PREFIX = "sounds/raw/srnn-small-sig"

    to_upload = {f: os.path.join(TARGET_PREFIX, f.strip("./"))
                 for f in files}

    for i, (src, target) in enumerate(to_upload.items()):
        # if i < 1:
        print(f"{i} -- uploading {src} to {target}")
        bucket.blob(target).upload_from_filename(src)
