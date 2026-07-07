# DIOS SketchUp Integration Architecture

Status: `DESIGN / EXPERIMENTAL / NOT PRODUCTION`

This document defines a public-safe architecture for controlled DIOS interaction with an open SketchUp Desktop model on a remote Windows workstation.

The integration is a working-representation connector. It does not make `.skp` files the canonical source of truth and does not change the current DIOS architecture-freeze gate for production measurement workflows.

## 1. Goal

Enable DIOS to inspect and update a SketchUp scene through structured, reviewable operations while preserving:

- drawing and revision authority;
- stable object identity;
- deterministic geometry and placement;
- one-command/one-undo behaviour;
- explicit human approval;
- remote use through a private Tailscale network;
- isolation between network transport and the SketchUp Ruby API.

The target workflow is:

```text
validated DIOS scene state
→ approved scene operation
→ remote workstation delivery
→ SketchUp main-thread execution
→ structured result
→ validation
→ proposed/manual corrections
→ DIOS approval
```

## 2. Preferred deployment topology

The media PC is not required.

```text
DIOS / Skeleton controller
        ⇅ private Tailscale network
Windows workstation
  ├─ DIOS Workstation Agent
  └─ SketchUp Desktop
      └─ DIOS SketchUp Bridge.rbz
```

The workstation may be at home, in an office, or on another trusted network. Tailscale supplies private peer connectivity. The connector is not exposed directly to the public internet.

If the DIOS controller runs on the same Windows workstation, the agent and extension still use the same local contracts, while Tailscale is used only for remote access to that workstation.

## 3. Architectural boundaries

### 3.1 DIOS/Skeleton Controller

Responsibilities:

- project, source and revision context;
- canonical scene graph;
- workflow state and approval gates;
- command creation and signing;
- command queue and retry policy;
- asset registry and approved asset references;
- validation before and after execution;
- evidence, audit and result storage;
- review of manual SketchUp changes.

The controller never sends arbitrary Ruby, shell, UI automation or mouse/keyboard commands.

### 3.2 DIOS Workstation Agent

A small Windows service or user-session process installed on the SketchUp workstation.

Responsibilities:

- Tailscale-facing transport;
- controller pairing and session authentication;
- command inbox/outbox;
- durable local queue;
- reconnect after roaming, sleep or network change;
- process and session health;
- local asset cache and restricted file transfer;
- localhost API for the SketchUp extension;
- structured logs without private drawing contents;
- optional later support for starting SketchUp and opening an approved model.

The agent does not call the SketchUp Ruby API directly.

### 3.3 DIOS SketchUp Bridge

A Ruby extension installed as `.rbz` and loaded inside SketchUp Desktop.

Responsibilities:

- compact `UI::HtmlDialog` panel;
- registration of the open model;
- polling the local agent over loopback only;
- validation of command context and schema version;
- queuing commands for SketchUp main-thread execution;
- stable DIOS entity/component attributes;
- idempotent component insertion and updates;
- camera, scene, tag, material and visibility operations;
- model inspection;
- preview export;
- capture of proposed manual changes;
- structured results and errors.

The bridge is not a public network server and does not hold persistent remote credentials.

### 3.4 SketchUp Working Model

The open `.skp` model is an editable working representation.

It may contain:

- imported drawing underlays;
- manually modelled geometry;
- generic components;
- exact product components;
- DIOS-managed objects;
- user-created objects not yet registered in DIOS.

Manual changes do not become canonical automatically.

## 4. Authority model

```text
drawing source and revision authority
→ DIOS canonical scene graph
→ approved operation plan
→ SketchUp working representation
→ structured execution result
→ validation and human approval
```

Authority rules:

1. The source drawing/revision remains authoritative for source facts.
2. The DIOS canonical scene graph is authoritative for normalized scene state.
3. SketchUp is authoritative only for the current local working representation.
4. Manual SketchUp edits are proposals until approved by DIOS.
5. Presentation outputs are never measurement or revision authority.
6. The connector must reject revision mismatch rather than applying commands to the wrong state.

## 5. Module decomposition

### 5.1 Controller Connector Adapter

Suggested package:

```text
src/dios/connectors/sketchup/
  adapter.py
  command_service.py
  session_service.py
  result_service.py
  change_service.py
  asset_service.py
  models.py
  errors.py
```

Interfaces:

```text
pair_workstation()
enqueue_command()
get_command_status()
receive_result()
receive_change_proposal()
register_preview()
revoke_session()
```

### 5.2 Workstation Agent

Suggested package:

```text
agents/sketchup_workstation/
  service/
  transport/
  pairing/
  queue/
  local_api/
  asset_cache/
  process_monitor/
  logging/
  config/
```

Internal services:

- `TailnetTransport`
- `PairingService`
- `CommandInbox`
- `ResultOutbox`
- `LocalBridgeApi`
- `AssetCache`
- `ProcessMonitor`
- `AgentStateStore`

### 5.3 SketchUp Bridge Extension

Suggested package:

```text
integrations/sketchup/dios_sketchup_bridge.rb
integrations/sketchup/dios_sketchup_bridge/
  extension.rb
  controller.rb
  local_transport.rb
  command_queue.rb
  command_validator.rb
  model_registry.rb
  entity_registry.rb
  command_executor.rb
  change_tracker.rb
  preview_exporter.rb
  ui/
  schemas/
  VERSION
```

Internal components:

- `BridgeController`
- `LocalTransport`
- `CommandQueue`
- `CommandValidator`
- `ModelRegistry`
- `EntityRegistry`
- `CommandExecutor`
- `ChangeTracker`
- `PreviewExporter`
- `BridgeDialog`

### 5.4 Shared Protocol Package

Suggested package:

```text
schemas/connectors/sketchup/
  command.schema.json
  result.schema.json
  change.schema.json
  session.schema.json
  asset-manifest.schema.json
```

The schemas are shared contract artifacts. Runtime implementations may be Python, .NET and Ruby, but the wire contract remains language-neutral.

## 6. Connection and pairing

### 6.1 Initial pairing

```text
1. Workstation agent starts and identifies its local workstation.
2. User opens the DIOS controller and requests a pairing code.
3. User enters the short-lived code in the workstation agent.
4. Controller and agent establish a named workstation registration.
5. Controller stores the workstation identity and allowed capabilities.
6. Agent stores only revocable session material required for reconnect.
```

Pairing must be explicit. Discovery of a peer on the tailnet is not sufficient authorization.

### 6.2 Runtime path

```text
Controller
→ authenticated command endpoint
→ Workstation Agent durable inbox
→ localhost bridge queue
→ SketchUp UI/main thread
→ local result
→ Agent durable outbox
→ Controller
```

### 6.3 Offline behaviour

If SketchUp is closed or the bridge is unavailable:

- the agent keeps commands in `WAITING_FOR_APPLICATION`;
- no command is marked executed;
- expired commands are not applied later;
- the controller displays workstation and application state separately;
- the user may cancel queued commands before SketchUp reconnects.

## 7. Command lifecycle

```text
CREATED
→ VALIDATED
→ QUEUED_REMOTE
→ DELIVERED_TO_AGENT
→ WAITING_FOR_APPLICATION
→ DELIVERED_TO_BRIDGE
→ EXECUTING
→ SUCCEEDED | FAILED | REJECTED | EXPIRED | CANCELLED
```

A command contains:

- `schema_version`;
- `command_id`;
- `correlation_id`;
- `project_id`;
- `model_id`;
- `expected_revision`;
- `command_type`;
- `created_at` and `expires_at`;
- `dry_run`;
- `payload`;
- `preconditions`;
- `requested_by`;
- `approval_reference` where required.

A result contains:

- command identity;
- final status;
- timestamps;
- SketchUp version and model context;
- affected object IDs;
- before/after summaries;
- validation findings;
- warnings and structured errors;
- generated artifact references;
- bridge and agent versions.

## 8. Stable identity

Use a SketchUp attribute dictionary named `dios`.

Model keys:

- `project_id`
- `model_id`
- `source_revision`
- `scene_state_revision`
- `registered_at`
- `last_sync_at`

Entity/component keys:

- `object_id`
- `object_type`
- `asset_id`
- `room_id`
- `source_revision`
- `last_command_id`
- `sync_status`
- `representation_status`

Rules:

```text
create if absent
update if changed
do nothing if identical
never duplicate silently
never adopt an unregistered entity without explicit registration
```

Persistent SketchUp IDs are useful local references but do not replace DIOS object IDs.

## 9. MVP command set

Read-only:

- `ping`
- `get_capabilities`
- `inspect_model`
- `inspect_selection`
- `inspect_registered_objects`

Registration:

- `register_model_context`
- `register_selected_component`
- `register_selected_group`

Controlled mutation:

- `place_component`
- `update_transform`
- `set_visibility`
- `assign_tag`
- `assign_material`
- `create_or_update_scene`
- `set_camera`

Artifacts and review:

- `export_preview`
- `capture_model_snapshot`
- `propose_manual_changes`

Excluded from the first MVP:

- arbitrary geometry tracing;
- free-form Ruby execution;
- automated public asset-site access;
- remote mouse or keyboard control;
- silent deletion;
- destructive batch operations without approval;
- automatic canonical acceptance of manual edits.

## 10. Main-thread execution

The network stack must never mutate the model directly.

```text
agent response
→ local transport callback
→ validated command queue
→ `UI.start_timer`
→ SketchUp main-thread executor
```

Each mutating command executes as one SketchUp operation:

```text
start operation
→ verify context and preconditions
→ capture before state
→ apply mutation
→ validate result
→ commit operation
```

On failure:

```text
abort operation
→ return structured error
→ leave model unchanged where possible
```

This preserves one-command/one-undo behaviour.

## 11. Transform and units contract

Wire units are millimetres and degrees.

Transform payload:

```json
{
  "position_mm": [4250, 3170, 0],
  "rotation_deg": [0, 0, 90],
  "scale": [1, 1, 1],
  "coordinate_frame": "MODEL"
}
```

The bridge converts millimetres to SketchUp internal units at execution time.

Supported coordinate frames:

- `MODEL`
- `PROJECT_ORIGIN`
- `ROOM_LOCAL` only after room-local transforms are explicitly registered.

No implicit scale inference is allowed during mutation.

## 12. Asset handling

Asset flow:

```text
approved asset record
→ controller asset manifest
→ workstation agent download/cache
→ local checksum verification
→ bridge receives local approved path
→ SketchUp loads/reuses component definition
```

Rules:

- only paths inside the configured agent asset cache are accepted;
- every asset has `asset_id`, checksum, format, dimensions, anchor and status;
- repeated placement reuses a loaded component definition;
- generic, substitute and exact assets remain distinguishable;
- the bridge does not scrape or automate external asset libraries;
- manually imported components may be registered into a private DIOS library after review.

Representation statuses:

- `GENERIC_PLACEHOLDER`
- `APPROVED_SUBSTITUTE`
- `EXACT_PRODUCT`
- `UNREGISTERED_LOCAL`

## 13. Manual change capture

The bridge maintains a last-approved baseline for registered objects.

A manual-change proposal records:

```json
{
  "object_id": "WC-01",
  "change_type": "TRANSFORM_CHANGED",
  "before": {},
  "after": {},
  "source": "MANUAL_SKETCHUP_EDIT",
  "status": "PROPOSED"
}
```

Initial change types:

- `TRANSFORM_CHANGED`
- `VISIBILITY_CHANGED`
- `TAG_CHANGED`
- `MATERIAL_CHANGED`
- `COMPONENT_REPLACED`
- `OBJECT_DELETED_LOCALLY`
- `UNREGISTERED_OBJECT_CREATED`

Deletion is never accepted silently. A locally missing managed object becomes a proposal or conflict.

## 14. Validation

Pre-execution checks:

- schema version supported;
- command not expired;
- workstation and application capability match;
- project/model IDs match the open model;
- expected source and scene revisions match;
- object IDs are unique;
- asset exists and checksum matches;
- payload ranges and sizes are valid;
- user approval exists for commands that require it.

Post-execution checks:

- target object exists exactly once;
- transform matches within tolerance;
- assigned asset/tag/material is correct;
- bounds are finite and plausible;
- no unexpected affected managed objects;
- no silent duplication;
- operation result can be serialized;
- model state revision advances exactly once.

Failure classes:

- `CONTEXT_MISMATCH`
- `REVISION_MISMATCH`
- `SCHEMA_INVALID`
- `COMMAND_EXPIRED`
- `CAPABILITY_UNAVAILABLE`
- `ASSET_NOT_FOUND`
- `ASSET_CHECKSUM_MISMATCH`
- `OBJECT_NOT_FOUND`
- `OBJECT_DUPLICATED`
- `PRECONDITION_FAILED`
- `EXECUTION_FAILED`
- `POSTCONDITION_FAILED`
- `LOCAL_CHANGE_CONFLICT`

## 15. Security model

Network identity and application authorization are separate layers.

Required controls:

- Tailscale private connectivity;
- explicit controller-agent pairing;
- revocable workstation registration;
- short-lived sessions;
- command allowlist;
- strict JSON validation;
- command expiry and replay protection;
- no arbitrary code execution;
- localhost-only bridge API;
- restricted local asset cache;
- encrypted transport through the private network;
- audit trail for all accepted and rejected commands;
- no private drawing contents in routine logs.

Recommended tailnet policy:

```text
controller role
→ may reach agent command API
workstation agent role
→ may reach controller result API
other peers
→ no connector access by default
```

## 16. Observability

Controller view:

- workstation online/offline;
- agent version;
- SketchUp running/not running;
- bridge connected/disconnected;
- open model ID and revision;
- queued/running/failed command counts;
- last successful sync;
- last error class;
- capability report.

Bridge panel:

- local agent state;
- paired controller name;
- current model registration;
- source and scene revisions;
- queue state;
- current command;
- latest result;
- dry-run indicator;
- manual-change count;
- reconnect and resync actions.

## 17. Versioning and compatibility

Each layer exposes a version:

- protocol version;
- controller adapter version;
- workstation agent version;
- bridge version;
- SketchUp version;
- model schema version.

Compatibility is negotiated before command delivery.

A command must be rejected when its required capability or schema version is not supported. The agent and bridge must not silently reinterpret unknown fields or command types.

## 18. Failure handling

### Workstation offline

Command remains queued until expiry or cancellation.

### Agent online, SketchUp closed

Command becomes `WAITING_FOR_APPLICATION`.

### Wrong model open

Bridge returns `CONTEXT_MISMATCH`; no mutation occurs.

### Revision changed locally

Bridge returns `REVISION_MISMATCH`; DIOS requests review/resync.

### SketchUp operation fails

Bridge aborts the operation and returns `EXECUTION_FAILED` with a sanitized error.

### Result upload interrupted

Agent stores the result durably and retries with the same command/result identity.

### Duplicate delivery

The bridge returns the stored prior result for the same completed command ID and does not execute twice.

## 19. Delivery stages

### Stage A — Protocol and mock

- JSON schemas;
- controller mock endpoints;
- agent local API mock;
- synthetic command fixtures;
- no SketchUp mutation.

### Stage B — Read-only bridge

- pairing visibility;
- model registration;
- model and selection inspection;
- capability reporting.

### Stage C — Controlled component operations

- component registration;
- asset cache;
- idempotent placement;
- transform, visibility, tag and material updates;
- one-command/one-undo.

### Stage D — Review and artifacts

- scene and camera control;
- preview export;
- baseline snapshot;
- manual change proposals;
- validation reports.

### Stage E — Optional workstation automation

- start SketchUp;
- open approved model;
- process health and restart;
- only after live connector reliability is proven.

## 20. Acceptance criteria for the architecture

The design is considered implementable when:

- all boundaries have explicit ownership;
- the extension is local-only and cannot receive arbitrary network code;
- controller, agent and bridge share versioned schemas;
- revision mismatch blocks mutation;
- commands are idempotent and replay-safe;
- every mutation is one undoable SketchUp operation;
- assets are checksum-controlled and path-restricted;
- manual changes remain proposals;
- the media PC is absent from the required path;
- remote operation works through Tailscale without public exposure;
- private project content is excluded from the public repository.
