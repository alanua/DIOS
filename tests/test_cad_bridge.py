from __future__ import annotations

import json
from pathlib import Path

from core.cad_bridge import (
    CADCommand,
    CADCommandBatch,
    CADSessionGrant,
    CAPABILITY_CREATE,
    CAPABILITY_SAVE,
    FULL_CAD_WORKSPACE,
    SyntheticCADAdapter,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "cad_bridge.schema.json"


def adapter_and_grant(tmp_path: Path):
    adapter = SyntheticCADAdapter(workspace_id="workspace-alpha", workspace_root=tmp_path)
    return adapter, adapter.grant(session_id="session-001")


def create_wall(command_id: str = "cmd-create", entity_ref: str = "wall-001") -> CADCommand:
    return CADCommand(
        command_id=command_id,
        operation="create",
        payload={
            "entity_ref": entity_ref,
            "type": "wall",
            "geometry": {"start": [0, 0], "end": [4, 0]},
            "properties": {"height_m": 2.7},
        },
    )


def test_schema_file_exists() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["$defs"]["CADTransactionReceipt"]["properties"]["status"]["enum"] == [
        "success",
        "partial_failure",
        "failed",
    ]
    for contract in (
        "CADSessionGrant",
        "CADCapabilityProfile",
        "CADCommand",
        "CADCommandBatch",
        "CADOperationResult",
        "CADWorkspaceSnapshot",
        "CADChangeSet",
        "CADValidationResult",
        "CADTransactionReceipt",
        "CADFailure",
    ):
        assert contract in schema["$defs"]


def test_capability_discovery_is_provider_neutral_and_no_live_runtime(tmp_path: Path) -> None:
    adapter = SyntheticCADAdapter(workspace_id="workspace-alpha", workspace_root=tmp_path)
    profile = adapter.capability_profile()

    assert profile.provider_id == "synthetic.in_process"
    assert profile.provider_kind == "synthetic"
    assert profile.live_runtime_execution is False
    assert set(profile.operations) >= {"create", "modify", "delete", "rebuild", "save", "checkpoint", "rollback"}


def test_create_modify_delete_rebuild_and_save_have_deterministic_snapshots(tmp_path: Path) -> None:
    adapter, grant = adapter_and_grant(tmp_path)
    receipt = adapter.execute_batch(
        grant,
        CADCommandBatch(
            batch_id="batch-main",
            commands=(
                create_wall(),
                CADCommand(
                    command_id="cmd-modify",
                    operation="modify",
                    target_ref="wall-001",
                    payload={"properties": {"fire_rating": "synthetic-60"}},
                ),
                CADCommand(command_id="cmd-rebuild", operation="rebuild"),
                CADCommand(command_id="cmd-save", operation="save", payload={"path": "exports/model.json"}),
            ),
        ),
    )

    assert receipt.status == "success"
    assert receipt.change_set.created_refs == ("wall-001",)
    assert receipt.after_snapshot.revision == 3
    assert receipt.after_snapshot.saved_revision == 3
    assert receipt.after_snapshot.rebuild_count == 1
    saved = json.loads((tmp_path / "exports" / "model.json").read_text(encoding="utf-8"))
    assert saved["snapshot_id"] == receipt.operation_results[-1].after_snapshot.snapshot_id
    assert saved["saved_revision"] == 3
    assert saved["entities"][0]["properties"] == {"fire_rating": "synthetic-60", "height_m": 2.7}

    repeated = adapter.snapshot()
    assert repeated.snapshot_id == adapter.snapshot().snapshot_id

    delete = adapter.execute(grant, CADCommand(command_id="cmd-delete", operation="delete", target_ref="wall-001"))
    assert delete.status == "ok"
    assert delete.change_set.deleted_refs == ("wall-001",)


def test_checkpoint_and_rollback_restore_workspace_with_receipt_changes(tmp_path: Path) -> None:
    adapter, grant = adapter_and_grant(tmp_path)
    first = adapter.execute_batch(
        grant,
        CADCommandBatch(
            batch_id="batch-checkpoint",
            commands=(
                create_wall(entity_ref="wall-001"),
                CADCommand(command_id="cmd-checkpoint", operation="checkpoint", payload={"checkpoint_id": "cp-clean"}),
                CADCommand(command_id="cmd-extra", operation="create", payload={"entity_ref": "door-001", "type": "door"}),
                CADCommand(
                    command_id="cmd-wall-change",
                    operation="modify",
                    target_ref="wall-001",
                    payload={"properties": {"height_m": 3.0}},
                ),
            ),
        ),
    )
    assert first.status == "success"
    assert {entity["entity_ref"] for entity in first.after_snapshot.entities} == {"wall-001", "door-001"}

    rollback = adapter.execute(
        grant,
        CADCommand(command_id="cmd-rollback", operation="rollback", payload={"checkpoint_id": "cp-clean"}),
    )

    assert rollback.status == "ok"
    assert rollback.change_set.deleted_refs == ("door-001",)
    assert rollback.change_set.modified_refs == ("wall-001",)
    assert [entity["entity_ref"] for entity in rollback.after_snapshot.entities] == ["wall-001"]
    assert rollback.after_snapshot.entities[0]["properties"] == {"height_m": 2.7}


def test_batch_partial_failure_receipt_continues_after_failed_command(tmp_path: Path) -> None:
    adapter, grant = adapter_and_grant(tmp_path)
    receipt = adapter.execute_batch(
        grant,
        CADCommandBatch(
            batch_id="batch-partial",
            commands=(
                create_wall(entity_ref="wall-001"),
                CADCommand(command_id="cmd-missing", operation="modify", target_ref="missing"),
                CADCommand(command_id="cmd-door", operation="create", payload={"entity_ref": "door-001", "type": "door"}),
            ),
        ),
    )

    assert receipt.status == "partial_failure"
    assert receipt.validation.status == "failed"
    assert [result.status for result in receipt.operation_results] == ["ok", "failed", "ok"]
    assert receipt.operation_results[1].failure is not None
    assert receipt.operation_results[1].failure.code == "TARGET_NOT_FOUND"
    assert receipt.change_set.created_refs == ("door-001", "wall-001")


def test_unsupported_capability_fails_explicitly_without_mutating(tmp_path: Path) -> None:
    adapter, grant = adapter_and_grant(tmp_path)
    result = adapter.execute(
        grant,
        CADCommand(command_id="cmd-provider-only", operation="create", required_capability="provider.private_macro"),
    )

    assert result.status == "failed"
    assert result.failure is not None
    assert result.failure.code == "CAPABILITY_UNSUPPORTED"
    assert result.before_snapshot.snapshot_id == result.after_snapshot.snapshot_id
    assert result.after_snapshot.entities == ()


def test_grant_capability_subset_blocks_ungranted_operation_without_per_operation_approval(tmp_path: Path) -> None:
    adapter = SyntheticCADAdapter(workspace_id="workspace-alpha", workspace_root=tmp_path)
    grant = adapter.grant(session_id="session-001", capabilities=(CAPABILITY_CREATE,))

    created = adapter.execute(grant, create_wall())
    blocked = adapter.execute(
        grant,
        CADCommand(command_id="cmd-save", operation="save", required_capability=CAPABILITY_SAVE),
    )

    assert created.status == "ok"
    assert blocked.status == "failed"
    assert blocked.failure is not None
    assert blocked.failure.code == "CAPABILITY_NOT_GRANTED"
    assert "approval" not in blocked.failure.message.lower()


def test_workspace_boundary_enforced_for_session_and_paths(tmp_path: Path) -> None:
    adapter, grant = adapter_and_grant(tmp_path)
    wrong_workspace = CADSessionGrant(
        session_id="session-002",
        workspace_id="other",
        workspace_root=str(tmp_path),
        scope=FULL_CAD_WORKSPACE,
    )
    wrong_receipt = adapter.execute_batch(
        wrong_workspace,
        CADCommandBatch(batch_id="wrong-workspace", commands=(create_wall(),)),
    )
    assert wrong_receipt.status == "failed"
    assert wrong_receipt.validation.failures[0].code == "WORKSPACE_MISMATCH"

    escaped = adapter.execute(
        grant,
        CADCommand(command_id="cmd-escape", operation="save", payload={"path": "../outside.json"}),
    )
    assert escaped.status == "failed"
    assert escaped.failure is not None
    assert escaped.failure.code == "WORKSPACE_BOUNDARY_VIOLATION"
    assert not (tmp_path.parent / "outside.json").exists()


def test_single_execute_returns_typed_failure_for_invalid_session(tmp_path: Path) -> None:
    adapter, _grant = adapter_and_grant(tmp_path)
    wrong_workspace = CADSessionGrant(
        session_id="session-002",
        workspace_id="other",
        workspace_root=str(tmp_path),
        scope=FULL_CAD_WORKSPACE,
    )

    result = adapter.execute(wrong_workspace, create_wall())

    assert result.status == "failed"
    assert result.failure is not None
    assert result.failure.code == "WORKSPACE_MISMATCH"
    assert result.before_snapshot.snapshot_id == result.after_snapshot.snapshot_id
    assert adapter.snapshot().entities == ()


def test_invalid_payload_fails_without_mutating_workspace(tmp_path: Path) -> None:
    adapter, grant = adapter_and_grant(tmp_path)

    result = adapter.execute(
        grant,
        CADCommand(
            command_id="cmd-invalid-payload",
            operation="create",
            payload={"entity_ref": "wall-001", "properties": ["not", "an", "object"]},
        ),
    )

    assert result.status == "failed"
    assert result.failure is not None
    assert result.failure.code == "PAYLOAD_INVALID"
    assert result.before_snapshot.snapshot_id == result.after_snapshot.snapshot_id
    assert adapter.snapshot().entities == ()
