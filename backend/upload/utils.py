"""文件上传验证工具"""

from pathlib import Path

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic"}
MAX_FILE_SIZE = 100 * 1024 * 1024


def validate_file_extension(filename: str) -> bool:
    """验证文件扩展名是否允许"""
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def validate_file_size(size: int, max_size: int = MAX_FILE_SIZE) -> bool:
    """验证文件大小是否在限制内"""
    return size <= max_size
