import unittest

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


if __name__ == "__main__":
    unittest.main()
