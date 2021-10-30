from setuptools import setup
import os

with open(os.path.join(os.path.dirname(__file__), 'requirements.txt'), "r", encoding="utf-8") as f:
    REQUIRES = [ln.strip() for ln in f.readlines() if ln.strip()]

setup(
    name='bucket-proxy',
    version='0.1.0',
    install_requires=REQUIRES,
    entry_points={
        'console_scripts': [
            'upload-outputs = upload_outputs:upload_outputs',
        ],
    },
)