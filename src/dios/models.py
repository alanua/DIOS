from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class DataClass(StrEnum):
    EXPLICIT = "EXPLICIT"
    CALCULATED = "CALCULATED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    CONFLICT = "CONFLICT"
    NOT_FOUND = "NOT_FOUND"


@dataclass(frozen=True)
class SourceRef:
    document_id: str
    revision: str | None = None
    sheet: str | None = None
    page: int | None = None
    evidence_reference: str | None = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.document_id.strip():
            errors.append("source.document_id is required")
        if self.page is not None and self.page < 1:
            errors.append("source.page must be >= 1")
        return errors


@dataclass
class QuantityRecord:
    item_id: str
    description: str
    unit: str
    data_class: DataClass
    verification_status: VerificationStatus
    source: SourceRef
    source_value: float | int | str | None = None
    normalized_si_value: float | int | None = None
    normalized_si_unit: str | None = None
    formula: str | None = None
    measurement_method: str | None = None
    discipline: str | None = None
    system: str | None = None
    location: str | None = None
    confidence: float | None = None
    assumptions: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    notes: str | None = None

    def validate(self) -> list[str]:
        errors = self.source.validate()
        if not self.item_id.strip():
            errors.append("item_id is required")
        if not self.description.strip():
            errors.append("description is required")
        if not self.unit.strip():
            errors.append("unit is required")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            errors.append("confidence must be between 0 and 1")
        if self.data_class is DataClass.INFERRED and self.verification_status is VerificationStatus.VERIFIED:
            errors.append("inferred data cannot be VERIFIED without an explicit review record")
        if self.verification_status is VerificationStatus.CONFLICT and not self.conflicts:
            errors.append("CONFLICT requires at least one conflict description")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "discipline": self.discipline,
            "system": self.system,
            "location": self.location,
            "description": self.description,
            "unit": self.unit,
            "source_value": self.source_value,
            "normalized_si_value": self.normalized_si_value,
            "normalized_si_unit": self.normalized_si_unit,
            "formula": self.formula,
            "measurement_method": self.measurement_method,
            "data_class": self.data_class.value,
            "confidence": self.confidence,
            "verification_status": self.verification_status.value,
            "source": {
                "document_id": self.source.document_id,
                "revision": self.source.revision,
                "sheet": self.source.sheet,
                "page": self.source.page,
                "evidence_reference": self.source.evidence_reference,
            },
            "assumptions": self.assumptions,
            "conflicts": self.conflicts,
            "notes": self.notes,
        }
