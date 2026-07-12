# DIOS Core v0.1 shared value objects

Status: `DRAFT / PRE-FREEZE / SYNTHETIC-ONLY`

These schemas define reusable primitives for DIOS domain contracts. They do not create a second platform identity, artifact registry, approval system, audit log, command envelope, node/session model, or canonical memory store. Those concerns remain owned by Skeleton.

## Schemas

- `identifier.schema.json` — opaque stable identifiers and external references
- `semantic_version.schema.json` — SemVer 2.0.0 values
- `verification_status.schema.json` — verified/review/conflict/not-found state
- `data_class.schema.json` — explicit/calculated/inferred/unknown origin
- `privacy_class.schema.json` — public/internal/private/restricted handling
- `content_hash.schema.json` — algorithm-qualified immutable digest
- `authority_scope.schema.json` — technical authority kind and exact scope
- `lifecycle_reference.schema.json` — immutable lifecycle and supersession links
- `evidence_location.schema.json` — exact source revision and coordinate locator
- `confidence_assessment.schema.json` — confidence separated from verification
- `responsibility_trace.schema.json` — human/model/deterministic responsibility
- `deterministic_receipt.schema.json` — replayable calculation receipt
- `entity_continuity.schema.json` — evidence-backed continue/split/merge/replace/remove/introduce/unresolved relations across exact revision sets
- `measurement_kind.schema.json` — length/area/volume/count/weight family
- `unit_value.schema.json` — numeric value with explicit measurement kind and unit
- `scale_control.schema.json` — verified/not-required/unverified/conflict scale state with evidence
- `calculation_plan.schema.json` — bounded typed operations and human-readable formula; never executable source code
- `validation_outcome.schema.json` — clean pass, pass with findings, failure, or blocked evaluation
- `validation_severity.schema.json` — info/warning/error/blocker finding severity
- `technical_impact.schema.json` — separate semantic, quantity, visual, and coordination impact channels
- `stale_state.schema.json` — current/stale/revalidation-required/blocked/void technical state vocabulary

## Hard rules

- Confidence never replaces evidence or verification.
- A source may have different authority kinds for different scopes.
- Every evidence location binds to one immutable technical source revision.
- Screenshots, generated visuals, chat messages, and exports are not geometry or quantity authority.
- Deterministic receipts record exact method version, input/output hashes, operation order, units, and replay state.
- Domain records reference Skeleton-owned records by stable identifier instead of redefining them.
- Entity continuity is evidence-backed and context-bound; unresolved continuity blocks silent quantity or property carry-forward.
- Split and merge relations are explicit and may not be collapsed into one-to-one identity guesses.
- Scale status is explicit. `VERIFIED` requires evidence and a positive scale factor; `UNVERIFIED` and `CONFLICT` cannot pass a scale-required method.
- Unit conversion is explicit. Original and normalized values remain separate.
- Calculation plans contain only the bounded `DIOS_TYPED_OPS_V1` operation vocabulary and declared parameters.
- A calculation plan has an immutable hash; arbitrary scripts, macros, shell commands, or source-code payloads are outside this contract.
- Validation outcome is separate from verification status: the result can be verified as a failure or blocker.
- `PASS` has no findings; `PASS_WITH_WARNINGS`, `FAIL`, and `BLOCKED` require at least one structured finding.
- Semantic, quantity, visual, and coordination impacts are assessed independently; one channel never implies another.
- Stale state is explicit and append-only. Invalidation never deletes or silently rewrites prior records.

These files are draft inputs to DIOS issues #9, #15, and #16. They are not frozen schemas and must not be used for production persistence or real-project ingestion.
