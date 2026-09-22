from abc import ABC, abstractmethod
from typing import BinaryIO, Optional
import os
import shutil
from fastapi import UploadFile

class StorageProvider(ABC):
    @abstractmethod
    def save(self, file: UploadFile, safe_filename: str) -> str:
        pass

    @abstractmethod
    def get_path(self, safe_filename: str) -> Optional[str]:
        pass

    @abstractmethod
    def delete(self, safe_filename: str) -> bool:
        pass

    @abstractmethod
    def exists(self, safe_filename: str) -> bool:
        pass


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: str):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_safe_path(self, safe_filename: str) -> str:
        # Prevent path traversal
        clean_name = os.path.basename(safe_filename)
        path = os.path.abspath(os.path.join(self.base_dir, clean_name))
        if os.path.commonpath([path, self.base_dir]) != self.base_dir:
            raise ValueError("Path traversal attempt detected.")
        return path

    def save(self, file: UploadFile, safe_filename: str) -> str:
        filepath = self._get_safe_path(safe_filename)
        file.file.seek(0)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return filepath

    def get_path(self, safe_filename: str) -> Optional[str]:
        try:
            filepath = self._get_safe_path(safe_filename)
            if os.path.isfile(filepath):
                return filepath
        except ValueError:
            pass
        return None

    def delete(self, safe_filename: str) -> bool:
        try:
            filepath = self._get_safe_path(safe_filename)
            if os.path.isfile(filepath):
                os.remove(filepath)
                return True
        except ValueError:
            pass
        return False

    def exists(self, safe_filename: str) -> bool:
        try:
            filepath = self._get_safe_path(safe_filename)
            return os.path.isfile(filepath)
        except ValueError:
            return False
