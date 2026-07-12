# Skeleton–DIOS gap analysis

Status: `ARCHITECTURE FREEZE INPUT / PUBLIC-SAFE / IMPLEMENTATION NOT AUTHORIZED`

Reviewed against the current public `alanua/Skeleton` control files, project manifests, capability registry, active architecture issues, and the DIOS Core/module contracts in draft PR #17.

## 1. Boundary used for this review

```text
Skeleton
→ generic control, identity, task execution, approvals, artifacts, audit,
  node/session transport, private-memory gateway and export routing

DIOS
→ technical source/revision semantics, authority scopes, revision sets,
  technical snapshots, entities, evidence, measurements, quantities,
  technical validation, detected changes and technical invalidation
```

A Skeleton gap does not justify duplicating the missing platform capability inside DIOS. DIOS must keep an external reference or extension point until Skeleton supplies the shared contract.

## 2. Status vocabulary

- `AVAILABLE` — current public contract or runtime capability exists and is usable as the shared owner.
- `PARTIAL` — a narrow or project-specific implementation exists, but it does not yet satisfy the reusable DIOS boundary.
- `SPECIFICATION_ONLY` — architecture is declared but not implemented or runner-ready.
- `MISSING_SHARED_CONTRACT` — no adequate shared contract was found.
- `DIOS_OWNED` — intentionally outside Skeleton and already represented in DIOS contracts.
- `STALE_METADATA` — current public control metadata conflicts with reviewed architecture.

## 3. Gap register

| ID | Capability | Current evidence | Status | Freeze effect | Required action |
|---|---|---|---|---|---|
| SG-01 | Project identity and routing | `BOOT_MANIFEST.yaml`, `PROJECT_INDEX.yaml`, `projects/*/PROJECT_MANIFEST.yaml`, `core/project_loader.py` capability | AVAILABLE | none | Keep DIOS references opaque and bind them to Skeleton project IDs. |
| SG-02 | Rich runtime `ProjectContext` | Project manifests expose identity, status, privacy and routing, but no reviewed reusable runtime record for stage, authority context and domain extensions | PARTIAL | non-blocking for schema freeze; blocking for production context persistence | Define a shared `ProjectContext`/extension attachment contract in Skeleton. DIOS must not create a replacement. |
| SG-03 | Users, roles, competence and authority | Current operator approvals, trusted-author checks and write gates exist; no general competence/authority model was found | MISSING_SHARED_CONTRACT | non-blocking for domain freeze; blocking for production approval policy | Add shared actor, role, competence and delegated-authority references. |
| SG-04 | Workflow/task execution | GitHub Runner is live and tested; universal Runner/Loop integration remains active work in Skeleton #1721 | PARTIAL | non-blocking for contract freeze; blocking for production workflow orchestration | Finish one authoritative task/Loop route and expose stable workflow/task references. |
| SG-05 | Generic approvals and review queues | Write gate exists; current `action_gate` is narrow and PR-merge-specific; operator-event contracts are dry-run/narrow | PARTIAL | blocking for accepted production snapshots, methods and quantities | Define provider-neutral `ApprovalDecision`, approval scope, expiry, supersession and review-queue references. |
| SG-06 | Generic source/artifact registry | `SOURCE_REGISTRY.yaml` is a trust/precedence registry, not an immutable artifact version service. Aufmass source-pack schema is an intake metadata checkpoint only | MISSING_SHARED_CONTRACT | blocking for real source ingestion and canonical revision binding | Define `ArtifactRecord`, immutable `ArtifactRevision`, content hash, storage route, privacy, lineage and derivative links. |
| SG-07 | Artifact storage and routing | Private routes and public/private boundaries exist; no single reviewed generic artifact-store contract was found | PARTIAL | blocking for production source and derivative persistence | Expose storage-route references and read/write receipts without leaking private paths. |
| SG-08 | Generic audit | Boot/audit reports, Runner comments, local ledgers and operator events exist, but no unified typed audit record spans all shared services | PARTIAL | non-blocking for schema freeze; blocking for production traceability | Define shared append-only audit event references and correlation IDs. |
| SG-09 | Module identity and registry | `CAPABILITY_REGISTRY.yaml` inventories capabilities; it is not yet a generic immutable module-manifest contract | PARTIAL | non-blocking because DIOS uses a manifest extension reference; blocking for module activation | Add a shared module manifest identity/version/lifecycle contract; attach DIOS extension by reference. |
| SG-10 | Node, resource and session transport | Skeleton #1720 defines the correct shared boundary and candidate entities, but remains specification-only | SPECIFICATION_ONLY | not required for first file-based vertical slice; blocking for application bridges | Implement and review provider-neutral node/session/lease/command/result contracts in Skeleton. |
| SG-11 | Memory Gateway canonical write boundary | Canonical SQLite exists internally; `MemoryGateway` is still declared as synthetic dry-run and live migration remains blocked in Skeleton #1544 | PARTIAL | non-blocking for DIOS schema freeze; blocking for canonical memory publication | Complete gateway parity and caller migration before any DIOS memory write. |
| SG-12 | Generic stale/invalid state hook | Skeleton has context freshness and task-state concepts, but no reviewed generic hook for domain invalidation graphs | MISSING_SHARED_CONTRACT | non-blocking: technical invalidation remains DIOS-owned | Add a generic attachment/event hook only; do not move technical propagation logic out of DIOS. |
| SG-13 | Generic export/artifact delivery | Individual exporters and private routing exist, but no unified approved-output routing contract was found | PARTIAL | non-blocking for schema freeze; blocking for production exports | Define derivative artifact registration, destination policy, delivery receipt and privacy enforcement. |
| SG-14 | DIOS project state metadata | `projects/dios/STATE.yaml` still cites closed draft PR #3 and an obsolete provider-specific bridge direction | STALE_METADATA | must be corrected before final freeze packet is treated as current | Replace the stale evidence source and summary after the final DIOS freeze verdict. |
| SG-15 | Aufmass ownership/routing | Skeleton still registers Aufmass as a DIOS child module whose current implementation route remains in Skeleton during freeze | AVAILABLE AS TRANSITION | none during freeze; migration required before new production implementation | Preserve current route until explicit post-freeze migration. Treat legacy code as evidence/fixtures, not canonical DIOS architecture. |

## 4. DIOS-owned capabilities — no Skeleton gap

The following remain correctly owned by DIOS and must not be requested from or duplicated in Skeleton:

- technical source class and authority scope;
- `TechnicalSourceRevision` domain extension;
- immutable `RevisionSet` and `TechnicalSnapshot`;
- sheets, views, zones, levels, rooms, grids and technical coordinate semantics;
- `TechnicalEntity`, source representations and continuity edges;
- observations and exact technical evidence locations;
- measurement methods, scale control, formulas and units;
- measurement and quantity records;
- technical validation findings;
- detected technical changes and stale propagation;
- discipline-pack semantics;
- derivative technical artifact classification.

## 5. Existing Skeleton assets that DIOS should reuse

DIOS should reuse rather than rebuild:

- manifest-driven boot and project selection;
- trust/precedence routing;
- GitHub Runner task gating and bounded worktree execution;
- read-before-write and explicit operator approval principles;
- public/private routing rules;
- capability inventory;
- private canonical SQLite as the eventual MemoryGateway storage engine;
- current Aufmass source-pack privacy pattern;
- public-safe synthetic fixture practice;
- node/session architecture from #1720 once implemented.

## 6. Architecture corrections required by this analysis

### 6.1 Do not treat Skeleton as fully implemented

Skeleton is an active controlled bootstrap with a mixture of:

- live capabilities;
- dry-run contracts;
- project-specific implementations;
- active migration work;
- architecture-only issues.

DIOS contracts must therefore distinguish a stable external reference from an available runtime service.

### 6.2 Do not use `SOURCE_REGISTRY.yaml` as the artifact registry

It defines source trust and precedence. It does not provide immutable file identity, revision lineage, content-hash reconciliation, storage receipts or derivative registration.

### 6.3 Do not use the current PR merge gate as the domain approval model

The current narrow action gate is evidence that Skeleton owns approval enforcement, but it is not a reusable approval record for technical snapshots, methods, measurements or quantities.

### 6.4 Do not activate Memory Gateway writes after DIOS freeze automatically

A new exact-head, public-safe packet and explicit operator approval are still required. Closed Skeleton #1618 correctly prohibits reuse of the superseded PR #3 packet.

### 6.5 Do not migrate production Aufmass during freeze

Current Skeleton routing remains transitional authority until a separately reviewed migration plan binds real source storage, approvals, audit and artifact revisions.

## 7. Minimum Skeleton prerequisites for the first production vertical slice

Before the architectural room/wall/opening measurement slice processes real drawings, the following shared prerequisites must exist or be supplied by a separately approved temporary adapter contract:

1. immutable artifact and artifact-revision identity;
2. private storage-route reference and exact read receipt;
3. reusable approval decision and review-queue reference;
4. generic audit/correlation reference;
5. project-context extension attachment;
6. approved derivative artifact registration and export routing.

Node/session runtime and live MemoryGateway writes are not prerequisites for the first file-based slice, provided no application bridge or canonical-memory publication is attempted.

## 8. Freeze assessment

The gaps above do **not** invalidate the DIOS domain architecture. They show that Skeleton is not yet a complete production platform for DIOS.

Recommended freeze interpretation:

```text
DIOS domain contracts may freeze
→ with external Skeleton references and explicit unavailable-service gates
→ without production runtime authorization
→ without merging PR #17 until final review
→ without production Aufmass migration
```

The final freeze verdict must explicitly separate:

- `DOMAIN_ARCHITECTURE_FROZEN`;
- `SHARED_PLATFORM_INTEGRATION_PENDING`;
- `PRODUCTION_RUNTIME_BLOCKED`.

## 9. Evidence reviewed

- Skeleton `README.md` and `BOOT_MANIFEST.yaml`;
- `COMMANDS.yaml`, `SOURCE_REGISTRY.yaml`, `PROJECT_INDEX.yaml`, `CAPABILITY_REGISTRY.yaml`;
- `projects/skeleton/PROJECT_MANIFEST.yaml`;
- `projects/dios/PROJECT_MANIFEST.yaml` and `STATE.yaml`;
- `projects/aufmass/PROJECT_MANIFEST.yaml`;
- `docs/AUFMASS_SOURCE_PACK.md` and `schemas/aufmass_source_pack.schema.json`;
- `schemas/action_gate.schema.json` and `schemas/operator_event.schema.json`;
- Skeleton issues #1544, #1618, #1720 and #1721;
- DIOS issues #8, #9, #15, #16 and draft PR #17.
