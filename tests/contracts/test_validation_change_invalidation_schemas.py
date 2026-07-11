from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas" / "dios"
VALUE_DIR = SCHEMA_DIR / "value_objects"
EXPECTED_DOMAIN_SCHEMAS = {
    "technical_validation_result.schema.json",
    "technical_change_set.schema.json",
    "technical_invalidation.schema.json",
}
EXPECTED_VALUE_SCHEMAS = {
    "validation_outcome.schema.json",
    "validation_severity.schema.json",
    "technical_impact.schema.json",
    "stale_state.schema.json",
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


class ValidationChangeInvalidationSchemaTests(unittest.TestCase):
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

    def test_expected_phase_five_schema_set_exists(self) -> None:
        self.assertTrue(EXPECTED_DOMAIN_SCHEMAS.issubset(self.load_domain_schemas()))
        self.assertTrue(EXPECTED_VALUE_SCHEMAS.issubset(self.load_value_schemas()))

    def test_schema_ids_match_filenames_and_local_refs_resolve(self) -> None:
        domain = self.load_domain_schemas()
        values = self.load_value_schemas()
        for filename in EXPECTED_DOMAIN_SCHEMAS:
            schema = domain[filename]
            self.assertEqual(schema["$id"], filename)
            for ref in iter_refs(schema):
                if ref.startswith("#") or "://" in ref or ref.startswith("urn:"):
                    continue
                target = SCHEMA_DIR / ref.split("#", 1)[0]
                self.assertTrue(target.is_file(), msg=f"{filename} has unresolved $ref {ref}")
        for filename in EXPECTED_VALUE_SCHEMAS:
            schema = values[filename]
            self.assertEqual(schema["$id"], filename)
            for ref in iter_refs(schema):
                if ref.startswith("#") or "://" in ref or ref.startswith("urn:"):
                    continue
                target = VALUE_DIR / ref.split("#", 1)[0]
                self.assertTrue(target.is_file(), msg=f"{filename} has unresolved $ref {ref}")

    def test_validation_result_pins_rule_and_exact_revision_context(self) -> None:
        schema = self.load_domain_schemas()["technical_validation_result.schema.json"]
        required = set(schema["required"])
        self.assertTrue(
            {
                "revision_set_id",
                "revision_set_hash",
                "validation_rule_id",
                "rule_version",
                "rule_hash",
                "subject_refs",
                "outcome",
                "findings",
            }.issubset(required)
        )

    def test_clean_pass_forbids_findings_and_all_other_outcomes_require_findings(self) -> None:
        rules = self.load_domain_schemas()["technical_validation_result.schema.json"]["allOf"]
        non_clean = rules[0]
        clean = rules[1]
        self.assertEqual(
            set(non_clean["if"]["properties"]["outcome"]["enum"]),
            {"PASS_WITH_WARNINGS", "FAIL", "BLOCKED"},
        )
        self.assertEqual(non_clean["then"]["properties"]["findings"]["minItems"], 1)
        self.assertEqual(clean["if"]["properties"]["outcome"]["const"], "PASS")
        self.assertEqual(clean["then"]["properties"]["findings"]["maxItems"], 0)

    def test_change_set_uses_detected_delta_not_mutation_or_stage_promotion(self) -> None:
        schema = self.load_domain_schemas()["technical_change_set.schema.json"]
        required = set(schema["required"])
        self.assertTrue(
            {
                "baseline_revision_set_id",
                "baseline_revision_set_hash",
                "target_revision_set_id",
                "target_revision_set_hash",
                "detection_method_id",
                "method_version",
                "method_hash",
                "change_items",
            }.issubset(required)
        )
        serialized = json.dumps(schema).lower()
        self.assertNotIn("last-write-wins", serialized)
        self.assertNotIn("promote_stage", serialized)
        self.assertNotIn("apply_mutation", serialized)

    def test_change_impacts_are_separate_channels(self) -> None:
        impact = self.load_value_schemas()["technical_impact.schema.json"]
        self.assertEqual(
            set(impact["required"]),
            {"semantic", "quantity", "visual", "coordination"},
        )
        for channel in impact["required"]:
            self.assertEqual(
                set(impact["properties"][channel]["enum"]),
                {"NONE", "POSSIBLE", "CONFIRMED", "UNKNOWN"},
            )

    def test_change_shapes_cover_add_remove_split_merge_and_unresolved(self) -> None:
        item = self.load_domain_schemas()["technical_change_set.schema.json"]["properties"]["change_items"]["items"]
        kinds = set(item["properties"]["change_type"]["enum"])
        self.assertTrue(
            {"ADDED", "REMOVED", "SPLIT", "MERGED", "UNRESOLVED"}.issubset(kinds)
        )
        unresolved = item["allOf"][-1]
        self.assertEqual(
            unresolved["if"]["properties"]["change_type"]["const"],
            "UNRESOLVED",
        )
        self.assertIn("confidence", unresolved["then"]["required"])

    def test_invalidation_is_explicit_graph_propagation_without_current_targets(self) -> None:
        schema = self.load_domain_schemas()["technical_invalidation.schema.json"]
        required = set(schema["required"])
        self.assertTrue(
            {
                "trigger_kind",
                "trigger_refs",
                "baseline_revision_set_id",
                "current_revision_set_id",
                "targets",
                "propagation_edges",
            }.issubset(required)
        )
        target = schema["properties"]["targets"]["items"]
        self.assertIn("required_action", target["required"])
        self.assertNotIn("CURRENT", target["properties"]["new_state"]["enum"])
        self.assertEqual(schema["properties"]["targets"]["minItems"], 1)
        self.assertEqual(schema["properties"]["propagation_edges"]["minItems"], 1)

    def test_invalidation_never_exposes_delete_or_silent_rewrite_actions(self) -> None:
        schema = self.load_domain_schemas()["technical_invalidation.schema.json"]
        serialized = json.dumps(schema).lower()
        for prohibited in ("delete_record", "overwrite_record", "silent_rewrite", "last-write-wins"):
            self.assertNotIn(prohibited, serialized)
        actions = set(
            schema["properties"]["targets"]["items"]["properties"]["required_action"]["enum"]
        )
        self.assertTrue(
            {
                "REVALIDATE",
                "REMEASURE",
                "REAGGREGATE",
                "REVIEW_CONTINUITY",
                "REAPPROVE",
                "REGENERATE_DERIVATIVE",
                "BLOCK_USE",
            }.issubset(actions)
        )

    def test_active_change_and_invalidation_records_require_verified_review_state(self) -> None:
        domain = self.load_domain_schemas()
        change_rule = domain["technical_change_set.schema.json"]["allOf"][0]["then"]
        invalidation_rule = domain["technical_invalidation.schema.json"]["allOf"][0]["then"]
        self.assertIn("decision_ref", change_rule["required"])
        self.assertEqual(
            change_rule["properties"]["verification_status"]["const"],
            "VERIFIED",
        )
        self.assertEqual(
            invalidation_rule["properties"]["verification_status"]["const"],
            "VERIFIED",
        )
        self.assertEqual(
            invalidation_rule["properties"]["validation_result_refs"]["minItems"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
