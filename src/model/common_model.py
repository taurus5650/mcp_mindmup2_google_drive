from dataclasses import dataclass
from typing import Optional, Any


@dataclass
class OperationResult:

    is_success: bool
    detail: Optional[Any] = None
    error: Optional[str] = None

    @classmethod
    def success(cls, detail: Any = None) -> 'OperationResult':
        return cls(is_success=True, detail=detail)

    @classmethod
    def fail(cls, detail: Any = None) -> 'OperationResult':
        return cls(is_success=False, detail=detail)
