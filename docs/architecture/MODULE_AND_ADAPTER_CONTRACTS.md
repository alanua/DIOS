# DIOS module and adapter contracts

Status: `ARCHITECTURE CANDIDATE / PRE-FREEZE / PUBLIC-SAFE`

## Boundary

DIOS modules extend Skeleton-owned module, workflow, artifact, approval, audit, node/session and execution services. They do not create replacements for those services.

```text
Skeleton module manifest and execution services
→ DIOS module-manifest extension
→ one bounded module-class contract
→ DIOS Core records and validations
→ Skeleton review/approval
→ derivative output where applicable
```

Provider-specific names, credentials, API details and private project configuration remain outside public contracts.

## Module classes

### Source adapter

Purpose: extract source structure, coordinates, metadata, candidate representations and observations from one registered immutable artifact revision.

May produce:

- source metadata;
- document inventory;
- coordinate frames;
- text fragments;
- vector primitives;
- model references;
- candidate representations;
- observations.

Must not produce or assign:

- accepted measurements;
- quantities;
- approval decisions;
- source authority;
- canonical source mutation.

Every adapter declares supported source/format versions, coordinate and unit behavior, stage responsibility, known information loss, validation fixtures and stable failure codes.

### Discipline pack

Purpose: implement one repeated bounded technical method using DIOS Core entities, observations, measurement methods and validation contracts.

A pack may produce observations, measurements, technical validations, detected changes and invalidations. Shared quantity aggregation remains a DIOS Core outcome over accepted measurements rather than pack-owned commercial takeoff logic.

A pack must declare:

- included and excluded operations;
- method references;
- entity and observation requirements;
- human/model/deterministic responsibility boundaries;
- validation and review gates;
- promotion evidence beyond one demonstration or pilot.

### Application bridge

Purpose: expose a private application API through a provider-neutral typed public contract.

Rules:

- read-only first;
- exact resource/revision binding;
- Skeleton-owned resource/session transport;
- typed allowlisted operations only;
- structured input/output schemas;
- idempotency, cancellation and replay protection;
- evidence and responsibility receipts;
- post-operation validation;
- working-copy or provider transaction boundary for any later mutation;
- original source mutation prohibited.

Arbitrary generated source code, unbounded macros, hidden state mutation and primary mouse automation are outside the contract.

### Output adapter

Purpose: generate review and exchange derivatives from accepted records.

Supported classes include marked-up PDF, CSV, XLSX, JSON, evidence packets, review reports and approved neutral exchange packages.

All outputs are classified as derivative and `REFERENCE_ONLY`. Output generation cannot write canonical technical state or promote an export to revision, geometry, measurement or quantity authority.

### ProjectProfile

A private `ProjectProfile` selects approved module-manifest extensions and binds project-specific authority, validation, approval, export and private-source references.

It may hold references to private configuration artifacts and secrets through Skeleton. It cannot redefine module contracts, source identity, evidence semantics, measurement rules or approval records.

## Shared failure declaration

Every module declares stable failure codes with:

- category;
- severity;
- retryability;
- downstream blocking effect;
- evidence requirement;
- recovery guidance.

Failures do not silently downgrade into warnings. A blocking authority, revision, evidence, scale, unit or privacy failure prevents acceptance of downstream records.

## Promotion gate

A candidate becomes a module only after:

```text
defined DIOS problem
→ repeated use case
→ evidence beyond marketing or one demo
→ Skeleton/Core non-duplication review
→ explicit human/AI/deterministic boundary
→ validation and failure design
→ synthetic fixture
→ private pilot where appropriate
→ architecture review
```

Research notes, experiments and private provider bridges are not public module identities by default.

## Initial post-freeze candidates

```text
Source adapters
- PDF/raster source adapter
- vector drawing source adapter

Discipline packs
- architectural room/wall/opening measurement
- structural geometry cross-check

Output adapters
- marked-up review PDF
- structured quantity export
```

Application bridges remain later evidence-dependent candidates and begin read-only.

## Contract files

- `schemas/modules/dios_module_manifest_extension.schema.json`
- `schemas/modules/source_adapter_contract.schema.json`
- `schemas/modules/discipline_pack_contract.schema.json`
- `schemas/modules/application_bridge_contract.schema.json`
- `schemas/modules/output_adapter_contract.schema.json`
- `schemas/modules/project_profile.schema.json`
- `schemas/modules/failure_declaration.schema.json`

These contracts are inputs to DIOS issues #8, #15 and #16. They remain non-production until architecture freeze and final contract review.
