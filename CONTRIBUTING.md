# Contributing

DIOS welcomes focused contributions to public-safe models, schemas, adapters, deterministic calculations, documentation, synthetic fixtures, and tests.

## Public-safe inputs only

Use synthetic fixtures or redistributable public examples. Do not contribute real customer drawings, private project packages, proprietary exports, credentials, or private CAD application state.

## Correctness rules

- do not invent missing dimensions;
- preserve exact source/revision references;
- keep original and normalized units distinct;
- require scale validation before measurement;
- distinguish explicit, calculated, inferred, conflict, and unknown states;
- add tests for failure/ambiguity paths, not only happy paths.

## Application bridges

External CAD integrations are security-sensitive. Prefer read-only inspection first. Write-capable operations must be typed, bounded, reviewable, and separately authorized; arbitrary macros or hidden application-state mutation are out of scope for normal contributions.

## Skeleton boundary

Skeleton provides shared execution, approval, audit, secret, and private-memory infrastructure. DIOS owns technical drawing/evidence/measurement semantics. Do not duplicate generic platform authority inside DIOS.

## License status

No open-source license has been selected for this repository yet. Do not add or change a repository license without an explicit maintainer decision.
