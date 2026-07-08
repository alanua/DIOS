# DIOS Canonical Memory-Gate Packet

Status: `APPROVED_DECISION_PACKET / PUBLIC_SAFE / PENDING_MEMORY_GATE_WRITE`

Purpose: provide one deterministic, operator-reviewable packet for canonical DIOS architecture decisions. This packet is a GitHub control artifact and must be written to canonical private memory only through the Skeleton Memory Gateway with validation, dedupe, provenance, approval and append-only audit.

## Memory write identity

```yaml
namespace: dios
record_type: architecture_decision_bundle
bundle_id: dios.architecture.core_revision_visualization.v1
dedupe_key: dios:architecture:core-revision-visualization:v1
idempotency_key: dios:architecture:core-revision-visualization:v1:2026-07-08
classification: PUBLIC_SAFE
approval_source: operator_explicit
canonical_write_status: PENDING_MEMORY_GATE_WRITE
source_repository: alanua/DIOS
source_branch: design/sketchup-bridge-architecture
source_pull_request: 3
```

## Canonical decisions

### DIOS-ARCH-001 — Core extraction authority

The DIOS core reads approved drawing/model sources, extracts and normalizes geometry, identifies objects and systems, classifies them, assigns stable identities, records source evidence and produces the canonical project scene/state model.

The DIOS core owns:

- source-pack intake;
- drawing and model adapters;
- revision and authority context;
- geometry extraction;
- object classification;
- stable object identity;
- room, level, sheet, zone and system relations;
- evidence links;
- validation findings;
- canonical scene graph and project-state snapshots.

### DIOS-ARCH-002 — Visualization is downstream

Visualization consumes an explicit approved DIOS project-state snapshot. It does not independently reinterpret source drawings as canonical truth.

Visualization owns representation choices such as:

- rendering engine and working-model adapter;
- approved assets;
- materials and style;
- visibility;
- scenes and cameras;
- previews, renders, animation and presentation artifacts.

Visualization may not silently change canonical geometry, room topology, openings, object placement, dimensions or revision context.

### DIOS-ARCH-003 — Revision is the project-state boundary

A drawing/model revision is an immutable boundary between project states.

```text
Revision
→ normalized project-state snapshot
→ classified change set from the previous snapshot
→ validation and approval
→ project stage
```

A new revision never silently overwrites the previous canonical state. Historical revisions and snapshots remain immutable.

### DIOS-ARCH-004 — Explicit revision sets

A project stage is based on an explicit `RevisionSet` containing compatible revisions from relevant disciplines.

The newest file from each discipline is not assumed compatible. Architecture, structure and MEP revisions require explicit compatibility review.

Revision conflicts block final downstream quantities and final visualization until resolved or explicitly accepted.

### DIOS-ARCH-005 — Project-state entities

The minimum revision/state model contains:

- `DrawingSource`;
- `DrawingRevision`;
- `RevisionSet`;
- `ProjectStage`;
- `ProjectStateSnapshot`;
- `RevisionChangeSet`;
- stable project objects and continuity relations;
- dependent artifacts with stale-state metadata.

### DIOS-ARCH-006 — Stable object continuity

A physical object keeps the same `object_id` across revisions while its identity remains valid.

Continuity relations include:

- `UNCHANGED`;
- `MODIFIED`;
- `ADDED`;
- `REMOVED`;
- `SPLIT_FROM`;
- `MERGED_FROM`;
- `REPLACED_BY`;
- `IDENTITY_UNCERTAIN`.

DIOS must neither silently allocate a new ID where continuity is known nor silently reuse an ID where identity is uncertain.

### DIOS-ARCH-007 — Revision register

DIOS produces a source revision register answering when each revision was issued, received, analyzed and approved.

Required date meanings remain distinct:

- `revision_date` — date declared by the issuer;
- `received_at` — date/time received by DIOS;
- `analyzed_at` — date/time extraction/comparison completed;
- `approved_at` — date/time human approval completed;
- `change_date` — authoritative effective date of the change.

Missing revision dates must remain unknown until resolved. Upload time must not silently substitute for revision date.

### DIOS-ARCH-008 — Detailed change register

DIOS produces a detailed revision change register answering what changed between two snapshots.

Each row records at minimum:

- from/to revision sets and snapshots;
- triggering revision;
- drawing, sheet/view, page/model location and zone/coordinates;
- stable object identity;
- semantic change class;
- before/after values;
- source evidence;
- data class and confidence;
- verification and approval status;
- quantity, visualization and coordination impact.

Initial semantic change classes include:

- `OBJECT_ADDED`;
- `OBJECT_REMOVED`;
- `OBJECT_MOVED`;
- `OBJECT_GEOMETRY_CHANGED`;
- `OBJECT_RECLASSIFIED`;
- `PROPERTY_CHANGED`;
- `MATERIAL_CHANGED`;
- `OPENING_ADDED`;
- `OPENING_REMOVED`;
- `ROOM_BOUNDARY_CHANGED`;
- `ROOM_IDENTITY_CHANGED`;
- `LEVEL_CHANGED`;
- `SYSTEM_RELATION_CHANGED`;
- `ANNOTATION_CHANGED`;
- `QUANTITY_IMPACT`;
- `VISUALIZATION_ONLY_CHANGE`;
- `COORDINATION_CONFLICT`;
- `UNKNOWN_CHANGE`.

### DIOS-ARCH-009 — Stale propagation

When a new accepted revision changes the project state, DIOS marks affected dependent artifacts as stale or requiring revalidation.

Dependent artifacts include:

- SketchUp working models;
- visualizations and renders;
- measurements and quantities;
- marked-up review artifacts;
- room and object registers;
- issue/conflict reports;
- asset assignments;
- exports.

Allowed stale-state concepts include:

- `CURRENT`;
- `POTENTIALLY_STALE`;
- `STALE`;
- `REVALIDATION_REQUIRED`;
- `BLOCKED_BY_CONFLICT`.

### DIOS-ARCH-010 — Source and revision authority

Authority is explicit by source, discipline and fact scope.

Examples:

- PDF may be revision authority for issued drawings;
- DXF/DWG may be a geometry source without being revision authority;
- IFC may be authoritative for selected content only;
- schedules/specifications may override properties without overriding geometry;
- marked-up review outputs are not automatically revision authority.

No source may gain authority merely because it is newer, more geometrically convenient or machine-readable.

### DIOS-ARCH-011 — No revision mixing

Every canonical object, quantity, visualization and review artifact references an explicit:

- `project_id`;
- `stage_id`;
- `revision_set_id`;
- `snapshot_id`;
- source/revision evidence.

DIOS must reject incompatible revision mixing rather than produce an apparently complete result.

### DIOS-ARCH-012 — SketchUp boundary

SketchUp is an editable working representation, not canonical truth and not revision authority.

The DIOS SketchUp integration consumes an approved snapshot and verifies project, stage, revision set and snapshot before mutation. Manual SketchUp changes return as `PROPOSED` changes and require DIOS validation and human approval.

### DIOS-ARCH-013 — Registers and exports

DIOS provides:

- machine-readable JSON revision register;
- compact CSV register;
- Excel review workbook;
- human-readable PDF revision report;
- per-revision summary;
- object history by stable `object_id`;
- room history by stable `room_id`;
- quantity-impact register;
- visualization-impact register;
- unresolved conflict register.

Excel and PDF are export/review artifacts, not canonical storage.

### DIOS-ARCH-014 — Responsibility split

```text
DIOS core determines what exists, where it exists, which revision it belongs to and how it changed.
Visualization determines how an approved state is represented.
Aufmass calculates against an approved state.
Coordination checks relations and conflicts between approved source facts.
All modules report results against the same project, stage, revision-set and snapshot context.
```

## Supersession and conflict rules

- This bundle supersedes no previously approved DIOS canonical memory record unless an explicit reconciliation identifies one.
- If an existing canonical fact conflicts with this packet, the write must stop and produce a conflict for operator review.
- The Memory Gateway must preserve provenance to the GitHub documents and explicit operator instruction.
- Derived semantic or graph indexes remain non-authoritative and rebuildable.

## Required Memory Gateway receipt

A successful canonical write must return or record:

- namespace;
- canonical record ID;
- bundle ID;
- dedupe and idempotency result;
- canonical revision;
- source provenance;
- approval reference;
- append-only audit reference;
- conflict/reconciliation result;
- write timestamp;
- verification status.

Until that receipt exists, status remains `PENDING_MEMORY_GATE_WRITE` even though the GitHub packet is durable.
