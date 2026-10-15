"""Pure-stdlib synthetic CAD capability acceptance; compatible with DIOS unittest CI."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
import unittest

from dios.cad_capability_benchmark import (
    ALL_CASES, CONTRACT_CASES, MISSING_CASES, CONTRACT_ONLY, NO_INSTALL,
    UNIMPLEMENTED, canonical_public_report_json, run_synthetic_capability_benchmark,
)
from dios.cad_bridge import (
    CADCapabilityProfile, CADSessionGrant, CadBridgeSession,
    CadCommand, CadCommandBatch, SyntheticMutableCadAdapter, CadBridgeError,
)


class CadCapabilityBenchmarkTests(unittest.TestCase):
    def test_public_capability_matrix_is_explicit_and_unambiguous(self):
        report = run_synthetic_capability_benchmark()
        self.assertEqual(report["schema"], "dios.cad_capability_benchmark.v1")
        self.assertEqual(report["release_verdict"], NO_INSTALL)
        self.assertEqual(report["native_cad_operations_verified"], 0)
        self.assertEqual(report["mode"], "SYNTHETIC_OFFLINE")
        self.assertFalse(report["customer_data_included"])
        entries = {v["capability"]: v for v in report["cases"]}
        self.assertEqual(set(entries), set(ALL_CASES))
        self.assertEqual(len(entries), len(ALL_CASES))
        for case in CONTRACT_CASES:
            self.assertEqual(entries[case]["status"], CONTRACT_ONLY)
        for case in MISSING_CASES:
            self.assertEqual(entries[case]["status"], UNIMPLEMENTED)
        self.assertFalse(any(v["status"] == "PROVIDER_VERIFIED" for v in report["cases"]))

    def test_drawing_and_bom_are_manual_metadata_not_fake_generation(self):
        entries = {v["capability"]: v
                   for v in run_synthetic_capability_benchmark()["cases"]}
        self.assertEqual(entries["drawing_metadata_record"]["status"], CONTRACT_ONLY)
        self.assertEqual(entries["bom_metadata_record"]["status"], CONTRACT_ONLY)
        self.assertEqual(entries["dimensioned_drawing_generation"]["status"], UNIMPLEMENTED)
        self.assertEqual(entries["automatic_bom_from_assembly"]["status"], UNIMPLEMENTED)
        self.assertEqual(entries["background_task_execution"]["status"], UNIMPLEMENTED)

    def test_report_is_reproducible_and_redacted(self):
        first = canonical_public_report_json()
        self.assertEqual(first, canonical_public_report_json())
        obj = json.loads(first)
        self.assertLess(len(first.encode()), 8000)
        self.assertIn("customer_data_included", obj)
        for prohibited in ("C:\\", "/home/", "/Users/", "token", "password", "filename"):
            self.assertNotIn(prohibited.lower(), first.lower())
        self.assertTrue(first.endswith("\n"))

    def test_concurrent_benchmark_runs_are_independent(self):
        with ThreadPoolExecutor(max_workers=4) as executor:
            outputs = list(executor.map(lambda _i: canonical_public_report_json(), range(8)))
        self.assertEqual(len(set(outputs)), 1)

    def test_synthetic_rights_and_unknown_vendor_commands_fail_closed(self):
        adapter = SyntheticMutableCadAdapter("safe-synthetic")
        session = CadBridgeSession("safe-session", adapter)
        readonly = CADSessionGrant(
            "safe-session", "safe-synthetic", CADCapabilityProfile.READ_ONLY,
            4102444800,
        )
        command = CadCommand("c1", "CREATE", "model", "toy", {"type": "part"})
        response = session.execute(CadCommandBatch.from_commands("b1", [command]), readonly)
        self.assertFalse(response.success)
        self.assertIsNone(adapter.entity("model"))
        self.assertEqual(adapter.snapshot().revision, 0)
        with self.assertRaises(CadBridgeError):
            CadCommand("c2", "RUN_MACRO", "model", "toy", {"name": "untrusted"})
        with self.assertRaises(CadBridgeError):
            CadCommand("c3", "DRAWING_TO_3D", "model", "toy", {})

    def test_rollback_and_failure_never_claim_live_support(self):
        report = run_synthetic_capability_benchmark()
        self.assertTrue(report["rollback_monotonic"])
        self.assertTrue(all("no native geometry" in v["evidence"]
                       for v in report["cases"] if v["status"] == CONTRACT_ONLY))
        self.assertTrue(all("no callable provider implementation" in v["evidence"]
                       for v in report["cases"] if v["status"] == UNIMPLEMENTED))


if __name__ == "__main__":
    unittest.main()
