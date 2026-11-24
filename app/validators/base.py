from abc import ABC, abstractmethod
from typing import Dict, Any, List
from app.models.extraction import ValidationStatus


class BaseValidator(ABC):
    """Base interface for validation rules."""

    @abstractmethod
    def validate(self, fields: Dict[str, Any], context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Validates extracted fields dictionary.
        Returns a list of validation outcomes:
        [
            {
                "field_name": str,
                "rule": str,
                "status": ValidationStatus,
                "message": str
            }
        ]
        """
        pass
