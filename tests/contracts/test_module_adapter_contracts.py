from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas" / "modules"
EXPECTED_SCHEMAS = {
    "failure_declaration.schema.json",
    "dios_module_manifest_extension.schema.json",
    "source_adapter_contract.schema.json",
    "discipline_pack_contract.schema.json",
    "application_bridge_contract.schema.json",
    "output_adapter_contract.schema.json",
    "project_profile.schema.json",
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


class ModuleAdapterContractTests(unittest.TestCase):
    def load_schemas(self) -> dict[str, dict[str, Any]]:
        return {
            path.name: json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(SCHEMA_DIR.glob("*.schema.json"))
        }

    def test_expected_module_schema_set_exists(self) -> None:
        self.assertTrue(EXPECTED_SCHEMAS.issubset(self.load_schemas()))

    def test_schema_ids_match_filenames_and_local_refs_resolve(self) -> None:
        schemas = self.load_schemas()
        for filename in EXPECTED_SCHEMAS:
            schema = schemas[filename]
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(schema["$id"], filename)
            for ref in iter_refs(schema):
                if ref.startswith("#") or "://" in ref or ref.startswith("urn:"):
                    continue
                target = (SCHEMA_DIR / ref.split("#", 1)[0]).resolve()
                self.assertTrue(target.is_file(), msg=f"{filename} has unresolved $ref {ref}")

    def test_manifest_is_a_dios_extension_not_a_second_generic_manifest(self) -> None:
        schema = self.load_schemas()["dios_module_manifest_extension.schema.json"]
        required = set(schema["required"])
        self.assertIn("skeleton_module_manifest_ref", required)
        self.assertNotIn("module_id", schema["properties"])
        self.assertNotIn("workflow_engine", schema["properties"])
        self.assertEqual(
            set(schema["properties"]["module_class"]["enum"]),
            {"SOURCE_ADAPTER", "DISCIPLINE_PACK", "APPLICATION_BRIDGE", "OUTPUT_ADAPTER"},
        )

    def test_source_adapter_cannot_assign_authority_or_emit_measurements(self) -> None:
        schema = self.load_schemas()["source_adapter_contract.schema.json"]
        revision_policy = schema["properties"]["revision_binding_policy"]["properties"]
        self.assertFalse(revision_policy["may_assign_authority"]["const"])
        prohibited = schema["properties"]["prohibited_outputs"]["const"]
        self.assertEqual(
            prohibited,
            [
                "MEASUREMENT_RECORD",
                "QUANTITY_RECORD",
                "APPROVAL_DECISION",
                "AUTHORITY_PROMOTION",
                "CANONICAL_SOURCE_MUTATION",
            ],
        )

    def test_discipline_pack_does_not_own_quantity_aggregation_or_platform_services(self) -> None:
        schema = self.load_schemas()["discipline_pack_contract.schema.json"]
        allowed = set(schema["properties"]["allowed_output_records"]["items"]["enum"])
        self.assertNotIn("QuantityRecord", allowed)
        prohibited = set(schema["properties"]["prohibited_responsibilities"]["const"])
        self.assertTrue(
            {
                "GENERIC_WORKFLOW_EXECUTION",
                "GENERIC_APPROVAL_STORAGE",
                "GENERIC_ARTIFACT_STORAGE",
                "DIRECT_QUANTITY_AGGREGATION",
                "PROVIDER_SPECIFIC_EXECUTION",
            }.issubset(prohibited)
        )

    def test_application_bridge_is_typed_private_and_never_mutates_original_source(self) -> None:
        schema = self.load_schemas()["application_bridge_contract.schema.json"]
        required = set(schema["required"])
        self.assertTrue(
            {
                "provider_binding_ref",
                "skeleton_resource_session_contract_ref",
                "allowed_operations",
                "post_operation_validation",
            }.issubset(required)
        )
        binding = schema["properties"]["resource_binding_policy"]["properties"]
        self.assertFalse(binding["original_source_mutation_allowed"]["const"])
        prohibited = set(schema["properties"]["prohibited_execution_modes"]["const"])
        self.assertTrue(
            {
                "ARBITRARY_GENERATED_SOURCE_CODE",
                "PRIMARY_MOUSE_AUTOMATION",
                "UNBOUNDED_MACRO_EXECUTION",
                "HIDDEN_PROVIDER_STATE_MUTATION",
            }.issubset(prohibited)
        )

    def test_read_only_bridge_mode_only_allows_read_only_operations(self) -> None:
        schema = self.load_schemas()["application_bridge_contract.schema.json"]
        read_only_rule = schema["allOf"][0]
        self.assertEqual(
            read_only_rule["if"]["properties"]["execution_mode"]["const"],
            "READ_ONLY_INSPECTION",
        )
        operation_mutability = read_only_rule["then"]["properties"]["allowed_operations"]["items"]["properties"]["mutability"]
        self.assertEqual(operation_mutability["const"], "READ_ONLY")

    def test_output_adapter_is_derivative_reference_only(self) -> None:
        schema = self.load_schemas()["output_adapter_contract.schema.json"]
        properties = schema["properties"]
        self.assertEqual(properties["authority_result"]["const"], "REFERENCE_ONLY")
        self.assertFalse(properties["canonical_write_allowed"]["const"])
        self.assertFalse(properties["source_revision_promotion_allowed"]["const"])

    def test_project_profile_is_private_selection_not_embedded_secrets_or_contracts(self) -> None:
        schema = self.load_schemas()["project_profile.schema.json"]
        self.assertEqual(set(schema["properties"]["privacy_class"]["enum"]), {"PRIVATE", "RESTRICTED"})
        configuration = schema["properties"]["module_configurations"]["items"]["properties"]
        self.assertIn("secret_ref", configuration)
        self.assertNotIn("secret_value", configuration)
        self.assertNotIn("module_contract", configuration)

    def test_failure_declaration_has_blocking_and_recovery_semantics(self) -> None:
        schema = self.load_schemas()["failure_declaration.schema.json"]
        required = set(schema["required"])
        self.assertTrue(
            {
                "code",
                "category",
                "severity",
                "retryability",
                "blocks_downstream",
                "evidence_required",
            }.issubset(required)
        )

    def test_public_module_contracts_contain_no_executable_code_fields(self) -> None:
        prohibited_keys = {
            "source_code",
            "script",
            "macro",
            "shell_command",
            "password",
            "token",
            "api_key",
        }
        for filename, schema in self.load_schemas().items():
            self.assertTrue(
                prohibited_keys.isdisjoint(iter_keys(schema)),
                msg=f"{filename} contains prohibited executable or secret field",
            )


if __name__ == "__main__":
    unittest.main()
