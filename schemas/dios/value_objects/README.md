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

## Hard rules

- Confidence never replaces evidence or verification.
- A source may have different authority kinds for different scopes.
- Every evidence location binds to one immutable technical source revision.
- Screenshots, generated visuals, chat messages, and exports are not geometry or quantity authority.
- Deterministic receipts record exact method version, input/output hashes, operation order, units, and replay state.
- Domain records reference Skeleton-owned records by stable identifier instead of redefining them.

These files are draft inputs to DIOS issues #9, #15, and #16. They are not frozen schemas and must not be used for production persistence or real-project ingestion.
