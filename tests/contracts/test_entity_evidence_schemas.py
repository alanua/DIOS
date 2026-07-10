from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas" / "dios"
EXPECTED_SCHEMAS = {
    "technical_entity.schema.json",
    "entity_representation.schema.json",
    "observation.schema.json",
}
CONTINUITY_SCHEMA = SCHEMA_DIR / "value_objects" / "entity_continuity.schema.json"


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


class EntityEvidenceSchemaTests(unittest.TestCase):
    def load_schemas(self) -> dict[str, dict[str, Any]]:
        return {
            path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(SCHEMA_DIR.glob("*.schema.json"))
        }

    def test_expected_entity_evidence_schema_set_exists(self) -> None:
        schemas = self.load_schemas()
        self.assertTrue(EXPECTED_SCHEMAS.issubset(schemas.keys()))
        self.assertTrue(CONTINUITY_SCHEMA.is_file())

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

    def test_entity_identity_is_separate_from_representations_and_continuity_edges(self) -> None:
        schema = self.load_schemas()["technical_entity.schema.json"]
        self.assertIn("representation_refs", schema["properties"])
        self.assertIn("continuity_relation_refs", schema["properties"])
        self.assertNotIn("continuity_relations", schema["properties"])
        self.assertNotIn("geometry", schema["properties"])
        self.assertNotIn("document_ref", schema["required"])
        active_rule = schema["allOf"][0]
        self.assertEqual(
            active_rule["if"]["properties"]["lifecycle"]["properties"]["status"]["const"],
            "ACTIVE",
        )
        self.assertEqual(
            active_rule["then"]["properties"]["representation_refs"]["minItems"],
            1,
        )

    def test_representation_uses_one_evidence_location_as_source_binding(self) -> None:
        schema = self.load_schemas()["entity_representation.schema.json"]
        required = set(schema["required"])
        self.assertTrue(
            {
                "technical_entity_id",
                "evidence_location",
                "representation_role",
                "physical_identity_status",
            }.issubset(required)
        )
        self.assertNotIn("technical_source_revision_id", schema["properties"])
        self.assertNotIn("document_ref", schema["properties"])
        legend_rule = schema["allOf"][0]
        self.assertEqual(
            legend_rule["if"]["properties"]["representation_role"]["const"],
            "LEGEND_SAMPLE",
        )
        self.assertEqual(
            legend_rule["then"]["properties"]["physical_identity_status"]["const"],
            "NON_INSTANCE",
        )

    def test_observation_binds_revision_set_and_requires_evidence_and_responsibility(self) -> None:
        schema = self.load_schemas()["observation.schema.json"]
        required = set(schema["required"])
        self.assertTrue(
            {
                "revision_set_id",
                "evidence_locations",
                "responsibility_trace",
                "data_class",
            }.issubset(required)
        )
        self.assertNotIn("technical_source_revision_id", schema["properties"])
        self.assertEqual(schema["properties"]["evidence_locations"]["minItems"], 1)
        inferred_rule = schema["allOf"][0]
        self.assertEqual(
            inferred_rule["if"]["properties"]["data_class"]["const"],
            "INFERRED",
        )
        self.assertIn("confidence", inferred_rule["then"]["required"])

    def test_continuity_relations_are_addressable_and_cover_conflict_shapes(self) -> None:
        schema = json.loads(CONTINUITY_SCHEMA.read_text(encoding="utf-8"))
        self.assertIn("continuity_relation_id", schema["required"])
        relation_types = set(schema["properties"]["relation_type"]["enum"])
        self.assertTrue(
            {
                "CONTINUES_AS",
                "SPLIT_INTO",
                "MERGED_FROM",
                "REPLACED_BY",
                "REMOVED",
                "INTRODUCED",
                "UNRESOLVED_MATCH",
            }.issubset(relation_types)
        )
        unresolved_rule = schema["allOf"][-1]
        self.assertEqual(
            unresolved_rule["if"]["properties"]["relation_type"]["const"],
            "UNRESOLVED_MATCH",
        )
        self.assertIn("confidence", unresolved_rule["then"]["required"])


if __name__ == "__main__":
    unittest.main()
