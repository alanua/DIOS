from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
from typing import Any, Protocol


JsonObject = dict[str, Any]


class CadCommandType(StrEnum):
    CREATE_ENTITY = "CREATE_ENTITY"
    UPDATE_ENTITY = "UPDATE_ENTITY"
    DELETE_ENTITY = "DELETE_ENTITY"


class CadCommandStatus(StrEnum):
    APPLIED = "APPLIED"
    FAILED = "FAILED"
    UNAUTHORIZED = "UNAUTHORIZED"
    ROLLED_BACK = "ROLLED_BACK"


class CadBridgeError(ValueError):
    """Raised when a CAD bridge request is malformed."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def deterministic_digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sorted_entities(entities: dict[str, JsonObject]) -> dict[str, JsonObject]:
    return {entity_id: deepcopy(entities[entity_id]) for entity_id in sorted(entities)}


@dataclass(frozen=True)
class CadMutationAuthority:
    session_id: str
    workspace_id: str
    scopes: frozenset[str]
    approved_by: str
    approval_reference: str

    def __post_init__(self) -> None:
        if not self.session_id.strip():
            raise CadBridgeError("authority.session_id is required")
        if not self.workspace_id.strip():
            raise CadBridgeError("authority.workspace_id is required")
        scopes = frozenset(self.scopes)
        if not scopes:
            raise CadBridgeError("authority.scopes requires at least one scope")
        if any(not scope.strip() for scope in scopes):
            raise CadBridgeError("authority.scopes cannot contain blank scopes")
        if not self.approved_by.strip():
            raise CadBridgeError("authority.approved_by is required")
        if not self.approval_reference.strip():
            raise CadBridgeError("authority.approval_reference is required")
        object.__setattr__(self, "scopes", scopes)

    @classmethod
    def grant(
        cls,
        *,
        session_id: str,
        workspace_id: str,
        scopes: set[str] | frozenset[str],
        approved_by: str,
        approval_reference: str,
    ) -> CadMutationAuthority:
        return cls(
            session_id=session_id,
            workspace_id=workspace_id,
            scopes=frozenset(scopes),
            approved_by=approved_by,
            approval_reference=approval_reference,
        )

    def receipt_payload(self) -> JsonObject:
        return {
            "approval_reference": self.approval_reference,
            "approved_by": self.approved_by,
            "scopes": sorted(self.scopes),
            "session_id": self.session_id,
            "workspace_id": self.workspace_id,
        }


@dataclass(frozen=True)
class CadWorkspaceSnapshot:
    workspace_id: str
    provider: str
    revision: int
    entities: dict[str, JsonObject]

    def to_dict(self) -> JsonObject:
        return {
            "entities": _sorted_entities(self.entities),
            "provider": self.provider,
            "revision": self.revision,
            "workspace_id": self.workspace_id,
        }

    @property
    def digest(self) -> str:
        return deterministic_digest(self.to_dict())


@dataclass(frozen=True)
class CadCommand:
    command_id: str
    command_type: CadCommandType
    target_id: str
    scope: str
    payload: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "command_type", CadCommandType(self.command_type))
        if not self.command_id.strip():
            raise CadBridgeError("command.command_id is required")
        if not self.target_id.strip():
            raise CadBridgeError("command.target_id is required")
        if not self.scope.strip():
            raise CadBridgeError("command.scope is required")
        if not isinstance(self.payload, dict):
            raise CadBridgeError("command.payload must be a dict")

    def to_dict(self) -> JsonObject:
        return {
            "command_id": self.command_id,
            "command_type": self.command_type.value,
            "payload": deepcopy(self.payload),
            "scope": self.scope,
            "target_id": self.target_id,
        }

    @property
    def digest(self) -> str:
        return deterministic_digest(self.to_dict())


@dataclass(frozen=True)
class CadCommandResult:
    command_id: str
    status: CadCommandStatus
    message: str
    before_digest: str
    after_digest: str
    receipt: str

    @property
    def success(self) -> bool:
        return self.status is CadCommandStatus.APPLIED

    @property
    def rolled_back(self) -> bool:
        return self.status is CadCommandStatus.ROLLED_BACK

    def to_dict(self) -> JsonObject:
        return {
            "after_digest": self.after_digest,
            "before_digest": self.before_digest,
            "command_id": self.command_id,
            "message": self.message,
            "receipt": self.receipt,
            "status": self.status.value,
        }


@dataclass(frozen=True)
class CadCommandBatch:
    batch_id: str
    commands: tuple[CadCommand, ...]
    rollback_on_failure: bool = True

    def __post_init__(self) -> None:
        if not self.batch_id.strip():
            raise CadBridgeError("batch.batch_id is required")
        object.__setattr__(self, "commands", tuple(self.commands))
        if not self.commands:
            raise CadBridgeError("batch.commands requires at least one command")

    @classmethod
    def from_commands(
        cls,
        batch_id: str,
        commands: list[CadCommand] | tuple[CadCommand, ...],
        *,
        rollback_on_failure: bool = True,
    ) -> CadCommandBatch:
        return cls(batch_id=batch_id, commands=tuple(commands), rollback_on_failure=rollback_on_failure)

    def to_dict(self) -> JsonObject:
        return {
            "batch_id": self.batch_id,
            "commands": [command.to_dict() for command in self.commands],
            "rollback_on_failure": self.rollback_on_failure,
        }


@dataclass(frozen=True)
class CadBatchResult:
    batch_id: str
    success: bool
    rolled_back: bool
    before_digest: str
    after_digest: str
    results: tuple[CadCommandResult, ...]
    receipt: str

    def to_dict(self) -> JsonObject:
        return {
            "after_digest": self.after_digest,
            "batch_id": self.batch_id,
            "before_digest": self.before_digest,
            "receipt": self.receipt,
            "results": [result.to_dict() for result in self.results],
            "rolled_back": self.rolled_back,
            "success": self.success,
        }


class CadAdapter(Protocol):
    provider: str
    workspace_id: str

    def snapshot(self) -> CadWorkspaceSnapshot:
        ...

    def apply_command(self, command: CadCommand) -> CadCommandResult:
        ...

    def restore(self, snapshot: CadWorkspaceSnapshot) -> None:
        ...


class SyntheticMutableCadAdapter:
    """Provider-neutral mutable adapter used for deterministic tests and local orchestration."""

    provider = "synthetic"

    def __init__(self, workspace_id: str, entities: dict[str, JsonObject] | None = None) -> None:
        if not workspace_id.strip():
            raise CadBridgeError("workspace_id is required")
        self.workspace_id = workspace_id
        self._entities: dict[str, JsonObject] = deepcopy(entities) if entities else {}
        self._revision = 0

    def snapshot(self) -> CadWorkspaceSnapshot:
        return CadWorkspaceSnapshot(
            workspace_id=self.workspace_id,
            provider=self.provider,
            revision=self._revision,
            entities=_sorted_entities(self._entities),
        )

    def restore(self, snapshot: CadWorkspaceSnapshot) -> None:
        if snapshot.workspace_id != self.workspace_id:
            raise CadBridgeError("cannot restore snapshot from a different workspace")
        self._entities = _sorted_entities(snapshot.entities)
        self._revision = snapshot.revision

    def entity(self, entity_id: str) -> JsonObject | None:
        entity = self._entities.get(entity_id)
        return deepcopy(entity) if entity is not None else None

    def apply_command(self, command: CadCommand) -> CadCommandResult:
        before = self.snapshot()
        status = CadCommandStatus.APPLIED
        message = "applied"

        try:
            self._apply(command)
        except CadBridgeError as exc:
            status = CadCommandStatus.FAILED
            message = str(exc)

        after = self.snapshot()
        receipt = self._command_receipt(command, status, message, before.digest, after.digest)
        return CadCommandResult(
            command_id=command.command_id,
            status=status,
            message=message,
            before_digest=before.digest,
            after_digest=after.digest,
            receipt=receipt,
        )

    def _apply(self, command: CadCommand) -> None:
        if command.command_type is CadCommandType.CREATE_ENTITY:
            if command.target_id in self._entities:
                raise CadBridgeError(f"entity already exists: {command.target_id}")
            if "type" not in command.payload:
                raise CadBridgeError("CREATE_ENTITY payload requires type")
            self._entities[command.target_id] = deepcopy(command.payload)
            self._revision += 1
            return

        if command.command_type is CadCommandType.UPDATE_ENTITY:
            if command.target_id not in self._entities:
                raise CadBridgeError(f"entity not found: {command.target_id}")
            self._entities[command.target_id].update(deepcopy(command.payload))
            self._revision += 1
            return

        if command.command_type is CadCommandType.DELETE_ENTITY:
            if command.target_id not in self._entities:
                raise CadBridgeError(f"entity not found: {command.target_id}")
            del self._entities[command.target_id]
            self._revision += 1
            return

        raise CadBridgeError(f"unsupported command type: {command.command_type}")

    def _command_receipt(
        self,
        command: CadCommand,
        status: CadCommandStatus,
        message: str,
        before_digest: str,
        after_digest: str,
    ) -> str:
        return deterministic_digest(
            {
                "after_digest": after_digest,
                "before_digest": before_digest,
                "command": command.to_dict(),
                "message": message,
                "provider": self.provider,
                "status": status.value,
                "workspace_id": self.workspace_id,
            }
        )


@dataclass
class CadBridgeSession:
    session_id: str
    adapter: CadAdapter

    def __post_init__(self) -> None:
        if not self.session_id.strip():
            raise CadBridgeError("session.session_id is required")

    @property
    def workspace_id(self) -> str:
        return self.adapter.workspace_id

    def snapshot(self) -> CadWorkspaceSnapshot:
        return self.adapter.snapshot()

    def execute(self, batch: CadCommandBatch, authority: CadMutationAuthority) -> CadBatchResult:
        self._assert_authority(authority)
        initial = self.adapter.snapshot()
        results: list[CadCommandResult] = []
        failed = False

        for command in batch.commands:
            if command.scope not in authority.scopes:
                before = self.adapter.snapshot()
                result = self._unauthorized_result(command, before, authority)
            else:
                result = self.adapter.apply_command(command)
            results.append(result)
            if not result.success:
                failed = True
                if batch.rollback_on_failure:
                    self.adapter.restore(initial)
                    results = self._mark_applied_results_rolled_back(results, initial.digest)
                    break

        final = self.adapter.snapshot()
        rolled_back = failed and batch.rollback_on_failure
        success = not failed
        receipt = deterministic_digest(
            {
                "after_digest": final.digest,
                "authority": authority.receipt_payload(),
                "batch": batch.to_dict(),
                "before_digest": initial.digest,
                "results": [result.to_dict() for result in results],
                "rolled_back": rolled_back,
                "success": success,
            }
        )
        return CadBatchResult(
            batch_id=batch.batch_id,
            success=success,
            rolled_back=rolled_back,
            before_digest=initial.digest,
            after_digest=final.digest,
            results=tuple(results),
            receipt=receipt,
        )

    def execute_batch(self, batch: CadCommandBatch, authority: CadMutationAuthority) -> CadBatchResult:
        return self.execute(batch, authority)

    def _assert_authority(self, authority: CadMutationAuthority) -> None:
        if authority.session_id != self.session_id:
            raise CadBridgeError("authority is not scoped to this session")
        if authority.workspace_id != self.workspace_id:
            raise CadBridgeError("authority is not scoped to this workspace")

    def _unauthorized_result(
        self,
        command: CadCommand,
        snapshot: CadWorkspaceSnapshot,
        authority: CadMutationAuthority,
    ) -> CadCommandResult:
        message = f"scope not authorized: {command.scope}"
        receipt = deterministic_digest(
            {
                "authority": authority.receipt_payload(),
                "command": command.to_dict(),
                "digest": snapshot.digest,
                "message": message,
                "status": CadCommandStatus.UNAUTHORIZED.value,
            }
        )
        return CadCommandResult(
            command_id=command.command_id,
            status=CadCommandStatus.UNAUTHORIZED,
            message=message,
            before_digest=snapshot.digest,
            after_digest=snapshot.digest,
            receipt=receipt,
        )

    def _mark_applied_results_rolled_back(
        self,
        results: list[CadCommandResult],
        restored_digest: str,
    ) -> list[CadCommandResult]:
        marked: list[CadCommandResult] = []
        for result in results:
            if result.status is not CadCommandStatus.APPLIED:
                marked.append(result)
                continue
            receipt = deterministic_digest(
                {
                    "command_id": result.command_id,
                    "original_receipt": result.receipt,
                    "restored_digest": restored_digest,
                    "status": CadCommandStatus.ROLLED_BACK.value,
                }
            )
            marked.append(
                CadCommandResult(
                    command_id=result.command_id,
                    status=CadCommandStatus.ROLLED_BACK,
                    message="rolled back after batch failure",
                    before_digest=result.before_digest,
                    after_digest=restored_digest,
                    receipt=receipt,
                )
            )
        return marked
