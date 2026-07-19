"""
Saves Streamlit UploadedFile objects to disk under uploads/<subfolder>/ and
returns the relative path to store in MySQL.
"""
import os
import uuid

UPLOAD_ROOT = os.getenv("UPLOAD_DIR", "uploads")


def save_upload(uploaded_file, subfolder: str) -> str:
    if uploaded_file is None:
        return None
    folder = os.path.join(UPLOAD_ROOT, subfolder)
    os.makedirs(folder, exist_ok=True)
    ext = os.path.splitext(uploaded_file.name)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(folder, filename)
    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path.replace("\\", "/")
