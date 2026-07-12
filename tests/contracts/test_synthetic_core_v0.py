from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT / "fixtures" / "synthetic" / "core_v0" / "fixture_suite.json"

EXPECTED_CASE_IDS = {f"COREV0-{index:02d}" for index in range(1, 17)}
PROVIDER_PRIVATE_TERMS = {
    "solidworks",
    "autocad",
    "sketchup",
    "nano banana",
    "chatgpt",
    "customer",
    "address",
}


def evaluate_case(case: dict[str, Any]) -> list[str]:
    scenario = case["scenario_type"]
    data = case["data"]
    codes: list[str] = []

    if scenario == "TWO_REVISIONS_ONE_SHEET":
        revisions = data["revisions"]
        revision_ids = {item["technical_source_revision_id"] for item in revisions}
        hashes = {item["content_hash"] for item in revisions}
        if len(revisions) != 2 or len(revision_ids) != 2 or len(hashes) != 2:
            codes.append("REVISION_IDENTITY_NOT_IMMUTABLE")

    elif scenario == "EXACT_REVISION_SET_AND_SNAPSHOT":
        revision_set = data["revision_set"]
        snapshot = data["snapshot"]
        if (
            snapshot["revision_set_id"] != revision_set["revision_set_id"]
            or snapshot["revision_set_hash"] != revision_set["set_hash"]
            or len(revision_set["member_ids"]) != len(revision_set["member_hashes"])
        ):
            codes.append("SNAPSHOT_REVISION_SET_MISMATCH")

    elif scenario == "STABLE_ENTITY_CONTINUITY":
        relations = data["relations"]
        if len(relations) != 1:
            codes.append("ENTITY_CONTINUITY_CONFLICT")
        else:
            relation = relations[0]
            if (
                relation["relation_type"] != "CONTINUES_AS"
                or len(relation["source_entity_ids"]) != 1
                or len(relation["target_entity_ids"]) != 1
                or relation["source_entity_ids"][0] != relation["target_entity_ids"][0]
                or relation["verification_status"] != "VERIFIED"
            ):
                codes.append("ENTITY_CONTINUITY_CONFLICT")

    elif scenario == "SPLIT_AND_MERGE_CONFLICT":
        relations = data["relations"]
        one_to_one_targets: set[tuple[str, str]] = set()
        split_sources: set[str] = set()
        merge_targets: set[str] = set()
        for relation in relations:
            source_ids = relation["source_entity_ids"]
            target_ids = relation["target_entity_ids"]
            if relation["relation_type"] == "CONTINUES_AS":
                one_to_one_targets.update(
                    (source, target) for source in source_ids for target in target_ids
                )
            elif relation["relation_type"] == "SPLIT_INTO":
                split_sources.update(source_ids)
            elif relation["relation_type"] == "MERGED_FROM":
                merge_targets.update(target_ids)
        conflict = any(source in split_sources for source, _ in one_to_one_targets)
        conflict = conflict or any(target in merge_targets for _, target in one_to_one_targets)
        if conflict:
            codes.append("ENTITY_CONTINUITY_CONFLICT")

    elif scenario == "CONTROL_DIMENSION_SCALE_VERIFIED":
        method = data["method"]
        scale = data["scale_control"]
        expected = scale["real_value"] / scale["drawing_value"]
        if (
            method["scale_requirement"] == "CONTROL_DIMENSION_REQUIRED"
            and (
                scale["status"] != "VERIFIED"
                or not scale["evidence_locations"]
                or scale["scale_factor"] <= 0
                or abs(scale["scale_factor"] - expected) > 1e-9
            )
        ):
            codes.append("SCALE_CONTROL_INVALID")

    elif scenario == "UNVERIFIED_SCALE_MEASUREMENT":
        method = data["method"]
        status = data["measurement"]["scale_control"]["status"]
        if method["scale_requirement"] == "CONTROL_DIMENSION_REQUIRED" and status != "VERIFIED":
            codes.append("UNVERIFIED_SCALE")

    elif scenario == "ROOM_WALL_OPENING_FULL_EVIDENCE":
        for measurement in data["measurements"]:
            if not all(
                [
                    measurement.get("technical_entity_id"),
                    measurement.get("method_id"),
                    measurement.get("formula"),
                    measurement.get("unit"),
                    measurement.get("evidence_locations"),
                    measurement.get("scale_status") == "VERIFIED",
                    measurement.get("verification_status") == "VERIFIED",
                ]
            ):
                codes.append("MEASUREMENT_EVIDENCE_INCOMPLETE")
                break

    elif scenario == "STRUCTURAL_CROSS_CHECK_CONFLICT":
        delta = abs(data["architectural"]["offset_mm"] - data["structural"]["offset_mm"])
        if delta > data["tolerance_mm"]:
            codes.append("STRUCTURAL_GEOMETRY_CONFLICT")

    elif scenario == "DUPLICATE_REPRESENTATION_ONE_OBJECT":
        representations = [
            item
            for item in data["representations"]
            if item["role"] == "INSTALLED_INSTANCE"
            and item["physical_identity_status"] != "NON_INSTANCE"
        ]
        unique_entities = {item["technical_entity_id"] for item in representations}
        if data["quantity"]["duplicate_key"] != "TECHNICAL_ENTITY_ID":
            codes.append("DUPLICATE_KEY_INVALID")
        if data["quantity"]["result_value"] != len(unique_entities):
            codes.append("DUPLICATE_REPRESENTATION_COUNTED")

    elif scenario == "LEGEND_SYMBOL_EXCLUDED":
        installed = [
            item
            for item in data["representations"]
            if item["role"] == "INSTALLED_INSTANCE"
            and item["physical_identity_status"] != "NON_INSTANCE"
        ]
        if any(
            item["role"] == "LEGEND_SAMPLE"
            and item["physical_identity_status"] != "NON_INSTANCE"
            for item in data["representations"]
        ):
            codes.append("LEGEND_CLASSIFIED_AS_INSTANCE")
        if data["quantity"]["result_value"] != len(
            {item["technical_entity_id"] for item in installed}
        ):
            codes.append("LEGEND_INCLUDED_IN_COUNT")

    elif scenario == "SEMANTIC_LABEL_CLASS_MISMATCH":
        if data["label"]["declared_class"] != data["linked_entity"]["entity_class"]:
            codes.append("SEMANTIC_LABEL_CLASS_MISMATCH")

    elif scenario == "UNIT_SCALE_IMPLAUSIBLE_MAGNITUDE":
        measurement = data["measurement"]
        profile = data["profile_limit"]
        if (
            measurement["normalized_unit"] == profile["unit"]
            and measurement["normalized_value"] > profile["max_value"]
        ):
            codes.append("IMPLAUSIBLE_MAGNITUDE")

    elif scenario == "STALE_MEASUREMENT_AFTER_REVISION_CHANGE":
        measurement = data["measurement"]
        current = data["current_context"]
        context_changed = (
            measurement["revision_set_id"] != current["revision_set_id"]
            or measurement["revision_set_hash"] != current["revision_set_hash"]
        )
        if context_changed and measurement["stale_state"] == "CURRENT":
            codes.append("STALE_AFTER_REVISION_CHANGE")

    elif scenario == "INVALID_QUANTITY_MISSING_FORMULA_OR_UNIT":
        quantity = data["quantity"]
        result = quantity.get("result_value") or {}
        if not quantity.get("calculation_plan") or not result.get("unit"):
            codes.append("INVALID_QUANTITY_FORMULA_OR_UNIT")

    elif scenario == "DERIVATIVE_AUTHORITY_PROMOTION":
        artifact_class = data["artifact"]["artifact_class"]
        requested = set(data["requested_authority_kinds"])
        forbidden = {"REVISION", "GEOMETRY", "SEMANTIC", "MEASUREMENT_INPUT"}
        if artifact_class == "DERIVATIVE" and requested.intersection(forbidden):
            codes.append("DERIVATIVE_AUTHORITY_PROMOTION")

    elif scenario == "TWO_MODULE_EXTENSIONS_ONE_IDENTITY":
        entity_id = data["technical_entity"]["technical_entity_id"]
        extension_entity_ids = {
            item["technical_entity_id"] for item in data["module_extensions"]
        }
        module_ids = {item["module_id"] for item in data["module_extensions"]}
        if extension_entity_ids != {entity_id} or len(module_ids) != len(
            data["module_extensions"]
        ):
            codes.append("IDENTITY_DUPLICATION_ACROSS_MODULES")

    else:
        codes.append("UNKNOWN_SYNTHETIC_SCENARIO")

    return sorted(set(codes))


class SyntheticCoreV0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.cases = cls.suite["cases"]

    def test_suite_is_public_safe_and_contains_exact_declared_cases(self) -> None:
        self.assertEqual(self.suite["classification"], "PUBLIC_SAFE_SYNTHETIC_ONLY")
        case_ids = {item["case_id"] for item in self.cases}
        self.assertEqual(case_ids, EXPECTED_CASE_IDS)
        self.assertEqual(len(case_ids), len(self.cases))

    def test_expected_status_and_codes_match_invariant_evaluation(self) -> None:
        for case in self.cases:
            with self.subTest(case_id=case["case_id"]):
                actual_codes = evaluate_case(case)
                self.assertEqual(actual_codes, sorted(case["expected_codes"]))
                expected_status = "VALID" if not actual_codes else "INVALID"
                self.assertEqual(case["expected_status"], expected_status)

    def test_valid_cases_have_no_invariant_violations(self) -> None:
        valid_cases = [item for item in self.cases if item["expected_status"] == "VALID"]
        self.assertGreaterEqual(len(valid_cases), 8)
        for case in valid_cases:
            with self.subTest(case_id=case["case_id"]):
                self.assertEqual(evaluate_case(case), [])

    def test_invalid_cases_expose_declared_failure_codes(self) -> None:
        invalid_cases = [item for item in self.cases if item["expected_status"] == "INVALID"]
        expected = {
            "ENTITY_CONTINUITY_CONFLICT",
            "UNVERIFIED_SCALE",
            "STRUCTURAL_GEOMETRY_CONFLICT",
            "SEMANTIC_LABEL_CLASS_MISMATCH",
            "IMPLAUSIBLE_MAGNITUDE",
            "STALE_AFTER_REVISION_CHANGE",
            "INVALID_QUANTITY_FORMULA_OR_UNIT",
            "DERIVATIVE_AUTHORITY_PROMOTION",
        }
        actual = {code for item in invalid_cases for code in evaluate_case(item)}
        self.assertEqual(actual, expected)

    def test_no_provider_or_private_terms_enter_public_fixtures(self) -> None:
        serialized = json.dumps(self.suite, sort_keys=True).lower()
        for term in PROVIDER_PRIVATE_TERMS:
            self.assertNotIn(term, serialized)

    def test_every_case_has_stable_shape(self) -> None:
        for case in self.cases:
            with self.subTest(case_id=case["case_id"]):
                self.assertEqual(
                    set(case),
                    {
                        "case_id",
                        "scenario_type",
                        "expected_status",
                        "expected_codes",
                        "data",
                    },
                )
                self.assertTrue(case["scenario_type"])
                self.assertIsInstance(case["data"], dict)


if __name__ == "__main__":
    unittest.main()
