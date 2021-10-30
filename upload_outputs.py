import os
import click

from h5mapper import FileWalker
from google.cloud import storage

storage_client = storage.Client("ax6-Project")


@click.command()
@click.option("-r", "--root", default="./", help="root to upload from")
@click.option("-b", "--bucket", default="ax6-outputs", help="bucket to upload to")
@click.option("-p", "--prefix", default="", help="prefix to upload to")
def upload_outputs(root: str = "./", bucket: str = 'ax6-outputs', prefix: str = ""):
    print(root, bucket, prefix)
    files = FileWalker(r"mp3|json", root)
    bucket = storage_client.bucket(bucket)
    to_upload = {f: os.path.join("sounds/raw", prefix, f.strip("./"))
                 for f in files}

    for i, (src, target) in enumerate(to_upload.items()):
        # if i < 1:
        print(f"{i} -- uploading {src} to {target}")
        bucket.blob(target).upload_from_filename(src)


if __name__ == '__main__':
    upload_outputs()
