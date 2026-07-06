# DIOS

Drawing Intelligence Operating System for structured analysis of construction and technical drawings.

Status: `PRE-ALPHA`

## Goals

- drawing intake and revision control
- sheet, unit and scale extraction
- geometry, symbol and text analysis
- length, area, volume, count and weight calculations
- conflict and completeness checks
- reviewable Aufmass records
- structured exports

## Principles

- do not invent missing dimensions
- preserve exact source references
- keep original and normalized units separately
- verify scale before measurement
- prefer deterministic calculations
- separate explicit, calculated, inferred and unknown data
- require review for ambiguity or conflict
- never mix revisions

## Structure

```text
src/dios/
schemas/
examples/
docs/
tests/
```

## Test

```bash
python -m unittest discover -s tests -v
```

No open-source license has been selected yet.