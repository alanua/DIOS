"""Provider-neutral CAD benchmark: public-safe synthetic evidence, never vendor claims.

This fixture is intentionally NOT a SolidWorks, AutoCAD, or MecAgent adapter.
Saving fields in a dictionary is not proof of editable feature-tree modelling,
material physics, assembly mates, dimensioned drawings, BOM generation, or jobs.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Final

from .cad_bridge import (
    CADCapabilityProfile, CADSessionGrant, CadBridgeError, CadBridgeSession,
    CadCommand, CadCommandBatch, SyntheticMutableCadAdapter,
)

SCHEMA: Final = "dios.cad_capability_benchmark.v1"
CONTRACT_ONLY: Final = "SYNTHETIC_RECORD_ONLY"
UNIMPLEMENTED: Final = "NOT_IMPLEMENTED"
NO_INSTALL: Final = "DO_NOT_INSTALL"

CONTRACT_CASES: Final[tuple[str, ...]] = (
    "part_record",
    "dimension_record",
    "material_record",
    "assembly_record",
    "drawing_metadata_record",
    "bom_metadata_record",
)
MISSING_CASES: Final[tuple[str, ...]] = (
    "parametric_feature_tree",
    "configurations_and_equations",
    "assembly_constraints_and_mates",
    "dimensioned_drawing_generation",
    "automatic_bom_from_assembly",
    "background_task_execution",
    "drawing_pdf_to_editable_cad",
    "step_to_native_parametric_features",
    "native_vendor_cad_integration",
    "manufacturing_grade_validation",
)
ALL_CASES: Final = CONTRACT_CASES + MISSING_CASES


@dataclass(frozen=True)
class CapabilityResult:
    capability: str
    status: str
    evidence: str

    def public(self) -> dict[str, str]:
        return {
            "capability": self.capability,
            "status": self.status,
            "evidence": self.evidence,
        }


def run_synthetic_capability_benchmark() -> dict[str, object]:
    """Exercise deterministic toy records only, with no external providers.

    The data are made-up fixture parameters (mm) and contain no real geometry,
    file paths, device identity, customer project or drawing bytes.
    """
    adapter = SyntheticMutableCadAdapter("benchmark-workspace")
    session = CadBridgeSession("benchmark-session", adapter)
    grant = CADSessionGrant(
        session_id="benchmark-session",
        workspace_id="benchmark-workspace",
        capability_profile=CADCapabilityProfile.FULL_CAD_WORKSPACE,
        expires_at=4102444800,
        approval_reference="synthetic-fixture-only",
    )
    initial = session.snapshot()
    session.checkpoint("before-fixture", grant)
    counter = 0

    def apply(kind: str, target_id: str, payload: dict[str, object]) -> None:
        nonlocal counter
        counter += 1
        c = CadCommand(
            command_id=f"benchmark-{counter}", command_type=kind,
            target_id=target_id, scope="toy", payload=payload,
        )
        batch = CadCommandBatch.from_commands(f"benchmark-batch-{counter}", [c])
        response = session.execute(batch, grant)
        if not response.success:
            raise CadBridgeError("BENCHMARK_SYNTHETIC_OPERATION_FAILED")

    apply("CREATE", "rotor", {
        "type": "part", "dimensions_mm": {"length": 120, "diameter": 15},
        "material": "unspecified",
    })
    part_ok = adapter.entity("rotor") == {
        "type": "part", "dimensions_mm": {"length": 120, "diameter": 15},
        "material": "unspecified",
    }
    apply("MODIFY", "rotor", {"dimensions_mm": {"length": 140, "diameter": 15}})
    dimension_ok = adapter.entity("rotor")["dimensions_mm"]["length"] == 140
    apply("MODIFY", "rotor", {"material": "synthetic_aluminum"})
    material_ok = adapter.entity("rotor")["material"] == "synthetic_aluminum"
    apply("CREATE", "helicopter", {
        "type": "assembly",
        "components": [{"ref": "rotor", "quantity": 2}],
    })
    assembly_ok = adapter.entity("helicopter")["components"] == [
        {"ref": "rotor", "quantity": 2}
    ]
    apply("CREATE", "drawing-index", {
        "type": "drawing_metadata",
        "source": "rotor",
        "view_names": ["front", "top", "side"],
    })
    drawing_ok = adapter.entity("drawing-index")["view_names"] == [
        "front", "top", "side"
    ]
    apply("CREATE", "bom-index", {
        "type": "bom_metadata",
        "manual_rows": [{"ref": "rotor", "quantity": 2}],
    })
    bom_ok = adapter.entity("bom-index")["manual_rows"] == [
        {"ref": "rotor", "quantity": 2}
    ]
    observed = (part_ok, dimension_ok, material_ok,
                assembly_ok, drawing_ok, bom_ok)
    if not all(observed):
        raise CadBridgeError("BENCHMARK_RECORD_VERIFICATION_FAILED")
    revision_before_rollback = adapter.snapshot().revision
    apply("ROLLBACK", "benchmark-workspace", {"checkpoint_id": "before-fixture"})
    after = session.snapshot()
    if not (after.entities == initial.entities and
            after.revision > revision_before_rollback):
        raise CadBridgeError("BENCHMARK_ROLLBACK_FAILED")

    report: list[CapabilityResult] = [
        CapabilityResult(
            name, CONTRACT_ONLY,
            "typed synthetic entity mutation and rollback only; no native geometry",
        )
        for name in CONTRACT_CASES
    ]
    report.extend(CapabilityResult(
        name, UNIMPLEMENTED,
        "no callable provider implementation or end-to-end evidence",
    ) for name in MISSING_CASES)
    return {
        "schema": SCHEMA,
        "reference": "MecAgent 2.0 advertised feature categories",
        "mode": "SYNTHETIC_OFFLINE",
        "release_verdict": NO_INSTALL,
        "native_cad_operations_verified": 0,
        "synthetic_contract_checks_passed": len(CONTRACT_CASES),
        "missing_provider_capabilities": len(MISSING_CASES),
        "cases": [entry.public() for entry in report],
        "rollback_monotonic": True,
        "customer_data_included": False,
    }


def canonical_public_report_json() -> str:
    return json.dumps(
        run_synthetic_capability_benchmark(),
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ) + "\n"
