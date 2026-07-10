from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas" / "dios"
EXPECTED_SCHEMAS = {
    "technical_source_revision.schema.json",
    "revision_set.schema.json",
    "technical_snapshot.schema.json",
}


def iter_refs(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref" and isinstance(child, str):
                refs.append(child)
            else:
                refs.extend(iter_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.extend(iter_refs(child))
    return refs


class SourceStateSchemaTests(unittest.TestCase):
    def load_schemas(self) -> dict[str, dict[str, Any]]:
        return {
            path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(SCHEMA_DIR.glob("*.schema.json"))
        }

    def test_expected_source_state_schema_set_exists(self) -> None:
        schemas = self.load_schemas()
        self.assertTrue(EXPECTED_SCHEMAS.issubset(schemas.keys()))

    def test_schema_ids_match_filenames_and_local_refs_resolve(self) -> None:
        schemas = self.load_schemas()
        for filename in EXPECTED_SCHEMAS:
            schema = schemas[filename]
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(schema["$id"], filename)
            for ref in iter_refs(schema):
                if ref.startswith("#") or "://" in ref or ref.startswith("urn:"):
                    continue
                target = SCHEMA_DIR / ref.split("#", 1)[0]
                self.assertTrue(target.is_file(), msg=f"{filename} has unresolved $ref {ref}")

    def test_source_revision_binds_skeleton_artifact_and_explicit_authority(self) -> None:
        schema = self.load_schemas()["technical_source_revision.schema.json"]
        required = set(schema["required"])
        self.assertTrue(
            {
                "source_artifact_id",
                "artifact_revision_id",
                "content_hash",
                "authority_scopes",
            }.issubset(required)
        )
        authority = schema["properties"]["authority_scopes"]
        self.assertEqual(authority["minItems"], 1)
        self.assertTrue(authority["uniqueItems"])
        issue_states = schema["properties"]["source_issue_status"]["enum"]
        self.assertNotIn("SUPERSEDED", issue_states)

    def test_revision_set_members_pin_revision_identity_and_hash(self) -> None:
        schema = self.load_schemas()["revision_set.schema.json"]
        member_required = set(schema["properties"]["members"]["items"]["required"])
        self.assertTrue(
            {"technical_source_revision_id", "content_hash", "member_role"}.issubset(
                member_required
            )
        )
        self.assertEqual(schema["properties"]["members"]["minItems"], 1)

    def test_snapshot_uses_shared_lifecycle_and_active_state_requires_review_receipts(self) -> None:
        schema = self.load_schemas()["technical_snapshot.schema.json"]
        self.assertNotIn("project_stage_ref", schema["required"])
        self.assertNotIn("snapshot_status", schema["properties"])
        active_rule = schema["allOf"][0]
        self.assertEqual(
            active_rule["if"]["properties"]["lifecycle"]["properties"]["status"]["const"],
            "ACTIVE",
        )
        self.assertTrue(
            {"approval_ref", "validation_result_refs"}.issubset(
                active_rule["then"]["required"]
            )
        )
        self.assertEqual(
            active_rule["then"]["properties"]["verification_status"]["const"],
            "VERIFIED",
        )


if __name__ == "__main__":
    unittest.main()
