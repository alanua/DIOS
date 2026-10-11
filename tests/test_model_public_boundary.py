import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dios.models import DataClass, QuantityRecord, SourceRef, VerificationStatus


class QuantityRecordPublicBoundaryTests(unittest.TestCase):
    def test_review_and_conflict_evidence_remain_distinct_from_verified(self) -> None:
        review_record = QuantityRecord(
            item_id="SYN-ROOM-AREA-001",
            description="Synthetic room area requiring review",
            unit="m2",
            source_value=24.0,
            normalized_si_value=24.0,
            normalized_si_unit="m2",
            measurement_method="SYNTHETIC_POLYGON_AREA",
            data_class=DataClass.CALCULATED,
            verification_status=VerificationStatus.NEEDS_REVIEW,
            source=SourceRef(
                document_id="synthetic-public-sample",
                revision="S1",
                sheet="SYN-101",
                page=1,
                evidence_reference="synthetic-zone:A",
            ),
            assumptions=["Synthetic sample quantity; reviewer must confirm geometry."],
        )
        conflict_record = QuantityRecord(
            item_id="SYN-ROOM-AREA-001",
            description="Synthetic room area with conflicting source",
            unit="m2",
            source_value=26.5,
            normalized_si_value=26.5,
            normalized_si_unit="m2",
            measurement_method="SYNTHETIC_TABULATED_AREA",
            data_class=DataClass.EXPLICIT,
            verification_status=VerificationStatus.CONFLICT,
            source=SourceRef(
                document_id="synthetic-public-schedule",
                revision="S1",
                sheet="SYN-201",
                page=2,
                evidence_reference="synthetic-row:7",
            ),
            conflicts=["Synthetic area differs from polygon sample by 2.5 m2."],
        )

        review_payload = review_record.to_dict()
        conflict_payload = conflict_record.to_dict()

        self.assertEqual(review_record.validate(), [])
        self.assertEqual(conflict_record.validate(), [])
        self.assertEqual(review_payload["verification_status"], "NEEDS_REVIEW")
        self.assertEqual(conflict_payload["verification_status"], "CONFLICT")
        self.assertNotEqual(review_payload["verification_status"], "VERIFIED")
        self.assertNotEqual(conflict_payload["verification_status"], "VERIFIED")
        self.assertEqual(review_payload["assumptions"], ["Synthetic sample quantity; reviewer must confirm geometry."])
        self.assertEqual(conflict_payload["conflicts"], ["Synthetic area differs from polygon sample by 2.5 m2."])

    def test_serialization_does_not_fabricate_private_paths_or_document_contents(self) -> None:
        record = QuantityRecord(
            item_id="SYN-OPENING-COUNT-001",
            description="Synthetic opening count with source identifier only",
            unit="pcs",
            source_value=4,
            normalized_si_value=4,
            normalized_si_unit="pcs",
            data_class=DataClass.EXPLICIT,
            verification_status=VerificationStatus.VERIFIED,
            source=SourceRef(document_id="synthetic-public-plan", evidence_reference="synthetic-markers:D1-D4"),
            notes="Synthetic public-safe sample, no document body attached.",
        )

        payload = record.to_dict()

        self.assertEqual(record.validate(), [])
        self.assertEqual(payload["verification_status"], "VERIFIED")
        self.assertEqual(payload["source"]["document_id"], "synthetic-public-plan")
        self.assertEqual(payload["source"]["evidence_reference"], "synthetic-markers:D1-D4")
        self.assertNotIn("file_path", payload["source"])
        self.assertNotIn("path", payload["source"])
        self.assertNotIn("document_contents", payload["source"])
        self.assertNotIn("text", payload["source"])
        self.assertNotIn("/", payload["source"]["document_id"])
        self.assertNotIn("\\", payload["source"]["document_id"])


if __name__ == "__main__":
    unittest.main()
