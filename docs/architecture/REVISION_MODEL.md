# DIOS Revision and Project Change Model

Status: `DESIGN / ARCHITECTURE CANDIDATE / NOT PRODUCTION`

## 1. Purpose

DIOS treats drawing revisions as immutable boundaries between project states.

A revision is not only a filename suffix or title-block field. It defines the source boundary for a specific discipline/source lineage and may contribute to a candidate project state.

The core rule is:

```text
Source revision
→ candidate RevisionSet
→ candidate ProjectStateSnapshot
→ ChangeSet from previous approved snapshot
→ validation
→ human approval decision
→ approved snapshot and, only when explicitly approved, project-stage transition
```

Visualization, measurement, review and export modules must consume an explicit revision or approved revision set. They must never silently combine incompatible revisions.

## 2. Main entities

### DrawingSource

Represents an imported PDF, scan, raster, vector drawing, DXF, IFC or other source file.

Required fields:

- `source_id`
- `project_id`
- `source_type`
- `discipline`
- `file_hash`
- `received_at`
- `authority_status`
- `supersedes_source_id`
- `verification_status`

### DrawingRevision

Represents one declared revision of a drawing or model source.

Required fields:

- `revision_id`
- `source_id`
- `drawing_id`
- `revision_code`
- `revision_date`
- `issue_purpose`
- `title_block_revision_text`
- `revision_authority`
- `supersedes_revision_id`
- `effective_status`
- `verification_status`

Possible `issue_purpose` values:

- `CONCEPT`
- `DESIGN_DEVELOPMENT`
- `COORDINATION`
- `TENDER`
- `CONSTRUCTION`
- `AS_BUILT`
- `CLIENT_REVIEW`
- `INTERNAL_REVIEW`
- `UNKNOWN`

Possible `effective_status` values:

- `RECEIVED`
- `UNDER_REVIEW`
- `APPROVED_FOR_STAGE`
- `SUPERSEDED`
- `WITHDRAWN`
- `CONFLICT`

### ProjectStage

Represents a human-approved business/design stage that may be bound to one or more approved revision sets.

Required fields:

- `stage_id`
- `project_id`
- `stage_name`
- `stage_sequence`
- `baseline_revision_set_id`
- `started_at`
- `approved_at`
- `approved_by`
- `status`

`baseline_revision_set_id` is nullable while the stage is being created. A `ProjectStage` may be created first as `DRAFT`; only after the compatible `RevisionSet` is approved may the stage baseline be assigned. A `RevisionSet.stage_id` may also be nullable while compatibility is being evaluated. This prevents a bootstrap cycle between stage creation and revision-set creation.

Possible statuses:

- `DRAFT`
- `REVIEW`
- `APPROVED`
- `SUPERSEDED`
- `CONFLICT`

### RevisionSet

A controlled set of compatible revisions used together for one project state or stage candidate.

Required fields:

- `revision_set_id`
- `project_id`
- `stage_id`
- `included_revision_ids`
- `discipline_coverage`
- `compatibility_status`
- `created_at`
- `approved_at`

`stage_id` is nullable for candidate revision sets. A revision set may be approved as a project-state boundary without automatically creating or promoting a new project stage.

Possible `compatibility_status` values:

- `VALID`
- `PARTIAL`
- `CONFLICT`
- `STALE`
- `UNKNOWN`

### ProjectStateSnapshot

Immutable normalized DIOS state produced from one revision set.

Required fields:

- `snapshot_id`
- `project_id`
- `stage_id`
- `revision_set_id`
- `scene_graph_hash`
- `created_at`
- `validation_status`
- `supersedes_snapshot_id`

`stage_id` is nullable for candidate snapshots. A snapshot becomes an approved stage baseline only through a separate human-approved stage decision.

### RevisionChangeSet

Represents differences between two project state snapshots.

Required fields:

- `change_set_id`
- `project_id`
- `stage_id`
- `from_snapshot_id`
- `to_snapshot_id`
- `from_revision_set_id`
- `to_revision_set_id`
- `created_at`
- `change_count`
- `validation_status`
- `approval_status`

`stage_id` is nullable when a change set compares a candidate snapshot that has not yet been attached to an approved project stage.

## 3. Revision boundary rule

A new authoritative revision creates a candidate project state. It does not overwrite history and does not automatically create or promote a new `ProjectStage`.

```text
Revision R1
→ RevisionSet RS1
→ Snapshot S1

Revision R2
→ candidate RevisionSet RS2
→ candidate Snapshot S2
→ ChangeSet S1→S2
→ approval decision
→ approved Snapshot S2, optional explicit stage transition

Revision R3
→ candidate RevisionSet RS3
→ candidate Snapshot S3
→ ChangeSet S2→S3
```

DIOS does not overwrite `S1` when `R2` arrives. It preserves both states and records the transition.

Every downstream artifact must reference the full canonical context tuple:

- `project_id`
- `stage_id`
- `revision_set_id`
- `snapshot_id`
- source drawing and revision evidence

`scene_state_revision` is not part of the canonical context tuple. It is local state for a working representation such as SketchUp.

## 4. Change classification

Each change between snapshots must be classified by semantic source/change event. Downstream impact is recorded separately.

Initial semantic change classes:

- `OBJECT_ADDED`
- `OBJECT_REMOVED`
- `OBJECT_GEOMETRY_CHANGED`
- `OBJECT_MOVED`
- `OBJECT_RECLASSIFIED`
- `PROPERTY_CHANGED`
- `MATERIAL_CHANGED`
- `OPENING_ADDED`
- `OPENING_REMOVED`
- `ROOM_BOUNDARY_CHANGED`
- `ROOM_IDENTITY_CHANGED`
- `LEVEL_CHANGED`
- `SYSTEM_RELATION_CHANGED`
- `ANNOTATION_CHANGED`
- `QUANTITY_RULE_CHANGED`
- `DERIVED_REPRESENTATION_CHANGED`
- `COORDINATION_CONFLICT`
- `UNKNOWN_CHANGE`

`VISUALIZATION_ONLY_CHANGE` is not source geometry authority. If retained by an implementation for compatibility, it must be treated as `DERIVED_REPRESENTATION_CHANGED` and must not change canonical source geometry, dimensions, quantities or revision authority.

Each change record must include:

- affected object IDs;
- previous and new values;
- source revision evidence;
- page/sheet/zone or model location;
- detected-by method;
- confidence;
- validation status;
- approval status;
- `quantity_impact`, `visualization_impact` and `coordination_impact` as downstream impact dimensions.

## 5. Object continuity across revisions

Stable physical objects keep the same `object_id` across revisions when their identity remains valid.

Examples:

- a wall moved by 100 mm remains the same object with a geometry change;
- a door type changed remains the same object with a property change;
- a removed wall keeps its historical identity and gains a removed state;
- a new wall receives a new object ID;
- one wall split into two requires an explicit split relation;
- two objects merged require an explicit merge relation.

Required continuity relations:

- `UNCHANGED`
- `MODIFIED`
- `ADDED`
- `REMOVED`
- `SPLIT_FROM`
- `MERGED_FROM`
- `REPLACED_BY`
- `IDENTITY_UNCERTAIN`

DIOS must not silently assign a new object ID when continuity can be established, and must not silently reuse an ID when identity is uncertain.

## 6. Revision authority

Authority is explicit per source and discipline.

Examples:

- PDF may be revision authority for issued architectural drawings;
- DXF/DWG may be the preferred geometry source but not automatically the revision authority;
- IFC may be authoritative for selected model content but stale for another discipline;
- schedules or specifications may override object properties without overriding geometry;
- marked-up review PDFs are review artifacts, not automatically authoritative revisions.

Each normalized fact therefore stores:

- `source_id`
- `revision_id`
- `authority_scope`
- `data_class`
- `verification_status`

## 7. Mixed-discipline revision sets

Projects often receive architectural, structural and MEP revisions at different times.

DIOS must build explicit revision sets rather than assume that the latest file from every discipline is mutually compatible.

Example:

```text
Project Stage P4
├─ Architecture A-07
├─ Structure S-05
├─ HVAC M-03
└─ Electrical E-04
```

The set is valid only after compatibility review.

Possible conflicts:

- architecture opening changed but structure still references the prior wall;
- reflected ceiling plan updated but lighting schedule is older;
- room numbers changed in architecture but MEP tags still use old room IDs;
- DXF geometry is newer than the issued PDF but not approved as revision authority.

Conflicting revision sets must not feed final quantities or final visualization without an explicit review decision.

## 8. Stage baseline and stale propagation

When a new revision is accepted:

1. DIOS creates a new revision record.
2. It determines whether the revision supersedes an existing revision.
3. It builds or updates a candidate revision set.
4. It reconstructs the normalized candidate project state.
5. It compares the candidate snapshot with the previous approved snapshot.
6. It creates a change set.
7. It marks dependent artifacts stale where affected.
8. It requires review and approval.
9. It records the approved snapshot or rejection.
10. It creates or promotes a project stage only when there is a separate explicit human-approved stage decision.

Dependent artifacts may include:

- visualization scenes;
- SketchUp working models;
- measurements and quantities;
- marked-up review PDFs;
- issue reports;
- room inventories;
- asset assignments;
- exports.

Stale statuses:

- `CURRENT`
- `POTENTIALLY_STALE`
- `STALE`
- `REVALIDATION_REQUIRED`
- `BLOCKED_BY_CONFLICT`

## 9. Visualization consumption rule

The visualization module consumes one explicit `ProjectStateSnapshot`.

```text
Approved ProjectStateSnapshot
→ visualization representation
→ preview/render/animation
```

It may not independently combine geometry from one revision with object placement or properties from another revision.

Each visualization artifact must record:

- `project_id`
- `stage_id`
- `revision_set_id`
- `snapshot_id`
- renderer and adapter versions;
- asset versions;
- camera/style configuration;
- validation status.

When the source snapshot is superseded, the visualization becomes stale. It may remain visible for historical comparison but cannot be presented as the current project state.

## 10. SketchUp integration rule

The SketchUp working model stores:

- `project_id`
- `stage_id`
- `revision_set_id`
- `snapshot_id`
- `source_revision`
- `scene_state_revision`

Before any mutation, the Bridge verifies that the open model matches the command target full canonical context tuple.

Mismatch examples:

- command targets snapshot S5 but model contains S4;
- model has local unapproved changes after the last sync;
- architecture revision matches but structural baseline differs;
- the model was copied from another project or stage.

Any mismatch returns `REVISION_MISMATCH` or `CONTEXT_MISMATCH` and blocks mutation. A matching `scene_state_revision` alone is never sufficient.

## 11. Historical comparison

DIOS must support side-by-side and overlay comparison of approved stages.

Examples:

- concept versus coordinated design;
- tender versus construction issue;
- construction issue versus as-built;
- previous revision versus current revision;
- approved state versus local SketchUp proposal.

Comparison views are derived artifacts. They never merge stages into a new canonical state.

## 12. Minimum validation rules

- revision codes are not assumed unique across drawings;
- a revision belongs to one drawing/source lineage;
- supersession relations must be explicit;
- no source revision may be silently replaced;
- no project snapshot may combine incompatible revisions;
- every normalized object references source evidence;
- every quantity references one snapshot and revision set;
- every visualization references one snapshot and revision set;
- every change set has explicit from/to snapshots;
- unresolved identity changes remain `IDENTITY_UNCERTAIN`;
- revision conflicts block final downstream artifacts;
- historical snapshots remain immutable;
- every mutable connector command/result/registration carries `project_id`, `stage_id`, `revision_set_id` and `snapshot_id`;
- no project stage is created or promoted without explicit human approval.

## 13. Architectural principle

```text
Revision defines the boundary.
Snapshot captures the project state at that boundary.
ChangeSet explains the transition between boundaries.
ProjectStage gives the approved business/design meaning of that state.
```

The DIOS core owns revisions, snapshots, object continuity and change classification. Visualization, Aufmass and other modules consume approved snapshots and report derived results back against the same revision context.