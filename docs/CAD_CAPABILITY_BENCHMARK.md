# DIOS CAD capability benchmark — MecAgent 2.0 comparison

**Scope:** reproducible provider-neutral acceptance baseline for the Skeleton/DIOS CAD Bridge v0.2. It is **not a CAD add-in**, an agent that runs in SOLIDWORKS, or a performance comparison. No third-party installer, vendor SDK, cloud account, design file or private workstation information is read.

Reference (vendor's *advertised* functionality, not independently verified):
- [MecAgent V2.0.0 release](https://mecagent.com/blog/introducing-mecagent-v2-0-0-the-future-of-ai-and-cad)
- [MecAgent product](https://mecagent.com/)

## Important evidence distinction

A `SYNTHETIC_RECORD_ONLY` result means that our **in-memory CAD adapter** successfully saved a JSON record and could restore a prior state. **It does not mean** that real editable 3D geometry, drawings, BOM, constraints or native document revisions were produced. An `NOT_IMPLEMENTED` result means no verified provider adapter exists for that use case. Public code must never emit `PROVIDER_VERIFIED` simply because fixture tests pass.

The benchmark deliberately reports a pre-install verdict of `DO_NOT_INSTALL`, even when all of its synthetic tests are green.

## Functional acceptance matrix

| Capability | Current proof | Evidence required to pass a real provider acceptance test |
|---|---|---|
| Create part from specification | Synthetic entity record | New native CAD part with editable feature tree, real bounded workspace, measurable geometry |
| Change dimensional parameters | Synthetic metadata update | Named parameters and rebuild, measured geometry and constraint verification |
| Assign material | Synthetic metadata update | Native material library assignment, mass properties and verified units |
| Create assembly | Synthetic members metadata | Native component references, mates, constraints, and correct assemblies/transformations |
| Drawing record | Synthetic views metadata | Real sheet views, projection, dimensions, units, title block/template, export |
| BOM record | Synthetic manual rows | BOM **automatically** extracted from canonical assembly, verified part counts/materials |
| Configurations and equations | Not implemented | Native driving equations, multiple parameter configurations, deterministic rebuild |
| Assembly mates | Not implemented | Constraint resolution and interference/motion validation |
| CAD-to-Drawing | Not implemented | Real native drawing from part/assembly, independently checked dimensions/views |
| Drawing-to-CAD | Not implemented | PDF/image drawing → editable native part, source traceability and error bounds |
| STEP → native parametric | Not implemented | Usable feature tree from STEP, dimensioned editable geometry and fidelity measurements |
| Background jobs | Not implemented | Scheduled **authorized** job, isolated session, cancellation, dedupe, durable receipts |
| Live vendor integration | Not implemented | Private allowlisted provider APIs and disposable CAD document tests |
| Engineering-grade validation | Not implemented | Exact tolerances, mass, geometry, and supplier-ready drawing validation |

## Reproduce

On a reviewed DIOS checkout **containing CAD Bridge PR #35** (the benchmark is stacked on that branch):

```bash
PYTHONPATH=src python3 -m pytest -q tests/test_cad_capability_benchmark.py tests/test_cad_bridge.py tests/test_models.py
PYTHONPATH=src python3 -c "from dios.cad_capability_benchmark import canonical_public_report_json; print(canonical_public_report_json(), end='')"
```

The report is machine-readable, deterministic, redacted and synthetic-only. No dates, local paths, customer drawings, network calls or credentials enter it. It is appropriate to attach as public GitHub test *counts/status*, never as a private CAD artifact.

## Before workstation installation

1. Resolve the competing DIOS drafts #34 and #35 into **one canonical contract**; do not merge different command semantics without a compatibility review.
2. Connect the reviewed DIOS contract to Skeleton's real registered SignedGate and workstation session transport. Synthetic grants must **never** authorize a production operation.
3. Implement and verify the private per-provider CAD adapters against disposable files only, with a machine operator at the console and real stop/rollback.
4. Pass the acceptance matrix with provider-side evidence, not just JSON snapshots. Pay particular attention to drawings/BOM, STEP and parallel background tasks.
5. Verify encrypted receipt queue crash recovery, per-device Windows installer, rollback/ACLs and exact-device operator authorization. No auto-install/merge/deploy from this PR.

**Privacy boundary:** public repository contains only synthetic fixtures and public-safe status. Machine identifiers, customer drawings, filenames/paths, software licenses, private model revisions and third-party account tokens stay private.
