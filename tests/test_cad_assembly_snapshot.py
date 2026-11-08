import sys
from pathlib import Path
import unittest
from dataclasses import replace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dios.cad_assembly_snapshot import (
    AssemblySnapshot, Component, ComponentState, NativeMate, Page, SnapshotError,
    SourceRevision, capture_snapshot, establish_motion_baseline, verify_baseline_receipt,
)

SOURCE = SourceRevision("synthetic", "assembly", "r1")
IDENTITY = (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
COMPONENT = Component("occ-1", "part", ComponentState.FREE, IDENTITY, SOURCE)


class Reader:
    def __init__(self):
        self.components = {None: Page(SOURCE, (COMPONENT,), 1)}
        self.mates = {None: Page(SOURCE, (), 0)}
        self.revisions = [SOURCE, SOURCE]
        self.calls = []

    def read_revision(self):
        return self.revisions.pop(0) if len(self.revisions) > 1 else self.revisions[0]

    def list_components(self, source, cursor):
        self.calls.append(("components", cursor))
        return self.components[cursor]

    def list_mates(self, source, cursor):
        self.calls.append(("mates", cursor))
        return self.mates[cursor]


class SnapshotTests(unittest.TestCase):
    def test_baseline_and_consumer(self):
        reader = Reader()
        receipt = establish_motion_baseline(reader, SOURCE, ("occ-1",))
        self.assertEqual(verify_baseline_receipt(receipt, reader, SOURCE, ("occ-1",)),
                         receipt.snapshot)
        self.assertEqual(len(receipt.evidence_digest), 64)

    def test_component_pagination_and_shared_native_part(self):
        reader = Reader()
        other = replace(COMPONENT, occurrence_id="occ-2")
        reader.components = {None: Page(SOURCE, (COMPONENT,), 2, "next"),
                             "next": Page(SOURCE, (other,), 2)}
        self.assertEqual(len(capture_snapshot(reader, SOURCE).components), 2)
        self.assertIn(("components", "next"), reader.calls)

    def test_mates_exhausted_before_gate(self):
        reader = Reader()
        mate = NativeMate("m1", ("occ-1",), "ground", SOURCE)
        reader.mates = {None: Page(SOURCE, (mate,), 2, "next"),
                        "next": Page(SOURCE, (replace(mate, mate_id="m2"),), 2)}
        with self.assertRaises(SnapshotError):
            capture_snapshot(reader, SOURCE)
        self.assertIn(("mates", "next"), reader.calls)

    def test_all_nonfree_and_unknown_states(self):
        for state in (*ComponentState, None, "free", "unexpected", True):
            if state is ComponentState.FREE:
                continue
            with self.subTest(state=state):
                self.assert_component_rejected(replace(COMPONENT, state=state))

    def assert_component_rejected(self, component):
        reader = Reader()
        reader.components[None] = Page(SOURCE, (component,), 1)
        with self.assertRaises(SnapshotError):
            capture_snapshot(reader, SOURCE)

    def test_component_identity_revision_and_transform_failures(self):
        for changes in ({"occurrence_id": ""}, {"native_id": None},
                        {"source": replace(SOURCE, revision="old")},
                        {"transform": IDENTITY[:-1]},
                        {"transform": list(IDENTITY)}):
            with self.subTest(changes=changes):
                self.assert_component_rejected(replace(COMPONENT, **changes))
        for index, value in ((0, float("nan")), (1, float("inf")), (0, True),
                             (0, 2), (0, -1), (12, 1), (15, 0), (1, .1)):
            values = list(IDENTITY)
            values[index] = value
            with self.subTest(index=index, value=value):
                self.assert_component_rejected(replace(COMPONENT, transform=tuple(values)))

    def test_pagination_failures(self):
        cases = [
            {None: Page(SOURCE, (COMPONENT,), 2)},
            {None: Page(SOURCE, (COMPONENT,), 0)},
            {None: Page(SOURCE, (), 1, "next")},
            {None: Page(SOURCE, (COMPONENT,), True)},
            {None: Page(SOURCE, (COMPONENT,), 2, "")},
            {None: Page(SOURCE, (COMPONENT,), 2, "x"), "x": Page(SOURCE, (), 3)},
            {None: Page(SOURCE, (COMPONENT,), 2, "x"),
             "x": Page(SOURCE, (COMPONENT,), 2, "x")},
            {None: Page(replace(SOURCE, revision="old"), (COMPONENT,), 1)},
            {None: Page(SOURCE, [COMPONENT], 1)},
            {None: Page(SOURCE, (COMPONENT, COMPONENT), 2)},
        ]
        for pages in cases:
            with self.subTest(pages=pages):
                reader = Reader()
                reader.components = pages
                with self.assertRaises(SnapshotError):
                    capture_snapshot(reader, SOURCE)

    def test_bounds_and_source_race(self):
        for limits in ({"max_pages": 0}, {"max_items": True}, {"max_items": 0}):
            with self.assertRaises(SnapshotError):
                capture_snapshot(Reader(), SOURCE, **limits)
        reader = Reader()
        reader.components = {None: Page(SOURCE, (COMPONENT,), 2, "x")}
        with self.assertRaises(SnapshotError):
            capture_snapshot(reader, SOURCE, max_pages=1)
        reader = Reader()
        reader.revisions = [SOURCE, replace(SOURCE, revision="r2")]
        with self.assertRaises(SnapshotError):
            capture_snapshot(reader, SOURCE)
        with self.assertRaises(SnapshotError):
            capture_snapshot(Reader(), replace(SOURCE, assembly_id="other"))

    def test_receipt_rejects_boolean_tamper_stale_and_selection(self):
        receipt = establish_motion_baseline(Reader(), SOURCE, ("occ-1",))
        for candidate in (True, replace(receipt, evidence_digest="fake"),
                          replace(receipt, contract_version="future"),
                          replace(receipt, snapshot=AssemblySnapshot(SOURCE, (), ()))):
            with self.subTest(candidate=candidate):
                with self.assertRaises(SnapshotError):
                    verify_baseline_receipt(candidate, Reader(), SOURCE, ("occ-1",))
        for moving in ((), ("missing",), ("occ-1", "occ-1"), ["occ-1"]):
            with self.assertRaises(SnapshotError):
                establish_motion_baseline(Reader(), SOURCE, moving)
        with self.assertRaises(SnapshotError):
            verify_baseline_receipt(receipt, Reader(), SOURCE, ("other",))
        reader = Reader()
        values = list(IDENTITY)
        values[3] = 1
        reader.components[None] = Page(SOURCE, (replace(COMPONENT, transform=tuple(values)),), 1)
        with self.assertRaises(SnapshotError):
            verify_baseline_receipt(receipt, reader, SOURCE, ("occ-1",))

    def test_mate_malformed_duplicate_and_dangling_fail_closed(self):
        mate = NativeMate("mate", ("occ-1",), "ground", SOURCE)
        for mates in ((mate, mate), (replace(mate, occurrence_ids=("missing",)),),
                      (replace(mate, source=replace(SOURCE, revision="old")),),
                      (replace(mate, occurrence_ids=("occ-1", "occ-1")),),
                      (replace(mate, kind=""),)):
            reader = Reader()
            reader.mates[None] = Page(SOURCE, mates, len(mates))
            with self.assertRaises(SnapshotError):
                capture_snapshot(reader, SOURCE)


if __name__ == "__main__":
    unittest.main()
