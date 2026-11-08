# Native assembly snapshot and motion baseline v1

`dios.cad_assembly_snapshot` defines a provider-neutral read-only `AssemblyReader`.
There is no native provider implementation, mutation operation, dynamic dispatch,
macro, shell, or live CAD call. Existing capability registration is unchanged.

Adapters supply typed immutable `SourceRevision`, `Component`, `NativeMate`, and
`Page` records. Revision identity includes provider, assembly, and an opaque
revision token. The adapter must guarantee revision-pinned exhaustive lists and
change the token whenever any relevant assembly state changes. Pagination totals
must be exact and stable. Terminal cursors are `None`; other cursors are opaque
nonblank strings. Empty intermediate pages, cursor cycles, inconsistent totals,
truncation, duplicates, and resource-limit exhaustion fail closed. Both lists
are fully traversed for an accepted snapshot. Default bounds are 1000 pages and
100000 records per list; reaching a bound never implies completeness.

Component IDs identify assembly occurrences, including nested instances; native
part IDs may repeat across distinct occurrences. Adapters must flatten the entire
assembly and resolve native mate references to those occurrence IDs. Missing,
ambiguous, unresolved, suppressed, fixed, constrained, and unknown states cannot
establish this conservative baseline. Every component must be explicitly FREE.
Even one explicit native mate blocks the baseline; its type is not interpreted.
Intended abstract joints are separate design intent and cannot substitute for
native mate evidence or establish that the assembly is unconstrained.

Transforms are immutable row-major 4x4 matrices from component-local coordinates
to assembly coordinates, translation in metres, with a right-handed orthonormal
rotation and homogeneous bottom row. Finite numeric values excluding booleans
are required. Rigidity and determinant checks use absolute tolerance 1e-9.
Adapters must normalize provider units and coordinate conventions before capture.

`capture_snapshot(reader, expected_source)` checks the caller's exact source
revision before enumeration, on every page and record, and after enumeration.
`establish_motion_baseline` additionally requires a nonempty, unique tuple of
existing moving occurrence IDs and returns a `VerifiedBaselineReceipt` containing
full evidence, selection, contract version, and SHA-256 digest. Any failure raises
`SnapshotError` and returns no receipt. Reader exceptions likewise propagate
without granting a baseline. Transport timeouts must be enforced by adapters.

A follow-up executor must call `verify_baseline_receipt` with its independently
expected source and exact motion selection. This rejects unchecked booleans,
altered evidence, wrong selections, stale revisions, and even changed transforms
under a reused revision token by recapturing and comparing the complete snapshot.
The digest is reproducible integrity evidence, not a signature, credential, or
mutation authorization. A caller-constructed receipt gains no trust merely by
having this Python type: all evidence is revalidated against the trusted reader.
The executor must bind verification and execution to the same native revision
using a provider transaction or compare-and-swap guard; read-only verification
alone cannot eliminate the subsequent time-of-check/time-of-use race.

## Evidence and remaining integration gate

Synthetic unittest cases exercise successful receipt consumption, occurrence
pagination, mate pagination, identity and state failures, malformed rigid
transforms, pagination failures and limits, revision races, and stale or altered
receipts. They prove only the source-level gate under the reader contract.

Native integration is **NOT VERIFIED**. Before motion execution, an independently
validated adapter must prove exhaustive nested occurrence/mate enumeration,
revision consistency, actual freedom/grounding semantics, unit/frame conversion,
and atomic revision binding. This receipt does not prove collision clearance,
kinematic feasibility, continuous-path safety, or authorization to execute motion.
Separate private collision evidence covers only sampled frames; no broader claim
is made here. No user CAD files or private workstation data are needed or read.
