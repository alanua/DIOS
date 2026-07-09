# DIOS Revision Register

Status: `DESIGN / ARCHITECTURE CANDIDATE / NOT PRODUCTION`

## 1. Purpose

DIOS must generate a structured revision register that answers two questions:

1. When did a project state change?
2. What exactly changed at that revision boundary?

The revision register is a derived view over source revisions, approved revision sets, project-state snapshots and classified change sets.

It is not the canonical source of geometry. It is the traceable history of how the canonical project state evolved.

## 2. Two linked registers

DIOS maintains two linked views.

### 2.1 Source Revision Register

One row per received drawing/model revision.

Required fields:

- `project_id`
- `drawing_id`
- `discipline`
- `source_id`
- `revision_id`
- `revision_code`
- `revision_date`
- `received_at`
- `analyzed_at`
- `issue_purpose`
- `title_block_revision_text`
- `revision_authority`
- `supersedes_revision_id`
- `effective_status`
- `verification_status`
- `file_hash`

This register establishes when a revision was issued, when DIOS received it and when it was analyzed. These timestamps must not be conflated.

### 2.2 Revision Change Register

One row per classified project change detected between two approved or candidate snapshots.

Required fields:

- `change_id`
- `change_set_id`
- `project_id`
- `stage_id`
- `from_snapshot_id`
- `to_snapshot_id`
- `from_revision_set_id`
- `to_revision_set_id`
- `trigger_revision_id`
- `change_date`
- `change_class`
- `discipline`
- `drawing_id`
- `sheet_or_view_id`
- `page_or_model_location`
- `zone_or_coordinates`
- `object_id`
- `related_object_ids`
- `before_value`
- `after_value`
- `change_summary`
- `quantity_impact`
- `visualization_impact`
- `coordination_impact`
- `evidence_reference`
- `data_class`
- `confidence`
- `verification_status`
- `approval_status`

The full canonical context tuple is `project_id`, `stage_id`, `revision_set_id` and `snapshot_id`. Change rows carry the tuple through `project_id`, from/to revision sets and from/to snapshots; `stage_id` may be nullable while a candidate change set has not yet been attached to an approved project stage.

## 3. Meaning of the date fields

The register distinguishes:

- `revision_date`: date declared by the issuer in the drawing/model revision;
- `received_at`: when the file entered DIOS;
- `analyzed_at`: when DIOS completed extraction/comparison;
- `approved_at`: when a human approved the revision set, snapshot or project stage;
- `change_date`: normally the authoritative revision date that introduced the change.

If the revision date is missing or conflicting, `change_date` remains unknown until resolved. DIOS must not substitute the upload date silently.

## 4. Revision summary row

Each revision has a summary record.

Example structure:

```text
Revision: A-08
Date: 2026-04-18
Purpose: COORDINATION
Supersedes: A-07
Affected drawings: A-101, A-203, A-601
Detected changes: 24
Added: 4
Removed: 2
Modified: 18
Quantity-impacting changes: 7
Coordination conflicts: 3
Status: UNDER_REVIEW
```

The summary is calculated from detailed change rows. It must never replace the detailed evidence.

## 5. Change content

The register records not only that a sheet changed, but what changed semantically.

Examples:

- wall W-104 moved 120 mm east;
- door D-023 width changed from 900 mm to 1000 mm;
- opening O-017 added in structural wall S-W-08;
- room R-2.14 boundary increased by 3.2 m²;
- sanitary object WC-03 removed;
- lighting type L-07 replaced by L-12;
- stair flight geometry changed;
- room number changed while physical room identity remained stable;
- quantity rule changed from net to gross area basis;
- sheet annotation changed without geometry impact;
- new architectural revision conflicts with the current structural baseline;
- derived visualization scene changed without source-geometry authority.

## 6. Evidence classes

Each change row states how it was established.

Allowed evidence classes:

- `EXPLICIT_REVISION_NOTE`
- `EXPLICIT_REVISION_CLOUD`
- `EXPLICIT_DELTA_SYMBOL`
- `DETECTED_GEOMETRY_DIFF`
- `DETECTED_PROPERTY_DIFF`
- `INFERRED_OBJECT_MATCH`
- `MARKETING_OR_PRESENTATION_ONLY`
- `CONFLICT`
- `UNKNOWN`

A revision note is not sufficient evidence that all listed changes are complete. DIOS compares the actual project-state snapshots independently.

Demonstrations, screenshots, marketing outputs and presentation renders may inspire tests or review prompts, but they are not verified technical evidence unless backed by source revisions, deterministic comparison, provenance and review.

## 7. Change classification

Initial semantic change classes:

- `OBJECT_ADDED`
- `OBJECT_REMOVED`
- `OBJECT_MOVED`
- `OBJECT_GEOMETRY_CHANGED`
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

`quantity_impact`, `visualization_impact` and `coordination_impact` are downstream impact dimensions. They are not semantic source/change classes. A visualization-only edit must be treated as a derived-representation change and must not promote a presentation artifact to geometry, quantity or revision authority.

## 8. Impact flags

Each change is assessed for downstream impact.

### Quantity impact

Possible values:

- `NONE`
- `POSSIBLE`
- `CONFIRMED`
- `RECALCULATION_REQUIRED`
- `UNKNOWN`

### Visualization impact

Possible values:

- `NONE`
- `STYLE_ONLY`
- `SCENE_UPDATE_REQUIRED`
- `ASSET_UPDATE_REQUIRED`
- `FULL_REBUILD_REQUIRED`
- `UNKNOWN`

### Coordination impact

Possible values:

- `NONE`
- `LOCAL`
- `CROSS_SHEET`
- `CROSS_DISCIPLINE`
- `BLOCKING_CONFLICT`
- `UNKNOWN`

## 9. Register lifecycle

```text
new revision received
→ source revision row created
→ candidate revision set formed
→ candidate snapshot generated
→ previous/current snapshots compared
→ detailed change rows created
→ revision summary calculated
→ dependent artifacts marked stale
→ human review
→ register rows approved or corrected
→ optional explicit project-stage transition decision
```

A new source revision does not automatically create or promote a new project stage. Stage creation and transition require a separate human-approved decision.

## 10. Historical integrity

The register is append-only at the historical level.

Corrections do not erase prior records. They create:

- corrected classification;
- corrected evidence reference;
- superseding review decision;
- audit entry explaining why the row changed.

Historical project states and original revision records remain immutable.

## 11. Required exports

DIOS should support at least:

- machine-readable JSON revision register;
- compact CSV register;
- Excel review workbook;
- human-readable PDF revision report;
- per-revision change summary;
- object history by stable `object_id`;
- room history by stable `room_id`;
- quantity-impact register;
- unresolved conflict register.

Excel and PDF are review/export artifacts, not canonical storage.

## 12. Example compact register

| Revision | Date | Drawing | Object | Change | Before | After | Impact | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A-08 | 2026-04-18 | A-101 | W-104 | `OBJECT_MOVED` | X=4250 | X=4370 | quantity possible | verified |
| A-08 | 2026-04-18 | A-101 | D-023 | `PROPERTY_CHANGED` | 900 mm | 1000 mm | quantity confirmed | verified |
| A-08 | 2026-04-18 | A-203 | O-017 | `OPENING_ADDED` | absent | present | cross-discipline | needs review |
| A-08 | 2026-04-18 | QTO | AREA-RULE | `QUANTITY_RULE_CHANGED` | net area | gross area | recalculation required | needs review |

## 13. Architectural rule

```text
Revision register answers: when did the boundary change?
Change register answers: what changed across that boundary?
Impact flags answer: what downstream work may be affected?
Object history answers: how did one physical object evolve through the project?
```

The DIOS core produces these registers. Visualization, Aufmass, coordination and export modules consume them and attach their outputs to the same project, stage, revision-set and snapshot context.