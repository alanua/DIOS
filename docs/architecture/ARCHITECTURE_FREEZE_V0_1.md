# DIOS architecture freeze v0.1

Status: `FREEZE_APPROVED_WITH_NON_BLOCKING_GAPS`

Classification: `ARCHITECTURE / PUBLIC_SAFE / DOMAIN_FREEZE / IMPLEMENTATION_GATED`

Decision scope: DIOS drawing-intelligence domain architecture represented by pull request #17 and the architecture decisions recorded in issues #8, #9 and #15.

This decision freezes domain ownership, canonical records, source/revision semantics, evidence, measurement, validation, module boundaries and the first vertical-slice boundary. It does not declare Skeleton shared-platform integration complete and does not authorize production runtime use.

## 1. Verdict

```text
FREEZE_APPROVED_WITH_NON_BLOCKING_GAPS
DOMAIN_ARCHITECTURE_FROZEN
SHARED_PLATFORM_INTEGRATION_PENDING
PRODUCTION_RUNTIME_BLOCKED
```

The remaining gaps are bounded and owned. None requires adding a new DIOS Core capability family or changing the frozen domain boundary. They block production integration or merge hardening, not the architecture decision itself.

## 2. Frozen responsibility boundary

### Skeleton owns

- generic `ProjectContext` identity and access binding;
- users, roles, competence and delegated authority;
- workflow, task, queue and Runner execution;
- generic source/artifact registration, immutable artifact revisions, storage and routing;
- generic approvals and review queues;
- node, workstation, resource, session and transport contracts;
- command/result envelopes, idempotency and replay protection;
- generic audit and correlation records;
- secrets and connectors;
- private canonical-memory gateway;
- generic module identity and lifecycle;
- derivative artifact delivery routing.

### DIOS owns

- technical source-revision extensions and typed authority scopes;
- immutable `RevisionSet` and reviewed `TechnicalSnapshot` semantics;
- stable technical entities and exact source representations;
- observations and evidence locations;
- entity continuity, split, merge, replacement, removal and unresolved matching;
- measurement methods, scale controls, formulas, units and deterministic receipts;
- measurement and quantity records;
- technical validation results;
- detected technical change sets;
- technical invalidation and stale-state propagation;
- drawing-intelligence module extensions and validation rules.

DIOS must not implement duplicate generic platform records while Skeleton gaps remain open.

## 3. Frozen DIOS Core records

```text
TechnicalSourceRevision
RevisionSet
TechnicalSnapshot
TechnicalEntity
EntityRepresentation
Observation
MeasurementMethod
MeasurementRecord
QuantityRecord
TechnicalValidationResult
TechnicalChangeSet
TechnicalInvalidation
```

Supporting value objects and graph edges remain subordinate contracts rather than additional platform services.

Adding, removing or materially redefining a first-class record requires an architecture decision record, compatibility analysis, schema version change and synthetic invariant coverage.

## 4. Frozen source, revision and authority rules

- One immutable Skeleton artifact revision is extended by one DIOS `TechnicalSourceRevision`.
- A filename, timestamp, format or revision label never grants authority automatically.
- Authority is typed and scoped: revision, geometry, semantic, property, measurement input or reference only.
- One source may have different authority kinds for different scopes.
- `RevisionSet` pins exact technical revision identities and content hashes.
- `TechnicalSnapshot` records reviewed technical state and does not create or promote a project stage.
- Conflicts remain explicit; `last-write-wins` is prohibited.
- Supersession creates new immutable records rather than editing accepted records in place.
- Unresolved entity continuity blocks silent property, measurement and quantity carry-forward.
- Derivative review/export artifacts remain `REFERENCE_ONLY` unless separately registered and reviewed as a new source.

## 5. Frozen evidence rules

Every accepted technical result must resolve through an evidence path containing:

```text
result
→ entity or representation
→ exact source revision
→ document, view or zone
→ exact source coordinates or locator
→ observation
→ method, formula and assumptions
→ validation
→ operator decision where required
```

A screenshot, generated visual, chat message, exported spreadsheet or successful API call is not sufficient geometry, measurement or quantity authority.

## 6. Frozen measurement and quantity rules

- No dimension may be invented.
- Revision sets may not be mixed silently.
- Scale requires explicit verified control evidence unless the method declares scale not applicable.
- Units and conversions are explicit.
- Formula operations are bounded typed data, not generated source code.
- Opening and deduction handling is evidence-backed and explicit.
- Duplicate handling is based on stable physical entity identity, not representation count.
- Legend samples, annotations and references are not installed instances.
- Quantities aggregate accepted active verified measurements only.
- Every quantity retains source, revision, coordinates, method, formula, unit, assumptions, confidence and verification status.
- A DIOS quantity is not a price, estimate, invoice, payment entitlement or design approval.

## 7. Frozen validation and stale-state rules

The validation model must detect or block at least:

- source or revision mismatch;
- unverified or conflicting scale;
- missing evidence;
- semantic label-class mismatch;
- duplicate representation risk;
- legend-instance confusion;
- implausible magnitude;
- entity-continuity conflict;
- stale measurements, quantities and derivative artifacts;
- invalid approval context after technical change.

Detected changes do not mutate canonical records. Invalidation is an explicit dependency graph with a required recovery action such as revalidate, remeasure, reaggregate, review continuity, reapprove, regenerate derivative or block use.

## 8. Frozen module boundaries

### Source adapter

Extracts source structure, coordinates, metadata, candidate representations and observations. It cannot assign authority, approve records, mutate canonical sources or emit accepted measurements and quantities.

### Discipline pack

Implements one repeated bounded technical method using DIOS Core contracts. It cannot own generic workflow, approval, storage, provider execution or unrestricted quantity aggregation.

### Application bridge

Uses a provider-neutral public contract and private provider implementation. It is read-only first, exact-resource-bound and limited to typed allowlisted operations. Later mutation requires working-copy or provider-transaction boundaries, explicit approval and post-operation validation. Original source mutation, arbitrary generated code, unbounded macros and hidden provider-state mutation are prohibited.

### Output adapter

Creates derivative review or exchange artifacts. Output authority remains `REFERENCE_ONLY`; canonical write and source-authority promotion are prohibited.

### ProjectProfile

Privately selects approved modules and policies by reference. It cannot redefine Core, authority, evidence, measurement or approval semantics.

## 9. Synthetic validation baseline

The public-safe harness contains sixteen declared scenarios covering revisions, snapshots, continuity, scale, architectural measurements, structural conflict, duplicate representation, legend exclusion, semantic mismatch, implausible magnitude, stale propagation, invalid quantity, derivative authority promotion and shared entity identity across modules.

This harness is the minimum regression baseline. Later implementation may extend it but may not weaken or remove these invariants without architecture review.

## 10. Non-blocking gaps

### Skeleton shared-platform contracts

The following remain partial or missing and are owned by Skeleton:

- rich runtime `ProjectContext` extension attachment;
- reusable roles, competence and delegated-authority contracts;
- generic `ApprovalDecision` and `ReviewQueue`;
- immutable generic `ArtifactRecord` and `ArtifactRevision` with exact private read receipts;
- unified append-only audit/correlation reference;
- generic module-manifest identity and lifecycle;
- generic invalidation attachment hook;
- derivative export registration and delivery receipts.

### Deferred integration capabilities

- workstation/node/resource/session architecture remains specification-level;
- live MemoryGateway ownership remains pending;
- write-capable application bridges remain prohibited;
- full production-shaped packets, canonical serialization/hash replay, graph traversal and mutation testing remain hardening work;
- external Draft 2020-12 meta-schema validation for all module schemas remains a pre-merge hardening item.

These gaps must be solved by extension or integration. They must not be copied into DIOS Core.

## 11. First post-freeze vertical slice

The first bounded vertical slice remains:

```text
architectural room / wall / opening measurement
+ structural geometry cross-check
```

It must begin from registered authoritative source revisions, explicit scale control, stable entity identity, evidence-backed measurements, deterministic receipts, technical validation and human review before derivative export.

Legacy production outputs may be used only as diagnostic evidence or synthetic failure fixtures. They are not canonical input.

## 12. Actions authorized by this freeze

- finalize and review the public contract packet;
- merge it only after separate explicit operator approval and exact-head review;
- correct stale Skeleton DIOS project metadata;
- define bounded Skeleton follow-up contracts for the identified shared gaps;
- prepare synthetic and controlled implementation slices using the frozen contracts;
- specify the first vertical slice without ingesting real production data.

## 13. Actions not authorized

- production Aufmaß rebuild;
- migration of legacy quantities into canon;
- real customer drawing ingestion into public routes;
- production persistence or deployment;
- live MemoryGateway publication;
- write-capable CAD/BIM/application integration;
- provider-specific public architecture;
- merge, deployment or runtime activation without their own explicit gates.

## 14. Change control

After this decision, the following require a new reviewed architecture decision:

- change of Skeleton/DIOS ownership;
- new first-class DIOS Core record;
- weakening of revision, authority, evidence or scale rules;
- new automatic canonical-write path;
- new application mutation class;
- removal of a frozen synthetic invariant;
- expansion of the first vertical slice beyond its stated boundary.

Implementation details that preserve these contracts may evolve through normal versioned schema and code review.

## 15. Final decision

```text
Architecture outputs complete: 10 / 10
Architecture verdict: FREEZE_APPROVED_WITH_NON_BLOCKING_GAPS
Domain implementation contracts: eligible for final review
Production integration: blocked pending shared prerequisites and separate approval
```
