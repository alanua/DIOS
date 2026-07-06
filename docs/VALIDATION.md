# Validation Strategy

Status: `PRE-ALPHA`

## Mandatory checks

- source document and revision identity;
- declared and verified units;
- scale proof from an explicit control dimension;
- plan, section, detail, schedule and legend consistency;
- duplicate and omission detection;
- legend instances excluded from installed counts;
- formula and subtotal reconciliation;
- original and normalized unit consistency;
- alternative-method comparison where possible;
- stale-state propagation after source revision changes.

## Review rules

A result remains `NEEDS_REVIEW` when:

- dimensions are missing;
- scale is unverified;
- geometry is inferred;
- views disagree;
- source revision is uncertain;
- the method uses a parametric allowance;
- the result has safety, design or contractual consequences.

## Benchmark fixtures

Public tests should use synthetic or openly licensed drawings with exact ground truth for:

- symbol counts;
- route lengths;
- closed areas;
- opening deductions;
- room topology;
- wall surfaces;
- revision differences;
- plan/section reconciliation.