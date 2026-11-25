"""Versioned upload/crop conventions, separate from all accepted feature specs."""
from pathlib import Path
import os

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'app/runtime/uploads'
QA_EVIDENCE=Path(os.environ.get('PORTRAIT_EVIDENCE',str(ROOT/'app/evidence/external_v1'))).resolve()
PREPROCESSING='EXIF_TRANSPOSE_RGB_INTEGER_SQUARE_PIL_BICUBIC256_v1'
MAX_UPLOAD_BYTES=10*1024*1024
MAX_PIXELS=16_000_000
MAX_SIDE=8192
MAX_SESSIONS=8
TTL_SECONDS=30*60
WORKER_TIMEOUT=180
FORMATS={'PNG':'image/png','JPEG':'image/jpeg','WEBP':'image/webp'}
MODEL_SHA256='64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff'
