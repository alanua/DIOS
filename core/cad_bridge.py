from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional


FULL_CAD_WORKSPACE = "FULL_CAD_WORKSPACE"

CAPABILITY_CREATE = "entity.create"
CAPABILITY_MODIFY = "entity.modify"
CAPABILITY_DELETE = "entity.delete"
CAPABILITY_REBUILD = "workspace.rebuild"
CAPABILITY_SAVE = "workspace.save"
CAPABILITY_CHECKPOINT = "transaction.checkpoint"
CAPABILITY_ROLLBACK = "transaction.rollback"
CAPABILITY_SNAPSHOT = "workspace.snapshot"

SUPPORTED_CAPABILITIES = frozenset(
    {
        CAPABILITY_CREATE,
        CAPABILITY_MODIFY,
        CAPABILITY_DELETE,
        CAPABILITY_REBUILD,
        CAPABILITY_SAVE,
        CAPABILITY_CHECKPOINT,
        CAPABILITY_ROLLBACK,
        CAPABILITY_SNAPSHOT,
    }
)

OPERATION_CAPABILITIES = {
    "create": CAPABILITY_CREATE,
    "modify": CAPABILITY_MODIFY,
    "delete": CAPABILITY_DELETE,
    "rebuild": CAPABILITY_REBUILD,
    "save": CAPABILITY_SAVE,
    "checkpoint": CAPABILITY_CHECKPOINT,
    "rollback": CAPABILITY_ROLLBACK,
}


@dataclass(frozen=True)
class CADFailure:
    code: str
    message: str
    command_id: Optional[str] = None
    operation: Optional[str] = None
    retryable: bool = False


@dataclass(frozen=True)
class CADSessionGrant:
    session_id: str
    workspace_id: str
    workspace_root: str
    scope: str = FULL_CAD_WORKSPACE
    capabilities: tuple[str, ...] = tuple(sorted(SUPPORTED_CAPABILITIES))
    expires_at: Optional[str] = None


@dataclass(frozen=True)
class CADCapabilityProfile:
    provider_id: str
    provider_kind: str
    bridge_revision: str
    capabilities: tuple[str, ...]
    operations: tuple[str, ...]
    max_batch_operations: int
    supports_transactions: bool
    supports_partial_failure: bool
    live_runtime_execution: bool = False


@dataclass(frozen=True)
class CADCommand:
    command_id: str
    operation: str
    target_ref: Optional[str] = None
    payload: Mapping[str, Any] = field(default_factory=dict)
    required_capability: Optional[str] = None
    idempotency_key: Optional[str] = None


@dataclass(frozen=True)
class CADCommandBatch:
    batch_id: str
    commands: tuple[CADCommand, ...]
    continue_on_error: bool = True


@dataclass(frozen=True)
class CADWorkspaceSnapshot:
    snapshot_id: str
    workspace_id: str
    revision: int
    saved_revision: int
    rebuild_count: int
    entities: tuple[Mapping[str, Any], ...]
    saved_artifacts: tuple[str, ...] = ()


@dataclass(frozen=True)
class CADChangeSet:
    before_snapshot_id: str
    after_snapshot_id: str
    created_refs: tuple[str, ...] = ()
    modified_refs: tuple[str, ...] = ()
    deleted_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CADValidationResult:
    status: str
    failures: tuple[CADFailure, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CADOperationResult:
    command_id: str
    operation: str
    status: str
    before_snapshot: CADWorkspaceSnapshot
    after_snapshot: CADWorkspaceSnapshot
    change_set: CADChangeSet
    entity_ref: Optional[str] = None
    output: Mapping[str, Any] = field(default_factory=dict)
    failure: Optional[CADFailure] = None


@dataclass(frozen=True)
class CADTransactionReceipt:
    batch_id: str
    status: str
    before_snapshot: CADWorkspaceSnapshot
    after_snapshot: CADWorkspaceSnapshot
    change_set: CADChangeSet
    validation: CADValidationResult
    operation_results: tuple[CADOperationResult, ...]


class SyntheticCADAdapter:
    """Provider-neutral in-process CAD bridge for deterministic contract tests."""

    def __init__(self, *, workspace_id: str, workspace_root: str | Path, max_batch_operations: int = 100) -> None:
        if not workspace_id:
            raise ValueError("workspace_id is required")
        if max_batch_operations < 1:
            raise ValueError("max_batch_operations must be positive")
        self.workspace_id = workspace_id
        self.workspace_root = Path(workspace_root).resolve()
        self.max_batch_operations = max_batch_operations
        self._entities: dict[str, dict[str, Any]] = {}
        self._revision = 0
        self._saved_revision = 0
        self._rebuild_count = 0
        self._checkpoints: dict[str, tuple[dict[str, dict[str, Any]], int, int, int]] = {}
        self._saved_artifacts: set[str] = set()
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def capability_profile(self) -> CADCapabilityProfile:
        return CADCapabilityProfile(
            provider_id="synthetic.in_process",
            provider_kind="synthetic",
            bridge_revision="cad_bridge.v2",
            capabilities=tuple(sorted(SUPPORTED_CAPABILITIES)),
            operations=tuple(sorted(OPERATION_CAPABILITIES)),
            max_batch_operations=self.max_batch_operations,
            supports_transactions=True,
            supports_partial_failure=True,
            live_runtime_execution=False,
        )

    def grant(self, *, session_id: str, capabilities: tuple[str, ...] | None = None) -> CADSessionGrant:
        if not session_id:
            raise ValueError("session_id is required")
        requested = tuple(sorted(capabilities or SUPPORTED_CAPABILITIES))
        unsupported = sorted(set(requested) - SUPPORTED_CAPABILITIES)
        if unsupported:
            raise ValueError("unsupported grant capabilities: " + ", ".join(unsupported))
        return CADSessionGrant(
            session_id=session_id,
            workspace_id=self.workspace_id,
            workspace_root=str(self.workspace_root),
            capabilities=requested,
        )

    def snapshot(self) -> CADWorkspaceSnapshot:
        return self._snapshot()

    def execute(self, grant: CADSessionGrant, command: CADCommand) -> CADOperationResult:
        receipt = self.execute_batch(
            grant,
            CADCommandBatch(batch_id=f"single.{command.command_id}", commands=(command,), continue_on_error=True),
        )
        if receipt.operation_results:
            return receipt.operation_results[0]
        failure = receipt.validation.failures[0] if receipt.validation.failures else CADFailure(
            "EXECUTION_FAILED",
            "command execution failed before operation dispatch",
            command_id=command.command_id,
            operation=command.operation,
        )
        return CADOperationResult(
            command_id=command.command_id,
            operation=command.operation,
            status="failed",
            before_snapshot=receipt.before_snapshot,
            after_snapshot=receipt.after_snapshot,
            change_set=receipt.change_set,
            entity_ref=command.target_ref,
            failure=failure,
        )

    def execute_batch(self, grant: CADSessionGrant, batch: CADCommandBatch) -> CADTransactionReceipt:
        grant_failure = self._validate_grant(grant)
        before_batch = self._snapshot()
        results: list[CADOperationResult] = []
        failures: list[CADFailure] = []

        if not batch.batch_id:
            failures.append(CADFailure("BATCH_ID_REQUIRED", "batch_id is required"))
        elif grant_failure is not None:
            failures.append(grant_failure)
        elif len(batch.commands) > self.max_batch_operations:
            failures.append(
                CADFailure(
                    code="BATCH_TOO_LARGE",
                    message=f"batch has {len(batch.commands)} commands; max is {self.max_batch_operations}",
                )
            )

        if not failures:
            for command in batch.commands:
                result = self._execute_validated_command(grant, command)
                results.append(result)
                if result.failure is not None:
                    failures.append(result.failure)
                    if not batch.continue_on_error:
                        break

        after_batch = self._snapshot()
        validation = CADValidationResult(status="failed" if failures else "passed", failures=tuple(failures))
        receipt_status = _receipt_status(results, failures)
        return CADTransactionReceipt(
            batch_id=batch.batch_id,
            status=receipt_status,
            before_snapshot=before_batch,
            after_snapshot=after_batch,
            change_set=_diff_snapshots(before_batch, after_batch),
            validation=validation,
            operation_results=tuple(results),
        )

    def _execute_validated_command(self, grant: CADSessionGrant, command: CADCommand) -> CADOperationResult:
        before = self._snapshot()
        failure = self._command_failure(grant, command)
        entity_ref: Optional[str] = command.target_ref
        output: dict[str, Any] = {}

        if failure is None:
            if command.operation == "create":
                entity_ref = self._create_entity(command)
                output = {"entity_ref": entity_ref}
            elif command.operation == "modify":
                entity_ref = self._modify_entity(command)
                output = {"entity_ref": entity_ref}
            elif command.operation == "delete":
                entity_ref = self._delete_entity(command)
                output = {"entity_ref": entity_ref}
            elif command.operation == "rebuild":
                self._revision += 1
                self._rebuild_count += 1
                output = {"rebuild_count": self._rebuild_count}
            elif command.operation == "save":
                path = self._save_workspace(command)
                output = {"path": path}
            elif command.operation == "checkpoint":
                checkpoint_id = self._checkpoint_workspace(command)
                output = {"checkpoint_id": checkpoint_id}
            elif command.operation == "rollback":
                checkpoint_id = self._rollback_workspace(command)
                output = {"checkpoint_id": checkpoint_id}

        after = self._snapshot()
        return CADOperationResult(
            command_id=command.command_id,
            operation=command.operation,
            status="failed" if failure is not None else "ok",
            before_snapshot=before,
            after_snapshot=after,
            change_set=_diff_snapshots(before, after),
            entity_ref=entity_ref,
            output=output,
            failure=failure,
        )

    def _validate_grant(self, grant: CADSessionGrant) -> Optional[CADFailure]:
        if grant.scope != FULL_CAD_WORKSPACE:
            return CADFailure("SESSION_SCOPE_UNSUPPORTED", "CAD bridge requires FULL_CAD_WORKSPACE scope")
        if grant.workspace_id != self.workspace_id:
            return CADFailure("WORKSPACE_MISMATCH", "session grant is bound to a different workspace")
        if Path(grant.workspace_root).resolve() != self.workspace_root:
            return CADFailure("WORKSPACE_ROOT_MISMATCH", "session grant is bound to a different workspace root")
        unsupported = sorted(set(grant.capabilities) - SUPPORTED_CAPABILITIES)
        if unsupported:
            return CADFailure("CAPABILITY_UNSUPPORTED", "unsupported grant capabilities: " + ", ".join(unsupported))
        return None

    def _command_failure(self, grant: CADSessionGrant, command: CADCommand) -> Optional[CADFailure]:
        if not command.command_id:
            return CADFailure("COMMAND_ID_REQUIRED", "command_id is required", operation=command.operation)
        if not isinstance(command.payload, Mapping):
            return CADFailure("PAYLOAD_INVALID", "command payload must be an object", command.command_id, command.operation)
        capability = command.required_capability or OPERATION_CAPABILITIES.get(command.operation)
        if capability is None:
            return CADFailure(
                "OPERATION_UNSUPPORTED",
                f"unsupported CAD operation: {command.operation}",
                command_id=command.command_id,
                operation=command.operation,
            )
        if capability not in SUPPORTED_CAPABILITIES:
            return CADFailure(
                "CAPABILITY_UNSUPPORTED",
                f"unsupported CAD capability: {capability}",
                command_id=command.command_id,
                operation=command.operation,
            )
        if capability not in set(grant.capabilities):
            return CADFailure(
                "CAPABILITY_NOT_GRANTED",
                f"CAD capability not granted for session: {capability}",
                command_id=command.command_id,
                operation=command.operation,
            )
        if command.operation in {"modify", "delete"} and not command.target_ref:
            return CADFailure("TARGET_REQUIRED", "command target_ref is required", command.command_id, command.operation)
        if command.operation in {"modify", "delete"} and command.target_ref not in self._entities:
            return CADFailure("TARGET_NOT_FOUND", "command target_ref was not found", command.command_id, command.operation)
        if command.operation == "create":
            try:
                entity_ref = _entity_ref_for(command)
            except ValueError as exc:
                return CADFailure("ENTITY_REF_INVALID", str(exc), command.command_id, command.operation)
            try:
                _json_value(command.payload.get("geometry", {}))
                properties = _json_value(command.payload.get("properties", {}))
            except (TypeError, ValueError) as exc:
                return CADFailure("PAYLOAD_INVALID", str(exc), command.command_id, command.operation)
            if not isinstance(properties, dict):
                return CADFailure("PAYLOAD_INVALID", "properties must be an object", command.command_id, command.operation)
            if entity_ref in self._entities:
                return CADFailure("ENTITY_ALREADY_EXISTS", "entity already exists", command.command_id, command.operation)
        if command.operation == "modify":
            try:
                if "geometry" in command.payload:
                    _json_value(command.payload["geometry"])
                if "properties" in command.payload:
                    properties = _json_value(command.payload["properties"])
                    if not isinstance(properties, dict):
                        return CADFailure(
                            "PAYLOAD_INVALID",
                            "properties must be an object",
                            command.command_id,
                            command.operation,
                        )
            except (TypeError, ValueError) as exc:
                return CADFailure("PAYLOAD_INVALID", str(exc), command.command_id, command.operation)
        if command.operation == "rollback":
            try:
                checkpoint_id = _string_payload(command, "checkpoint_id", default=command.target_ref)
            except ValueError as exc:
                return CADFailure("CHECKPOINT_REF_INVALID", str(exc), command.command_id, command.operation)
            if checkpoint_id not in self._checkpoints:
                return CADFailure("CHECKPOINT_NOT_FOUND", "checkpoint was not found", command.command_id, command.operation)
        if command.operation in {"save", "checkpoint"}:
            try:
                self._resolve_workspace_path(command.payload.get("path") or f"{command.operation}.json")
            except ValueError as exc:
                return CADFailure("WORKSPACE_BOUNDARY_VIOLATION", str(exc), command.command_id, command.operation)
        return None

    def _create_entity(self, command: CADCommand) -> str:
        entity_ref = _entity_ref_for(command)
        self._entities[entity_ref] = {
            "entity_ref": entity_ref,
            "type": str(command.payload.get("type", "generic")),
            "geometry": _json_value(command.payload.get("geometry", {})),
            "properties": _json_value(command.payload.get("properties", {})),
            "version": 1,
        }
        self._revision += 1
        return entity_ref

    def _modify_entity(self, command: CADCommand) -> str:
        assert command.target_ref is not None
        entity = self._entities[command.target_ref]
        if "type" in command.payload:
            entity["type"] = str(command.payload["type"])
        if "geometry" in command.payload:
            entity["geometry"] = _json_value(command.payload["geometry"])
        if "properties" in command.payload:
            merged = dict(entity.get("properties", {}))
            merged.update(_json_value(command.payload["properties"]))
            entity["properties"] = merged
        entity["version"] = int(entity["version"]) + 1
        self._revision += 1
        return command.target_ref

    def _delete_entity(self, command: CADCommand) -> str:
        assert command.target_ref is not None
        del self._entities[command.target_ref]
        self._revision += 1
        return command.target_ref

    def _save_workspace(self, command: CADCommand) -> str:
        path = self._resolve_workspace_path(command.payload.get("path") or "workspace.json")
        self._saved_revision = self._revision
        rel_path = path.relative_to(self.workspace_root).as_posix()
        self._saved_artifacts.add(rel_path)
        data = _snapshot_dict(self._snapshot())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return rel_path

    def _checkpoint_workspace(self, command: CADCommand) -> str:
        checkpoint_id = _string_payload(command, "checkpoint_id", default=command.target_ref or command.command_id)
        self._checkpoints[checkpoint_id] = (
            copy.deepcopy(self._entities),
            self._revision,
            self._saved_revision,
            self._rebuild_count,
        )
        path_value = command.payload.get("path")
        if path_value is not None:
            path = self._resolve_workspace_path(path_value)
            self._saved_artifacts.add(path.relative_to(self.workspace_root).as_posix())
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(_snapshot_dict(self._snapshot()), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return checkpoint_id

    def _rollback_workspace(self, command: CADCommand) -> str:
        checkpoint_id = _string_payload(command, "checkpoint_id", default=command.target_ref)
        entities, revision, saved_revision, rebuild_count = self._checkpoints[checkpoint_id]
        del revision
        current_revision = self._revision
        self._entities = copy.deepcopy(entities)
        self._revision = current_revision + 1
        self._saved_revision = saved_revision
        self._rebuild_count = rebuild_count
        return checkpoint_id

    def _snapshot(self) -> CADWorkspaceSnapshot:
        entities = tuple(copy.deepcopy(self._entities[key]) for key in sorted(self._entities))
        body = {
            "workspace_id": self.workspace_id,
            "revision": self._revision,
            "saved_revision": self._saved_revision,
            "rebuild_count": self._rebuild_count,
            "entities": entities,
            "saved_artifacts": tuple(sorted(self._saved_artifacts)),
        }
        snapshot_id = "cadss_" + hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        ).hexdigest()[:32]
        return CADWorkspaceSnapshot(
            snapshot_id=snapshot_id,
            workspace_id=self.workspace_id,
            revision=self._revision,
            saved_revision=self._saved_revision,
            rebuild_count=self._rebuild_count,
            entities=entities,
            saved_artifacts=tuple(sorted(self._saved_artifacts)),
        )

    def _resolve_workspace_path(self, value: object) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("workspace path must be a non-empty relative string")
        candidate = Path(value)
        if candidate.is_absolute():
            raise ValueError("workspace path must be relative")
        resolved = (self.workspace_root / candidate).resolve()
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError as exc:
            raise ValueError("workspace path escapes the session workspace") from exc
        return resolved


def _receipt_status(results: list[CADOperationResult], failures: list[CADFailure]) -> str:
    if not failures:
        return "success"
    if results and any(result.status == "ok" for result in results):
        return "partial_failure"
    return "failed"


def _entity_ref_for(command: CADCommand) -> str:
    explicit = command.payload.get("entity_ref") or command.target_ref
    if explicit is not None:
        if not isinstance(explicit, str) or not explicit.strip():
            raise ValueError("entity_ref must be a non-empty string")
        return explicit
    source = command.idempotency_key or command.command_id
    return "ent_" + hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


def _string_payload(command: CADCommand, key: str, *, default: object = None) -> str:
    value = command.payload.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _json_value(value: object) -> Any:
    encoded = json.dumps(value, sort_keys=True, allow_nan=False)
    return json.loads(encoded)


def _snapshot_dict(snapshot: CADWorkspaceSnapshot) -> dict[str, Any]:
    return {
        "snapshot_id": snapshot.snapshot_id,
        "workspace_id": snapshot.workspace_id,
        "revision": snapshot.revision,
        "saved_revision": snapshot.saved_revision,
        "rebuild_count": snapshot.rebuild_count,
        "entities": list(snapshot.entities),
        "saved_artifacts": list(snapshot.saved_artifacts),
    }


def _entity_map(snapshot: CADWorkspaceSnapshot) -> dict[str, Mapping[str, Any]]:
    return {str(entity["entity_ref"]): entity for entity in snapshot.entities}


def _diff_snapshots(before: CADWorkspaceSnapshot, after: CADWorkspaceSnapshot) -> CADChangeSet:
    before_entities = _entity_map(before)
    after_entities = _entity_map(after)
    before_refs = set(before_entities)
    after_refs = set(after_entities)
    created = tuple(sorted(after_refs - before_refs))
    deleted = tuple(sorted(before_refs - after_refs))
    modified = tuple(
        ref
        for ref in sorted(before_refs & after_refs)
        if json.dumps(before_entities[ref], sort_keys=True) != json.dumps(after_entities[ref], sort_keys=True)
    )
    metadata: dict[str, Any] = {}
    if before.rebuild_count != after.rebuild_count:
        metadata["rebuild_count_delta"] = after.rebuild_count - before.rebuild_count
    if before.saved_artifacts != after.saved_artifacts:
        metadata["saved_artifacts"] = tuple(path for path in after.saved_artifacts if path not in before.saved_artifacts)
    return CADChangeSet(
        before_snapshot_id=before.snapshot_id,
        after_snapshot_id=after.snapshot_id,
        created_refs=created,
        modified_refs=modified,
        deleted_refs=deleted,
        metadata=metadata,
    )
