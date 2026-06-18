import os
import shutil
import hashlib
import logging
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class FileManager:
    """File system utilities."""

    @staticmethod
    def ensure_dir(path: str) -> Path:
        """Ensure directory exists, create if not."""
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @staticmethod
    def get_temp_file(suffix: str = ".wav", prefix: str = "audio_") -> str:
        """Create a temporary file and return its path."""
        FileManager.ensure_dir("./temp")
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir="./temp")
        os.close(fd)
        return path

    @staticmethod
    def safe_delete(path: str) -> bool:
        """Safely delete a file."""
        try:
            if os.path.exists(path):
                os.remove(path)
                return True
        except Exception as e:
            logger.warning(f"Could not delete {path}: {e}")
        return False

    @staticmethod
    def get_file_hash(path: str) -> Optional[str]:
        """Get MD5 hash of a file."""
        try:
            md5 = hashlib.md5()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    md5.update(chunk)
            return md5.hexdigest()
        except Exception as e:
            logger.error(f"Error hashing file {path}: {e}")
            return None

    @staticmethod
    def get_file_size_mb(path: str) -> float:
        """Get file size in MB."""
        try:
            return os.path.getsize(path) / (1024 * 1024)
        except Exception:
            return 0.0

    @staticmethod
    def cleanup_temp_files(max_age_hours: int = 24) -> int:
        """Clean up old temporary files."""
        cleaned = 0
        temp_dir = Path("./temp")
        if not temp_dir.exists():
            return 0
        cutoff = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        for file in temp_dir.iterdir():
            if file.is_file() and file.stat().st_mtime < cutoff:
                try:
                    file.unlink()
                    cleaned += 1
                except Exception as e:
                    logger.warning(f"Could not clean {file}: {e}")
        return cleaned

    @staticmethod
    def export_to_file(content: str, filename: str, export_dir: str = "./exports") -> str:
        """Write export content to file and return path."""
        FileManager.ensure_dir(export_dir)
        path = os.path.join(export_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Exported to {path}")
        return path
