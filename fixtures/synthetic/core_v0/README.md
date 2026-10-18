# DIOS Core v0 synthetic fixture suite

Status: `PUBLIC_SAFE / SYNTHETIC_ONLY / PRE_FREEZE`

This suite exists to test cross-record invariants that JSON Schema cannot enforce by itself. It contains no real project geometry, addresses, customer data, third-party product names, source transcripts, or provider-specific implementation semantics.

## Coverage

`fixture_suite.json` contains exactly sixteen declared scenarios:

1. two immutable revisions of one synthetic sheet;
2. one exact revision set and one matching technical snapshot;
3. stable one-to-one entity continuity;
4. contradictory one-to-one, split, and merge continuity claims;
5. explicit control-dimension scale verification;
6. rejection of a scale-required measurement with unverified scale;
7. room, wall, and opening measurements with method, formula, unit, scale, and evidence;
8. architectural/structural geometry conflict beyond tolerance;
9. two representations of one physical object counted once;
10. legend sample excluded from installed count;
11. semantic label/entity-class mismatch;
12. unit/scale mismatch producing implausible magnitude;
13. measurement left current after its revision set changed;
14. quantity missing calculation plan and result unit;
15. derivative artifact attempting technical-authority promotion;
16. two modules extending one stable technical entity without identity duplication.

## Execution

```text
python -m unittest discover -s tests/contracts -v
```

The data-driven evaluator in `tests/contracts/test_synthetic_core_v0.py` checks expected validity and exact failure codes. Valid cases must emit no violation. Invalid cases must emit the declared bounded code set.

## Boundaries

- This is not a production validation engine.
- Fixture data is intentionally compact and does not replace full JSON Schema instance fixtures.
- A passing synthetic suite does not authorize production persistence, source ingestion, CAD/BIM integration, or production Aufmaß.
- Discipline-specific plausibility limits remain profile rules, not universal DIOS Core constants.
- Skeleton-owned approvals, users, roles, workflows, audit, storage, and runtime records are represented only by stable references where needed.

## Required follow-up after architecture freeze

- replace compact fixture records with schema-valid complete record packets;
- add canonical serialization and hash-replay fixtures;
- add graph traversal for stale propagation;
- add module-manifest extension fixtures;
- add mutation tests proving each prohibited case fails for the intended reason;
- keep all fixtures public-safe and synthetic.
