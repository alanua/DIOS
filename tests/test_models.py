import unittest

from dios.models import DataClass, QuantityRecord, SourceRef, VerificationStatus


class QuantityRecordTests(unittest.TestCase):
    def test_source_ref_requires_document_evidence(self) -> None:
        source = SourceRef(
            document_id=" ",
            revision="SYN-REV-A",
            sheet="SYN-A-100",
            page=1,
            evidence_reference="synthetic-zone:A1",
        )

        self.assertEqual(source.validate(), ["source.document_id is required"])

    def test_source_ref_rejects_invalid_page_evidence(self) -> None:
        source = SourceRef(
            document_id="synthetic-source-invalid-page",
            revision="SYN-REV-A",
            sheet="SYN-A-101",
            page=0,
            evidence_reference="synthetic-zone:B4",
        )

        self.assertEqual(source.validate(), ["source.page must be >= 1"])

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

    def test_confidence_accepts_closed_interval_boundaries(self) -> None:
        for confidence in (0.0, 1.0):
            with self.subTest(confidence=confidence):
                record = QuantityRecord(
                    item_id=f"SYN-CONFIDENCE-{confidence}",
                    description="Synthetic confidence boundary",
                    unit="m",
                    data_class=DataClass.EXPLICIT,
                    verification_status=VerificationStatus.NEEDS_REVIEW,
                    confidence=confidence,
                    source=SourceRef(document_id="synthetic-confidence-source"),
                )

                self.assertNotIn("confidence must be between 0 and 1", record.validate())

    def test_confidence_rejects_values_outside_closed_interval(self) -> None:
        for confidence in (-0.01, 1.01):
            with self.subTest(confidence=confidence):
                record = QuantityRecord(
                    item_id=f"SYN-CONFIDENCE-{confidence}",
                    description="Synthetic invalid confidence",
                    unit="m",
                    data_class=DataClass.EXPLICIT,
                    verification_status=VerificationStatus.NEEDS_REVIEW,
                    confidence=confidence,
                    source=SourceRef(document_id="synthetic-confidence-source"),
                )

                self.assertIn("confidence must be between 0 and 1", record.validate())

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

    def test_conflict_with_explanation_is_reviewable(self) -> None:
        record = QuantityRecord(
            item_id="SYN-CONFLICT-EXPLAINED-001",
            description="Synthetic opening count discrepancy",
            unit="pcs",
            data_class=DataClass.CALCULATED,
            verification_status=VerificationStatus.CONFLICT,
            source=SourceRef(document_id="synthetic-conflict-source", page=2),
            conflicts=["synthetic schedule count differs from plan count"],
        )

        self.assertNotIn("CONFLICT requires at least one conflict description", record.validate())

    def test_quantity_record_to_dict_retains_units_and_source_lineage(self) -> None:
        record = QuantityRecord(
            item_id="SYN-LINEAGE-001",
            description="Synthetic duct length",
            unit="ft",
            source_value="12 ft",
            normalized_si_value=3.6576,
            normalized_si_unit="m",
            data_class=DataClass.EXPLICIT,
            verification_status=VerificationStatus.NEEDS_REVIEW,
            confidence=0.8,
            source=SourceRef(
                document_id="synthetic-lineage-document",
                revision="SYN-REV-B",
                sheet="SYN-M-201",
                page=3,
                evidence_reference="synthetic-polyline:duct-7",
            ),
        )

        payload = record.to_dict()

        self.assertEqual(payload["unit"], "ft")
        self.assertEqual(payload["source_value"], "12 ft")
        self.assertEqual(payload["normalized_si_value"], 3.6576)
        self.assertEqual(payload["normalized_si_unit"], "m")
        self.assertEqual(
            payload["source"],
            {
                "document_id": "synthetic-lineage-document",
                "revision": "SYN-REV-B",
                "sheet": "SYN-M-201",
                "page": 3,
                "evidence_reference": "synthetic-polyline:duct-7",
            },
        )


if __name__ == "__main__":
    unittest.main()
