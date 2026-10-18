from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas" / "dios" / "value_objects"
EXPECTED_SCHEMAS = {
    "identifier.schema.json",
    "semantic_version.schema.json",
    "verification_status.schema.json",
    "data_class.schema.json",
    "privacy_class.schema.json",
    "content_hash.schema.json",
    "authority_scope.schema.json",
    "lifecycle_reference.schema.json",
    "evidence_location.schema.json",
    "confidence_assessment.schema.json",
    "responsibility_trace.schema.json",
    "deterministic_receipt.schema.json",
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


class ValueObjectSchemaTests(unittest.TestCase):
    def load_schemas(self) -> dict[str, dict[str, Any]]:
        return {
            path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(SCHEMA_DIR.glob("*.schema.json"))
        }

    def test_expected_schema_set_exists(self) -> None:
        schemas = self.load_schemas()
        self.assertTrue(EXPECTED_SCHEMAS.issubset(schemas.keys()))

    def test_schema_ids_are_unique_and_match_filenames(self) -> None:
        schemas = self.load_schemas()
        schema_ids = [schema["$id"] for schema in schemas.values()]
        self.assertEqual(len(schema_ids), len(set(schema_ids)))
        for filename, schema in schemas.items():
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(schema["$id"], filename)

    def test_all_relative_refs_resolve_inside_value_object_directory(self) -> None:
        schemas = self.load_schemas()
        for filename, schema in schemas.items():
            for ref in iter_refs(schema):
                if ref.startswith("#") or "://" in ref or ref.startswith("urn:"):
                    continue
                target = ref.split("#", 1)[0]
                self.assertIn(target, schemas, msg=f"{filename} has unresolved $ref {ref}")

    def test_core_classification_enums_are_stable(self) -> None:
        schemas = self.load_schemas()
        self.assertEqual(
            schemas["verification_status.schema.json"]["enum"],
            ["VERIFIED", "NEEDS_REVIEW", "CONFLICT", "NOT_FOUND"],
        )
        self.assertEqual(
            schemas["data_class.schema.json"]["enum"],
            ["EXPLICIT", "CALCULATED", "INFERRED", "UNKNOWN"],
        )

    def test_evidence_location_supports_declared_locator_types(self) -> None:
        schema = self.load_schemas()["evidence_location.schema.json"]
        kinds = {
            branch["properties"]["kind"]["const"]
            for branch in schema["properties"]["locator"]["oneOf"]
        }
        self.assertEqual(
            kinds,
            {
                "PAGE_POINT",
                "PAGE_BOX",
                "PAGE_POLYGON",
                "VECTOR_ENTITY",
                "MODEL_ENTITY",
                "TABLE_CELL",
                "TEXT_RANGE",
                "IMAGE_REGION",
            },
        )


if __name__ == "__main__":
    unittest.main()
