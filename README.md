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

## Architecture

```text
source package
→ project and revision context
→ document and sheet registry
→ extraction
→ object graph
→ measurement plan
→ quantity engine
→ validation
→ review
→ exports
```

## Structure

```text
src/dios/
schemas/
examples/
docs/
tests/
```

## Quick start

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Aufmass Method](docs/AUFMASS_METHOD.md)
- [Data Model](docs/DATA_MODEL.md)
- [Validation](docs/VALIDATION.md)
- [Roadmap](docs/ROADMAP.md)

Only public-safe code, schemas and synthetic fixtures belong in this repository. Real project files and outputs remain outside it.

No open-source license has been selected yet.