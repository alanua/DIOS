from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas" / "dios"
VALUE_DIR = SCHEMA_DIR / "value_objects"
EXPECTED_DOMAIN_SCHEMAS = {
    "measurement_method.schema.json",
    "measurement_record.schema.json",
    "quantity_record.schema.json",
}
EXPECTED_VALUE_SCHEMAS = {
    "measurement_kind.schema.json",
    "unit_value.schema.json",
    "scale_control.schema.json",
    "calculation_plan.schema.json",
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


def iter_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(key)
            keys.update(iter_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(iter_keys(child))
    return keys


class MeasurementQuantitySchemaTests(unittest.TestCase):
    def load_domain_schemas(self) -> dict[str, dict[str, Any]]:
        return {
            path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(SCHEMA_DIR.glob("*.schema.json"))
        }

    def load_value_schemas(self) -> dict[str, dict[str, Any]]:
        return {
            path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(VALUE_DIR.glob("*.schema.json"))
        }

    def test_expected_measurement_schema_set_exists(self) -> None:
        self.assertTrue(EXPECTED_DOMAIN_SCHEMAS.issubset(self.load_domain_schemas()))
        self.assertTrue(EXPECTED_VALUE_SCHEMAS.issubset(self.load_value_schemas()))

    def test_new_schema_ids_match_filenames_and_local_refs_resolve(self) -> None:
        schemas = self.load_domain_schemas()
        value_schemas = self.load_value_schemas()
        for filename in EXPECTED_DOMAIN_SCHEMAS:
            schema = schemas[filename]
            self.assertEqual(schema["$id"], filename)
            for ref in iter_refs(schema):
                if ref.startswith("#") or "://" in ref or ref.startswith("urn:"):
                    continue
                target = SCHEMA_DIR / ref.split("#", 1)[0]
                self.assertTrue(target.is_file(), msg=f"{filename} has unresolved $ref {ref}")
        for filename in EXPECTED_VALUE_SCHEMAS:
            schema = value_schemas[filename]
            self.assertEqual(schema["$id"], filename)
            for ref in iter_refs(schema):
                if ref.startswith("#") or "://" in ref or ref.startswith("urn:"):
                    continue
                target = VALUE_DIR / ref.split("#", 1)[0]
                self.assertTrue(target.is_file(), msg=f"{filename} has unresolved $ref {ref}")

    def test_method_contract_is_versioned_bounded_and_evidence_ready(self) -> None:
        schema = self.load_domain_schemas()["measurement_method.schema.json"]
        required = set(schema["required"])
        self.assertTrue(
            {
                "method_version",
                "method_hash",
                "scale_requirement",
                "unit_policy",
                "representation_policy",
                "deduction_policy",
                "calculation_plan",
                "validation_fixture_refs",
            }.issubset(required)
        )
        representation = schema["properties"]["representation_policy"]["properties"]
        self.assertEqual(representation["duplicate_key"]["const"], "TECHNICAL_ENTITY_ID")
        self.assertEqual(
            schema["properties"]["unit_policy"]["properties"]["conversion_policy"]["const"],
            "EXPLICIT_ONLY",
        )

    def test_calculation_plan_is_typed_data_not_source_code(self) -> None:
        schema = self.load_value_schemas()["calculation_plan.schema.json"]
        self.assertIn("plan_hash", schema["required"])
        self.assertEqual(schema["properties"]["expression_language"]["const"], "DIOS_TYPED_OPS_V1")
        operation = schema["properties"]["operations"]["items"]["properties"]
        self.assertIn("COUNT_UNIQUE_ENTITY", operation["operation"]["enum"])
        self.assertFalse(operation["parameters"]["additionalProperties"])
        prohibited_keys = {"source_code", "script", "macro", "shell_command"}
        self.assertTrue(iter_keys(schema).isdisjoint(prohibited_keys))

    def test_scale_control_has_explicit_hard_gate_states(self) -> None:
        schema = self.load_value_schemas()["scale_control.schema.json"]
        statuses = set(schema["properties"]["status"]["enum"])
        self.assertEqual(statuses, {"VERIFIED", "NOT_REQUIRED", "UNVERIFIED", "CONFLICT"})
        verified_rule = schema["allOf"][0]
        self.assertEqual(verified_rule["if"]["properties"]["status"]["const"], "VERIFIED")
        self.assertIn("scale_factor", verified_rule["then"]["required"])
        self.assertEqual(verified_rule["then"]["properties"]["evidence_locations"]["minItems"], 1)

    def test_measurement_record_is_exact_context_and_replay_bound(self) -> None:
        schema = self.load_domain_schemas()["measurement_record.schema.json"]
        required = set(schema["required"])
        self.assertTrue(
            {
                "revision_set_id",
                "revision_set_hash",
                "measurement_method_id",
                "method_version",
                "method_hash",
                "selected_representation_refs",
                "evidence_locations",
                "scale_control",
                "applied_formula_display",
                "deterministic_receipt",
            }.issubset(required)
        )
        adjustment = schema["properties"]["adjustments"]["items"]
        self.assertTrue(
            {"subject_ref", "value", "formula_display", "evidence_locations"}.issubset(
                adjustment["required"]
            )
        )
        active_rule = schema["allOf"][0]
        self.assertIn("technical_snapshot_id", active_rule["then"]["required"])
        self.assertEqual(active_rule["then"]["properties"]["validation_result_refs"]["minItems"], 1)

    def test_quantity_aggregates_only_active_verified_measurements(self) -> None:
        schema = self.load_domain_schemas()["quantity_record.schema.json"]
        properties = schema["properties"]
        self.assertEqual(properties["input_policy"]["const"], "ACTIVE_VERIFIED_MEASUREMENTS_ONLY")
        self.assertEqual(properties["duplicate_key"]["const"], "TECHNICAL_ENTITY_ID")
        self.assertEqual(properties["input_measurement_refs"]["minItems"], 1)
        active_rule = schema["allOf"][0]
        self.assertIn("approval_ref", active_rule["then"]["required"])
        self.assertEqual(active_rule["then"]["properties"]["validation_result_refs"]["minItems"], 1)

    def test_quantity_scope_requires_refs_except_for_whole_project(self) -> None:
        scope = self.load_domain_schemas()["quantity_record.schema.json"]["properties"]["quantity_scope"]
        rule = scope["allOf"][0]
        self.assertEqual(rule["if"]["properties"]["scope_type"]["const"], "PROJECT")
        self.assertEqual(rule["then"]["properties"]["scope_refs"]["maxItems"], 0)
        self.assertEqual(rule["else"]["properties"]["scope_refs"]["minItems"], 1)

    def test_quantity_contract_contains_no_commercial_entitlement_fields(self) -> None:
        schema = self.load_domain_schemas()["quantity_record.schema.json"]
        properties = set(schema["properties"])
        self.assertTrue(
            properties.isdisjoint(
                {"price", "rate", "cost", "estimate", "payment", "entitlement", "invoice"}
            )
        )


if __name__ == "__main__":
    unittest.main()
