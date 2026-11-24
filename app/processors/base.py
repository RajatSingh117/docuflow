from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pathlib import Path


class BaseProcessor(ABC):
    """Abstract base class for all document format processors."""

    @abstractmethod
    def process(self, file_path: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process the document and return extracted raw text, structured tables, or records.
        Returns a dict:
        {
            "raw_text": str,
            "pages": List[Dict[str, Any]],
            "records": List[Dict[str, Any]],
            "metadata": Dict[str, Any]
        }
        """
        pass
