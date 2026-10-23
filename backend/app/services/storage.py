import uuid
from pathlib import Path

from werkzeug.utils import secure_filename
from flask import current_app


ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "txt"}

FILE_SIGNATURES = {
    "pdf": b"%PDF-",
    "png": b"\x89PNG\r\n\x1a\n",
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
}


def save_private_file(uploaded_file):

    if not uploaded_file or not uploaded_file.filename:
        raise ValueError("No file selected")

    safe_name = secure_filename(uploaded_file.filename)

    if not safe_name or "." not in safe_name:
        raise ValueError("Invalid filename")

    extension = safe_name.rsplit(".", 1)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("File type not allowed")

    # Read the actual uploaded bytes.
    uploaded_file.stream.seek(0)
    file_bytes = uploaded_file.stream.read()
    uploaded_file.stream.seek(0)

    if not file_bytes:
        raise ValueError("Uploaded file is empty")

    # Validate file content.
    if extension in FILE_SIGNATURES:
        signature = FILE_SIGNATURES[extension]

        if not file_bytes.startswith(signature):
            raise ValueError("File content does not match its extension")

    elif b"\x00" in file_bytes[:1024]:
        raise ValueError("Invalid text file")

    storage_key = uuid.uuid4().hex

    storage_dir = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    storage_dir.mkdir(parents=True, exist_ok=True)

    file_path = storage_dir / storage_key

    # Write bytes directly to private storage.
    file_path.write_bytes(file_bytes)

    if file_path.stat().st_size != len(file_bytes):
        file_path.unlink(missing_ok=True)
        raise RuntimeError("File storage verification failed")

    return storage_key, safe_name


def get_private_file_path(storage_key):

    if not storage_key or not storage_key.isalnum():
        return None

    storage_dir = Path(current_app.config["UPLOAD_FOLDER"]).resolve()

    file_path = (storage_dir / storage_key).resolve()

    if file_path.parent != storage_dir:
        return None

    return file_path