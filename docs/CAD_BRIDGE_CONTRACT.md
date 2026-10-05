# Universal CAD Bridge Contract

`core/cad_bridge.py` defines a provider-neutral CAD application bridge
foundation. The public repository contains only typed contracts and an
in-process synthetic adapter. It does not contain provider-specific bindings,
Windows automation, live CAD runtime code, shell execution, macro execution, or
private workstation paths.

The session authority is `CADSessionGrant` with `scope:
FULL_CAD_WORKSPACE`. Inside a valid full-workspace grant there is no
per-operation approval model; authorization is the session grant plus the
declared capability set. Commands are structured `CADCommand` objects grouped in
`CADCommandBatch`, and unsupported operations or capabilities must return a
typed `CADFailure`.

Private provider adapters must conform to these rules:

- Implement the same create, modify, delete, rebuild, save, checkpoint,
  rollback, snapshot, batch receipt, and capability-discovery semantics.
- Bind every command to the granted workspace and reject paths or handles that
  escape the workspace boundary.
- Return deterministic before/after `CADWorkspaceSnapshot` records and
  `CADTransactionReceipt` objects for success, failure, and partial failure.
- Never expose arbitrary shell, script, macro, executable path, endpoint,
  credential, customer drawing content, or workstation identity through the
  public contract.
- Keep provider-specific code and live runtime registration outside this public
  repository unless a separate approved contract explicitly permits it.

## Contract Objects

- `CADSessionGrant` is the only authority token for bridge execution. A valid
  grant is workspace-bound, full-workspace scoped, and capability-limited.
- `CADCapabilityProfile` advertises supported structured operations and whether
  the adapter is synthetic or live. Public code must keep
  `live_runtime_execution` false.
- `CADCommand` and `CADCommandBatch` carry typed operations only. They do not
  carry arbitrary scripts, shell commands, macros, provider executables, or live
  automation handles.
- `CADWorkspaceSnapshot`, `CADChangeSet`, `CADOperationResult`,
  `CADValidationResult`, and `CADTransactionReceipt` provide deterministic
  before/after evidence for success, failure, and partial-failure batches.
- `CADFailure` is the required error surface for unsupported operations,
  unsupported capabilities, missing targets, invalid checkpoints, oversized
  batches, and workspace-boundary violations.

## Synthetic Adapter Behavior

The public `SyntheticCADAdapter` is an in-process adapter for contract tests and
agent integration development. It creates, modifies, deletes, rebuilds, saves,
checkpoints, rolls back, snapshots, discovers capabilities, and executes batches
against a deterministic in-memory workspace. Save and checkpoint files are
restricted to the granted workspace root and contain only public-safe synthetic
snapshot data.

Batch execution supports partial failure. With `continue_on_error` true, later
commands continue after a failed command and the receipt status becomes
`partial_failure` when any earlier or later operation succeeds. With
`continue_on_error` false, execution stops at the first failed command.

## Private Adapter Conformance

Private provider adapters may map the contract to a local CAD runtime outside
this repository, but they must preserve the public semantics:

- Reject any command whose workspace id, workspace root, target handle, or file
  path escapes the granted workspace boundary.
- Return stable snapshots for identical workspace state, with sorted entity and
  artifact ordering.
- Return `CADFailure` for unsupported capabilities instead of falling through to
  provider-specific errors.
- Produce a receipt for every batch attempt, including grant validation failure,
  unsupported capability failure, partial failure, and rollback.
- Treat a valid `FULL_CAD_WORKSPACE` grant as sufficient authority for granted
  capabilities; do not add a per-operation approval prompt inside the adapter.
- Keep secrets, workstation names, customer/project identifiers, private paths,
  provider-specific source code, and live CAD automation bindings out of public
  artifacts.
