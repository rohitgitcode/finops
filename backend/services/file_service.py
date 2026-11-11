import os
import shutil
import tempfile
from fastapi import UploadFile, HTTPException, status

def save_temp_file(file: UploadFile) -> tuple[str, str]:
    """
    Validates PDF format, creates an isolated temporary directory,
    and streams the incoming UploadFile to disk.

    Returns:
        tuple[str, str]: (temp_file_path, temp_dir)
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF documents are supported."
        )

    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, file.filename)

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return temp_file_path, temp_dir
    except Exception as exc:
        cleanup_temp_dir(temp_dir)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to buffer uploaded file: {str(exc)}"
        )

def cleanup_temp_dir(temp_dir: str) -> None:
    """
    Safely removes the temporary directory and all buffered files.
    """
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)

