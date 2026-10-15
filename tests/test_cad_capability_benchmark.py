"""MecAgent-reference capability matrix tests: synthetic records, no CAD deployment."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from dios.cad_capability_benchmark import (
    ALL_CASES, CONTRACT_CASES, MISSING_CASES, CONTRACT_ONLY, NO_INSTALL,
    UNIMPLEMENTED, canonical_public_report_json, run_synthetic_capability_benchmark,
)
from dios.cad_bridge import (
    CADCapabilityProfile, CADSessionGrant, CadBridgeSession,
    CadCommand, CadCommandBatch, SyntheticMutableCadAdapter, CadBridgeError,
)

def test_public_capability_matrix_is_explicit_and_unambiguous():
    report = run_synthetic_capability_benchmark()
    assert report["schema"] == "dios.cad_capability_benchmark.v1"
    assert report["release_verdict"] == NO_INSTALL
    assert report["native_cad_operations_verified"] == 0
    assert report["mode"] == "SYNTHETIC_OFFLINE"
    assert not report["customer_data_included"]
    entries = {v["capability"]: v for v in report["cases"]}
    assert set(entries) == set(ALL_CASES)
    assert len(entries) == len(ALL_CASES)
    for case in CONTRACT_CASES:
        assert entries[case]["status"] == CONTRACT_ONLY
    for case in MISSING_CASES:
        assert entries[case]["status"] == UNIMPLEMENTED
    assert all(entry["status"] != "PROVIDER_VERIFIED" for entry in report["cases"])

def test_drawing_and_bom_are_manual_metadata_not_fake_generation():
    entries = {v["capability"]: v
               for v in run_synthetic_capability_benchmark()["cases"]}
    assert entries["drawing_metadata_record"]["status"] == CONTRACT_ONLY
    assert entries["bom_metadata_record"]["status"] == CONTRACT_ONLY
    assert entries["dimensioned_drawing_generation"]["status"] == UNIMPLEMENTED
    assert entries["automatic_bom_from_assembly"]["status"] == UNIMPLEMENTED
    assert entries["background_task_execution"]["status"] == UNIMPLEMENTED

def test_report_is_reproducible_and_redacted():
    first = canonical_public_report_json()
    assert first == canonical_public_report_json()
    obj = json.loads(first)
    assert len(first.encode()) < 8000
    for prohibited in ("C:\\", "/home/", "/Users/", "token", "password", "customer", "filename"):
        if prohibited == "customer":
            # Public non-sensitive boolean is explicitly allowed.
            assert "customer_data_included" in obj
        else:
            assert prohibited.lower() not in first.lower()
    assert first.endswith("\n")

def test_concurrent_benchmark_runs_are_independent():
    with ThreadPoolExecutor(max_workers=4) as executor:
        outputs = list(executor.map(lambda _i: canonical_public_report_json(), range(8)))
    assert len(set(outputs)) == 1

def test_synthetic_rights_and_unknown_vendor_commands_fail_closed():
    adapter = SyntheticMutableCadAdapter("safe-synthetic")
    session = CadBridgeSession("safe-session", adapter)
    readonly = CADSessionGrant(
        "safe-session", "safe-synthetic", CADCapabilityProfile.READ_ONLY,
        4102444800,
    )
    command = CadCommand("c1", "CREATE", "model", "toy", {"type":"part"})
    response = session.execute(CadCommandBatch.from_commands("b1", [command]), readonly)
    assert not response.success
    assert adapter.entity("model") is None
    assert adapter.snapshot().revision == 0
    with pytest.raises(CadBridgeError):
        CadCommand("c2", "RUN_MACRO", "model", "toy", {"name":"untrusted"})
    with pytest.raises(CadBridgeError):
        CadCommand("c3", "DRAWING_TO_3D", "model", "toy", {})

def test_rollback_and_failure_never_claim_live_support():
    report = run_synthetic_capability_benchmark()
    assert report["rollback_monotonic"]
    assert all("no native geometry" in v["evidence"]
               for v in report["cases"] if v["status"] == CONTRACT_ONLY)
    assert all("no callable provider implementation" in v["evidence"]
               for v in report["cases"] if v["status"] == UNIMPLEMENTED)
