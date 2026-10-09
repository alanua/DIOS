import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dios.models import DataClass, QuantityRecord, SourceRef, VerificationStatus


class QuantityRecordTests(unittest.TestCase):
    def test_valid_explicit_record(self) -> None:
        record = QuantityRecord(
            item_id="ARCH-ROOM-001",
            description="Synthetic room floor area",
            unit="m2",
            source_value=12.5,
            normalized_si_value=12.5,
            normalized_si_unit="m2",
            measurement_method="CLOSED_POLYGON_AREA",
            data_class=DataClass.CALCULATED,
            verification_status=VerificationStatus.NEEDS_REVIEW,
            confidence=0.95,
            source=SourceRef(
                document_id="synthetic-plan",
                revision="A",
                sheet="A-101",
                page=1,
                evidence_reference="zone:B2",
            ),
        )
        self.assertEqual(record.validate(), [])

    def test_inferred_record_cannot_be_verified(self) -> None:
        record = QuantityRecord(
            item_id="ARCH-WALL-001",
            description="Synthetic wall height",
            unit="m",
            data_class=DataClass.INFERRED,
            verification_status=VerificationStatus.VERIFIED,
            source=SourceRef(document_id="synthetic-section"),
        )
        self.assertIn("inferred data cannot be VERIFIED without an explicit review record", record.validate())

    def test_inferred_quantity_with_calculation_details_still_cannot_auto_verify(self) -> None:
        record = QuantityRecord(
            item_id="MEP-DUCT-001",
            description="Synthetic inferred duct route length",
            unit="m",
            source_value="12.0",
            normalized_si_value=12.0,
            normalized_si_unit="m",
            formula="synthetic centerline allowance",
            measurement_method="INFERRED_ROUTE_ALLOWANCE",
            data_class=DataClass.INFERRED,
            verification_status=VerificationStatus.VERIFIED,
            confidence=0.8,
            assumptions=["Synthetic route not explicitly dimensioned"],
            source=SourceRef(
                document_id="synthetic-mechanical-plan",
                revision="B",
                sheet="M-201",
                page=2,
                evidence_reference="zone:C4",
            ),
        )
        self.assertEqual(
            record.validate(),
            ["inferred data cannot be VERIFIED without an explicit review record"],
        )

    def test_invalid_source_page_and_confidence_fail_closed(self) -> None:
        record = QuantityRecord(
            item_id="ARCH-BAD-001",
            description="Synthetic invalid record",
            unit="m",
            data_class=DataClass.CALCULATED,
            verification_status=VerificationStatus.NEEDS_REVIEW,
            confidence=1.5,
            source=SourceRef(document_id=" ", page=0),
        )
        errors = record.validate()
        self.assertIn("source.document_id is required", errors)
        self.assertIn("source.page must be >= 1", errors)
        self.assertIn("confidence must be between 0 and 1", errors)

    def test_conflict_requires_description(self) -> None:
        record = QuantityRecord(
            item_id="ARCH-OPENING-001",
            description="Synthetic opening",
            unit="pcs",
            data_class=DataClass.EXPLICIT,
            verification_status=VerificationStatus.CONFLICT,
            source=SourceRef(document_id="synthetic-plan"),
        )
        self.assertIn("CONFLICT requires at least one conflict description", record.validate())

    def test_conflict_with_bad_provenance_and_unit_reports_each_supported_error(self) -> None:
        record = QuantityRecord(
            item_id="ARCH-OPENING-002",
            description="Synthetic opening conflict",
            unit=" ",
            data_class=DataClass.EXPLICIT,
            verification_status=VerificationStatus.CONFLICT,
            source=SourceRef(document_id=" ", page=-3),
        )
        errors = record.validate()
        self.assertIn("source.document_id is required", errors)
        self.assertIn("source.page must be >= 1", errors)
        self.assertIn("unit is required", errors)
        self.assertIn("CONFLICT requires at least one conflict description", errors)

    def test_bad_numeric_confidence_values_fail_closed(self) -> None:
        for confidence in (-0.01, 1.01):
            with self.subTest(confidence=confidence):
                record = QuantityRecord(
                    item_id="QTY-NUMERIC-001",
                    description="Synthetic numeric bounds check",
                    unit="pcs",
                    data_class=DataClass.CALCULATED,
                    verification_status=VerificationStatus.NEEDS_REVIEW,
                    confidence=confidence,
                    source=SourceRef(document_id="synthetic-schedule"),
                )
                self.assertIn("confidence must be between 0 and 1", record.validate())


if __name__ == "__main__":
    unittest.main()
