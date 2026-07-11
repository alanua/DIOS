# DIOS Core v0.1 domain contracts

Status: `DRAFT / PRE-FREEZE / SYNTHETIC-ONLY`

This directory contains DIOS-specific domain schemas. Generic project identity, artifact storage, approvals, audit, node/session state, command transport, and canonical memory remain owned by Skeleton and are referenced by stable identifiers.

## Source-state chain

```text
Skeleton ArtifactRecord / ArtifactRevision
→ TechnicalSourceRevision
→ RevisionSet
→ TechnicalSnapshot
```

## Entity-evidence chain

```text
TechnicalEntity
→ EntityRepresentation
→ EvidenceLocation
→ Observation
→ validation / measurement / decision
```

Entity continuity across revision sets is represented by addressable evidence-backed graph edges rather than duplicated identity fields inside entities.

## Measurement-quantity chain

```text
active MeasurementMethod
→ exact RevisionSet / TechnicalSnapshot
→ selected TechnicalEntity representations
→ evidence and scale control
→ deterministic MeasurementRecord
→ accepted input measurements
→ deterministic QuantityRecord
```

## Contracts

- `technical_source_revision.schema.json` attaches technical source class, exact content hash, authority scopes, document inventory, verification, privacy, and lifecycle to one immutable Skeleton artifact revision.
- `revision_set.schema.json` pins the exact source revisions and hashes used for one interpretation. Membership is immutable after activation.
- `technical_snapshot.schema.json` records one reviewed technical state bound to one revision-set hash. It does not create or promote a project stage.
- `technical_entity.schema.json` owns stable domain identity without embedding provider geometry or document coordinates.
- `entity_representation.schema.json` records one source occurrence through one exact `EvidenceLocation`; duplicate source fields are intentionally not repeated.
- `observation.schema.json` records an evidence-backed claim tied to one revision set, responsibility trace, data class, and verification state.
- `value_objects/entity_continuity.schema.json` records continue, split, merge, replace, remove, introduce, and unresolved-match relations across exact revision sets.
- `measurement_method.schema.json` defines one immutable method version, scale requirement, unit policy, representation selection, duplicate handling, deductions, typed calculation plan, and validation fixtures.
- `measurement_record.schema.json` records one result with exact source context, method version/hash, selected representations, evidence, scale state, formula, adjustments, values, deterministic receipt, and validation references.
- `quantity_record.schema.json` aggregates only active verified measurements under a typed calculation plan and explicit scope. It is not an estimate, price, invoice, or payment-entitlement record.

## Hard rules

- A revision label, filename, timestamp, or file format does not grant authority automatically.
- Authority is typed and scoped: revision, geometry, semantic, property, measurement input, or reference only.
- The same source may hold different authority kinds for different scopes.
- A revision set pins both revision identity and immutable content hash.
- Conflicts are recorded; no `last-write-wins` rule is allowed.
- An active technical snapshot requires validation references, a Skeleton approval reference, and `VERIFIED` status.
- Supersession creates a new immutable record; accepted records are not edited in place.
- `project_stage_ref` is optional and never created or promoted by these schemas.
- Technical entity identity is separate from every drawing/model representation.
- Legend samples, annotations, and references are not installed physical instances.
- `EvidenceLocation` is the single source binding for a representation; duplicate top-level source fields are prohibited.
- Observations bind to a `RevisionSet`, and every evidence location must resolve to one of its members.
- Inferred observations require an explicit confidence assessment.
- Unresolved continuity blocks silent property, measurement, and quantity carry-forward.
- A measurement method is immutable by version and hash. Active methods require reviewed fixtures and a Skeleton approval reference.
- Scale-required methods reject `UNVERIFIED` or `CONFLICT` scale state. A declared drawing scale alone is not sufficient unless the method policy explicitly allows it.
- Original, working, result, and normalized units are explicit; conversion must be declared and replayable.
- Formula and operation order are represented as bounded typed data, not generated executable code.
- Deductions and corrections require their own subject reference, formula, value, and evidence.
- Duplicate physical objects are resolved by `TechnicalEntity`, not by counting every representation.
- A quantity aggregates active verified measurement records only and requires a deterministic receipt.
- Active quantities require validation references, `VERIFIED` status, and a Skeleton approval reference.
- Quantity records contain no commercial price, cost, invoice, payment, entitlement, or design-approval semantics.

## Known custom invariants

The following require invariant tests in addition to JSON Schema:

- no duplicate `technical_source_revision_id` values inside one revision set;
- canonical revision-set hash calculation from normalized member data;
- project-context equality across all members and the parent revision set;
- referenced content hashes must match registered artifact revisions;
- lifecycle transitions are append-only and auditable;
- active snapshot validation and approval references must resolve to compatible contexts;
- every representation evidence location must resolve to the same project context as its entity;
- every observation evidence location must belong to its declared revision set;
- continuity edges must not form contradictory one-to-one and split/merge claims for the same context pair;
- duplicate physical-object detection must operate across representations, not by source occurrence count;
- calculation operation sequence values are unique, contiguous, and replayed in order;
- every operation input reference resolves to an earlier input or output;
- measurement kind is consistent across method, gross value, adjustments, result, normalized value, and quantity;
- method hash and version resolve to the exact active method used by the record;
- scale control satisfies the referenced method requirement;
- unit conversions are approved, dimensionally compatible, and preserve original values;
- result value equals gross value plus signed adjustments under the declared formula and operation order;
- deterministic receipt input/output hashes match canonical serialized inputs and outputs;
- active measurement references one compatible snapshot and at least one valid validation result;
- every quantity input measurement is active, verified, in the same revision set/snapshot, and used at most once after entity deduplication;
- quantity result equals replay of its typed calculation plan over the exact accepted inputs;
- implausible magnitude checks are discipline/profile rules and cannot be inferred from schema shape alone.

These contracts are draft inputs to issues #9, #15, and #16 and must not be used for production persistence or real-project ingestion before architecture freeze.
