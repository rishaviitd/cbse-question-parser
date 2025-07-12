import os
import tempfile
import shutil
from typing import Optional, BinaryIO, Union
from fastapi import UploadFile, HTTPException
import hashlib
import mimetypes
from pathlib import Path

def validate_pdf_file(file: UploadFile) -> bool:
    """
    Validate that the uploaded file is a PDF.
    
    Args:
        file: FastAPI UploadFile object
        
    Returns:
        bool: True if valid PDF, False otherwise
    """
    # Check file extension
    if not file.filename.lower().endswith('.pdf'):
        return False
    
    # Check MIME type if available
    if file.content_type and file.content_type != 'application/pdf':
        return False
    
    return True

def get_file_size(file: Union[UploadFile, BinaryIO]) -> int:
    """
    Get the size of an uploaded file.
    
    Args:
        file: File object
        
    Returns:
        int: File size in bytes
    """
    if hasattr(file, 'size'):
        return file.size
    
    # For UploadFile, we need to read and calculate
    if hasattr(file, 'file'):
        current_pos = file.file.tell()
        file.file.seek(0, 2)  # Seek to end
        size = file.file.tell()
        file.file.seek(current_pos)  # Restore position
        return size
    
    return 0

def generate_file_hash(file_content: bytes) -> str:
    """
    Generate MD5 hash of file content.
    
    Args:
        file_content: File content as bytes
        
    Returns:
        str: MD5 hash hex string
    """
    return hashlib.md5(file_content).hexdigest()

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing dangerous characters.
    
    Args:
        filename: Original filename
        
    Returns:
        str: Sanitized filename
    """
    # Remove or replace dangerous characters
    dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    sanitized = filename
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Limit length
    if len(sanitized) > 100:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:100-len(ext)] + ext
    
    return sanitized

def create_temp_file(content: bytes, suffix: str = '.pdf') -> str:
    """
    Create a temporary file with given content.
    
    Args:
        content: File content as bytes
        suffix: File suffix/extension
        
    Returns:
        str: Path to temporary file
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_file.write(content)
    temp_file.close()
    return temp_file.name

def ensure_directory_exists(directory: str) -> None:
    """
    Ensure a directory exists, create if it doesn't.
    
    Args:
        directory: Directory path
    """
    os.makedirs(directory, exist_ok=True)

def clean_temp_file(filepath: str) -> None:
    """
    Clean up a temporary file.
    
    Args:
        filepath: Path to file to delete
    """
    try:
        if os.path.exists(filepath):
            os.unlink(filepath)
    except Exception:
        pass

def get_file_info(filepath: str) -> dict:
    """
    Get information about a file.
    
    Args:
        filepath: Path to file
        
    Returns:
        dict: File information
    """
    if not os.path.exists(filepath):
        return {}
    
    stat = os.stat(filepath)
    mime_type, _ = mimetypes.guess_type(filepath)
    
    return {
        'path': filepath,
        'name': os.path.basename(filepath),
        'size': stat.st_size,
        'modified': stat.st_mtime,
        'mime_type': mime_type or 'application/octet-stream'
    }

def list_files_in_directory(directory: str, extension: Optional[str] = None) -> list:
    """
    List files in a directory, optionally filtered by extension.
    
    Args:
        directory: Directory path
        extension: Optional file extension filter (e.g., '.pdf')
        
    Returns:
        list: List of file paths
    """
    if not os.path.exists(directory):
        return []
    
    files = []
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isfile(item_path):
            if extension is None or item.lower().endswith(extension.lower()):
                files.append(item_path)
    
    return sorted(files)

def get_latest_files(directory: str, count: int = 5) -> list:
    """
    Get the latest files in a directory by modification time.
    
    Args:
        directory: Directory path
        count: Number of latest files to return
        
    Returns:
        list: List of latest file paths
    """
    if not os.path.exists(directory):
        return []
    
    files = []
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isfile(item_path):
            files.append((item_path, os.path.getmtime(item_path)))
    
    # Sort by modification time (newest first)
    files.sort(key=lambda x: x[1], reverse=True)
    
    return [f[0] for f in files[:count]]

class MockUploadFile:
    """
    Mock UploadFile class for compatibility with existing functions.
    """
    def __init__(self, file_content: bytes, filename: str):
        self.file_content = file_content
        self.filename = filename
        self.name = filename
        self.size = len(file_content)
        self.content_type = 'application/pdf'
    
    def getvalue(self) -> bytes:
        return self.file_content
    
    async def read(self) -> bytes:
        return self.file_content

def create_mock_file(content: bytes, filename: str) -> MockUploadFile:
    """
    Create a mock upload file for testing or processing.
    
    Args:
        content: File content as bytes
        filename: Filename
        
    Returns:
        MockUploadFile: Mock file object
    """
    return MockUploadFile(content, filename)

def validate_file_size(file: UploadFile, max_size_mb: int = 50) -> bool:
    """
    Validate file size is within limits.
    
    Args:
        file: UploadFile object
        max_size_mb: Maximum size in MB
        
    Returns:
        bool: True if within limits
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    file_size = get_file_size(file)
    return file_size <= max_size_bytes

def get_storage_info() -> dict:
    """
    Get storage information for the logs directory.
    
    Returns:
        dict: Storage information
    """
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        return {'exists': False}
    
    total_size = 0
    file_count = 0
    
    for root, dirs, files in os.walk(logs_dir):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                total_size += os.path.getsize(file_path)
                file_count += 1
            except OSError:
                pass
    
    return {
        'exists': True,
        'total_size_bytes': total_size,
        'total_size_mb': total_size / (1024 * 1024),
        'file_count': file_count,
        'directory': logs_dir
    } 