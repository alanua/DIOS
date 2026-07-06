# Aufmaß Method

Status: `PRE-ALPHA`

## Workflow

1. Register source package, document, revision and issue status.
2. Detect sheets, title blocks, units, scales and drawing zones.
3. Verify scale using an explicit control dimension.
4. Link plan, section, elevation, detail, schedule and legend views.
5. Build object and relationship records.
6. Create a measurement plan before calculating quantities.
7. Run deterministic length, area, volume, count or weight calculations.
8. Cross-check totals, revisions, units, duplicate instances and missing objects.
9. Route assumptions and conflicts to review.
10. Export structured records and marked-up evidence.

## Measurement classes

- `EXPLICIT_SOURCE_VALUE`
- `COUNT_INSTANCE`
- `LINEAR_MEASUREMENT`
- `AREA_MEASUREMENT`
- `VOLUME_MEASUREMENT`
- `WEIGHT_CALCULATION`
- `PARAMETRIC_ALLOWANCE`
- `INFERRED_GEOMETRY`

## Data classes

- `EXPLICIT`
- `CALCULATED`
- `INFERRED`
- `UNKNOWN`

## Verification states

- `VERIFIED`
- `NEEDS_REVIEW`
- `CONFLICT`
- `NOT_FOUND`

## Required evidence

Every quantity should include document, revision, sheet, page, zone or coordinates, method, formula, units, assumptions and review state.