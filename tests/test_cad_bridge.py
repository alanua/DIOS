import unittest

from dios import (
    CadBridgeError,
    CadBridgeSession,
    CadCommand,
    CadCommandBatch,
    CadCommandStatus,
    CadCommandType,
    CadMutationAuthority,
    CadWorkspaceSnapshot,
    SyntheticMutableCadAdapter,
)


class CadBridgeTests(unittest.TestCase):
    def authority(self, session_id: str = "session-1", scopes: set[str] | None = None) -> CadMutationAuthority:
        return CadMutationAuthority.grant(
            session_id=session_id,
            workspace_id="workspace-1",
            scopes=scopes or {"model"},
            approved_by="reviewer",
            approval_reference="approval:123",
        )

    def test_session_scoped_authority_is_required(self) -> None:
        session = CadBridgeSession("session-1", SyntheticMutableCadAdapter("workspace-1"))
        batch = CadCommandBatch.from_commands(
            "batch-1",
            [
                CadCommand(
                    command_id="cmd-1",
                    command_type=CadCommandType.CREATE_ENTITY,
                    target_id="wall-1",
                    scope="model",
                    payload={"type": "wall"},
                )
            ],
        )

        with self.assertRaisesRegex(CadBridgeError, "session"):
            session.execute(batch, self.authority(session_id="other-session"))

    def test_synthetic_adapter_mutates_and_produces_deterministic_receipts(self) -> None:
        def run_once() -> tuple[str, str, str]:
            session = CadBridgeSession("session-1", SyntheticMutableCadAdapter("workspace-1"))
            batch = CadCommandBatch.from_commands(
                "batch-1",
                [
                    CadCommand(
                        command_id="cmd-1",
                        command_type=CadCommandType.CREATE_ENTITY,
                        target_id="room-1",
                        scope="model",
                        payload={"type": "room", "area": 12},
                    ),
                    CadCommand(
                        command_id="cmd-2",
                        command_type=CadCommandType.UPDATE_ENTITY,
                        target_id="room-1",
                        scope="model",
                        payload={"area": 14},
                    ),
                ],
            )
            result = session.execute(batch, self.authority())
            entity = session.adapter.entity("room-1")
            self.assertEqual(entity, {"type": "room", "area": 14})
            return result.after_digest, result.receipt, result.results[0].receipt

        self.assertEqual(run_once(), run_once())

    def test_partial_failure_without_rollback_reports_truth_and_keeps_prior_mutation(self) -> None:
        adapter = SyntheticMutableCadAdapter("workspace-1")
        session = CadBridgeSession("session-1", adapter)
        batch = CadCommandBatch.from_commands(
            "batch-1",
            [
                CadCommand(
                    command_id="cmd-1",
                    command_type=CadCommandType.CREATE_ENTITY,
                    target_id="door-1",
                    scope="model",
                    payload={"type": "door"},
                ),
                CadCommand(
                    command_id="cmd-2",
                    command_type=CadCommandType.DELETE_ENTITY,
                    target_id="missing",
                    scope="model",
                ),
            ],
            rollback_on_failure=False,
        )

        result = session.execute(batch, self.authority())

        self.assertFalse(result.success)
        self.assertFalse(result.rolled_back)
        self.assertEqual(result.results[0].status, CadCommandStatus.APPLIED)
        self.assertEqual(result.results[1].status, CadCommandStatus.FAILED)
        self.assertEqual(adapter.entity("door-1"), {"type": "door"})

    def test_rollback_restores_initial_snapshot_and_marks_applied_results(self) -> None:
        adapter = SyntheticMutableCadAdapter("workspace-1", {"existing": {"type": "line"}})
        session = CadBridgeSession("session-1", adapter)
        before = session.snapshot()
        batch = CadCommandBatch.from_commands(
            "batch-1",
            [
                CadCommand(
                    command_id="cmd-1",
                    command_type=CadCommandType.CREATE_ENTITY,
                    target_id="room-1",
                    scope="model",
                    payload={"type": "room"},
                ),
                CadCommand(
                    command_id="cmd-2",
                    command_type=CadCommandType.CREATE_ENTITY,
                    target_id="bad-entity",
                    scope="model",
                    payload={"area": 3},
                ),
            ],
            rollback_on_failure=True,
        )

        result = session.execute(batch, self.authority())

        self.assertFalse(result.success)
        self.assertTrue(result.rolled_back)
        self.assertEqual(result.before_digest, result.after_digest)
        self.assertEqual(result.after_digest, before.digest)
        self.assertEqual(result.results[0].status, CadCommandStatus.ROLLED_BACK)
        self.assertEqual(result.results[1].status, CadCommandStatus.FAILED)
        self.assertIsNone(adapter.entity("room-1"))
        self.assertEqual(adapter.entity("existing"), {"type": "line"})

    def test_unauthorized_command_scope_fails_closed(self) -> None:
        adapter = SyntheticMutableCadAdapter("workspace-1")
        session = CadBridgeSession("session-1", adapter)
        batch = CadCommandBatch.from_commands(
            "batch-1",
            [
                CadCommand(
                    command_id="cmd-1",
                    command_type=CadCommandType.CREATE_ENTITY,
                    target_id="wall-1",
                    scope="layout",
                    payload={"type": "wall"},
                )
            ],
            rollback_on_failure=False,
        )

        result = session.execute(batch, self.authority(scopes={"model"}))

        self.assertFalse(result.success)
        self.assertEqual(result.results[0].status, CadCommandStatus.UNAUTHORIZED)
        self.assertIsNone(adapter.entity("wall-1"))

    def test_command_payload_is_copied_and_json_safe(self) -> None:
        payload = {"type": "room", "metadata": {"level": 1}}
        command = CadCommand(
            command_id="cmd-1",
            command_type=CadCommandType.CREATE_ENTITY,
            target_id="room-1",
            scope="model",
            payload=payload,
        )

        payload["metadata"]["level"] = 2

        self.assertEqual(command.payload, {"type": "room", "metadata": {"level": 1}})
        with self.assertRaisesRegex(CadBridgeError, "JSON-serializable"):
            CadCommand(
                command_id="cmd-2",
                command_type=CadCommandType.CREATE_ENTITY,
                target_id="room-2",
                scope="model",
                payload={"bad": object()},
            )

    def test_bad_command_type_raises_bridge_error(self) -> None:
        with self.assertRaisesRegex(CadBridgeError, "unsupported command type"):
            CadCommand(
                command_id="cmd-1",
                command_type="MOVE_ENTITY",  # type: ignore[arg-type]
                target_id="room-1",
                scope="model",
            )

    def test_batch_rejects_duplicate_command_ids(self) -> None:
        commands = [
            CadCommand(
                command_id="cmd-1",
                command_type=CadCommandType.CREATE_ENTITY,
                target_id="room-1",
                scope="model",
                payload={"type": "room"},
            ),
            CadCommand(
                command_id="cmd-1",
                command_type=CadCommandType.DELETE_ENTITY,
                target_id="room-1",
                scope="model",
            ),
        ]

        with self.assertRaisesRegex(CadBridgeError, "duplicate command_id"):
            CadCommandBatch.from_commands("batch-1", commands)

    def test_snapshot_copies_entities_and_restore_requires_provider_match(self) -> None:
        entities = {"room-1": {"type": "room", "area": 12}}
        snapshot = CadWorkspaceSnapshot(
            workspace_id="workspace-1",
            provider="synthetic",
            revision=1,
            entities=entities,
        )
        entities["room-1"]["area"] = 20

        self.assertEqual(snapshot.entities["room-1"]["area"], 12)

        adapter = SyntheticMutableCadAdapter("workspace-1")
        with self.assertRaisesRegex(CadBridgeError, "different provider"):
            adapter.restore(
                CadWorkspaceSnapshot(
                    workspace_id="workspace-1",
                    provider="other-provider",
                    revision=1,
                    entities={"room-1": {"type": "room"}},
                )
            )

    def test_adapter_bridge_error_is_reported_as_failed_result(self) -> None:
        class RaisingAdapter(SyntheticMutableCadAdapter):
            def apply_command(self, command: CadCommand):  # type: ignore[no-untyped-def]
                raise CadBridgeError("provider rejected command")

        adapter = RaisingAdapter("workspace-1")
        session = CadBridgeSession("session-1", adapter)
        batch = CadCommandBatch.from_commands(
            "batch-1",
            [
                CadCommand(
                    command_id="cmd-1",
                    command_type=CadCommandType.CREATE_ENTITY,
                    target_id="room-1",
                    scope="model",
                    payload={"type": "room"},
                )
            ],
        )

        result = session.execute(batch, self.authority())

        self.assertFalse(result.success)
        self.assertTrue(result.rolled_back)
        self.assertEqual(result.results[0].status, CadCommandStatus.FAILED)
        self.assertEqual(result.results[0].message, "provider rejected command")


if __name__ == "__main__":
    unittest.main()
