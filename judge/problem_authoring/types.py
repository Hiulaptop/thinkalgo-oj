from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class AuthoringContext:
    user_id: int
    organization_id: Optional[int] = None


@dataclass(frozen=True)
class CaseSpec:
    input_file: str
    output_file: str
    order: int
    points: Decimal = Decimal('1')
    is_pretest: bool = False


@dataclass(frozen=True)
class PackageManifest:
    kind: str
    fields: dict
    tests: list[CaseSpec]
    source_name: Optional[str]
    warnings: list[str]
    sha256: str
    compressed_bytes: int
    expanded_bytes: int


@dataclass(frozen=True)
class DraftChanges:
    problem_fields: dict = field(default_factory=dict)
    solution_fields: Optional[dict] = None
    test_upload_id: Optional[UUID] = None
    cases: Optional[list[CaseSpec]] = None
    data_fields: dict = field(default_factory=dict)
    language_limits: Optional[list[dict]] = None
    pdf_upload_id: Optional[UUID] = None
    reference_upload_id: Optional[UUID] = None
    reference_language_id: Optional[int] = None
    replace_sections: frozenset[str] = frozenset()


@dataclass(frozen=True)
class SaveResult:
    problem_id: int
    revision: int
    operation_id: Optional[UUID] = None


class AuthoringError(Exception):
    def __init__(self, code: str, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field


class ConflictError(AuthoringError):
    pass
