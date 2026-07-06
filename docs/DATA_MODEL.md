# Canonical Data Model

Status: `PRE-ALPHA`

## Core entities

- `project`
- `source_package`
- `document`
- `sheet`
- `revision`
- `drawing_zone`
- `level`
- `grid`
- `room`
- `drawing_object`
- `system`
- `work_package`
- `quantity_record`
- `evidence_record`
- `assumption`
- `conflict`
- `review`

## Core relations

```text
project contains source_package
source_package contains document
document contains sheet
sheet has revision
sheet contains drawing_zone
drawing_zone contains drawing_object
drawing_object belongs_to room / level / system / work_package
drawing_object measured_by quantity_record
quantity_record supported_by evidence_record
quantity_record may_have assumption or conflict
quantity_record approved_by review
revision supersedes revision
revision change invalidates dependent records
```

## Design rules

- stable identifiers survive export and reprocessing;
- source and derived values are stored separately;
- revisions are immutable;
- proposal, reviewed and approved states are separate;
- one physical object may have several representations across sheets;
- legends and schedules define types but do not automatically represent installed instances.