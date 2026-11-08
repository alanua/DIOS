"""Read-only assembly evidence and a conservative motion-baseline gate.

No provider implementation or motion executor is supplied by this module.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
import hashlib
import json
import math
from typing import Protocol, TypeVar, Generic


class SnapshotError(ValueError):
    """Evidence is incomplete, inconsistent, or unsafe for a baseline."""


class ComponentState(StrEnum):
    FREE = "free"
    FIXED = "fixed"
    CONSTRAINED = "constrained"
    SUPPRESSED = "suppressed"
    UNRESOLVED = "unresolved"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SourceRevision:
    provider: str
    assembly_id: str
    revision: str


@dataclass(frozen=True)
class Component:
    occurrence_id: str
    native_id: str
    state: ComponentState
    transform: tuple[float, ...]
    source: SourceRevision


@dataclass(frozen=True)
class NativeMate:
    mate_id: str
    occurrence_ids: tuple[str, ...]
    kind: str
    source: SourceRevision


T = TypeVar("T")


@dataclass(frozen=True)
class Page(Generic[T]):
    source: SourceRevision
    items: tuple[T, ...]
    total: int
    next_cursor: str | None = None


class AssemblyReader(Protocol):
    """Adapter must expose revision-pinned, exhaustive occurrence-level lists."""

    def read_revision(self) -> SourceRevision: ...
    def list_components(self, source: SourceRevision, cursor: str | None) -> Page[Component]: ...
    def list_mates(self, source: SourceRevision, cursor: str | None) -> Page[NativeMate]: ...


@dataclass(frozen=True)
class AssemblySnapshot:
    source: SourceRevision
    components: tuple[Component, ...]
    mates: tuple[NativeMate, ...]


@dataclass(frozen=True)
class VerifiedBaselineReceipt:
    """Evidence container; consumers MUST call verify_baseline_receipt before use."""

    snapshot: AssemblySnapshot
    moving_occurrence_ids: tuple[str, ...]
    evidence_digest: str
    contract_version: str = "assembly-baseline-v1"


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _source(source: object) -> None:
    if type(source) is not SourceRevision or not all(
        _text(x) for x in (source.provider, source.assembly_id, source.revision)
    ):
        raise SnapshotError("invalid source revision")


def _transform(values: object) -> None:
    # Row-major homogeneous transform: right-handed orthonormal rotation,
    # translation in metres, mapping component-local into assembly coordinates.
    if type(values) is not tuple or len(values) != 16 or any(
        type(x) not in (int, float) or not math.isfinite(x) for x in values
    ):
        raise SnapshotError("invalid transform values")
    if any(abs(values[12 + i] - target) > 1e-9
           for i, target in enumerate((0, 0, 0, 1))):
        raise SnapshotError("invalid homogeneous transform")
    rows = [values[i:i + 3] for i in (0, 4, 8)]
    for i in range(3):
        for j in range(3):
            if abs(sum(a * b for a, b in zip(rows[i], rows[j])) - (i == j)) > 1e-9:
                raise SnapshotError("non-rigid transform")
    a, b, c = rows
    determinant = (a[0] * (b[1]*c[2] - b[2]*c[1])
                   - a[1] * (b[0]*c[2] - b[2]*c[0])
                   + a[2] * (b[0]*c[1] - b[1]*c[0]))
    if abs(determinant - 1) > 1e-9:
        raise SnapshotError("reflected transform")


def _collect(reader: AssemblyReader, source: SourceRevision, *, mates: bool,
             max_pages: int, max_items: int) -> tuple:
    cursor = None
    seen: set[str] = set()
    result: list = []
    total = None
    for _ in range(max_pages):
        page = (reader.list_mates(source, cursor) if mates
                else reader.list_components(source, cursor))
        if type(page) is not Page or page.source != source:
            raise SnapshotError("invalid page or changed source revision")
        if type(page.total) is not int or not 0 <= page.total <= max_items:
            raise SnapshotError("invalid page total")
        if total is not None and page.total != total:
            raise SnapshotError("inconsistent page total")
        total = page.total
        if type(page.items) is not tuple:
            raise SnapshotError("page items must be immutable")
        result.extend(page.items)
        if len(result) > total:
            raise SnapshotError("page total exceeded")
        if page.next_cursor is None:
            if len(result) != total:
                raise SnapshotError("truncated list")
            return tuple(result)
        if not page.items or not _text(page.next_cursor) or page.next_cursor in seen:
            raise SnapshotError("non-progressing pagination")
        seen.add(page.next_cursor)
        cursor = page.next_cursor
    raise SnapshotError("pagination limit exceeded")


def _validate(snapshot: AssemblySnapshot) -> None:
    if type(snapshot) is not AssemblySnapshot:
        raise SnapshotError("typed snapshot required")
    _source(snapshot.source)
    if type(snapshot.components) is not tuple or type(snapshot.mates) is not tuple:
        raise SnapshotError("immutable evidence required")
    ids: set[str] = set()
    for component in snapshot.components:
        if type(component) is not Component:
            raise SnapshotError("invalid component")
        if not _text(component.occurrence_id) or not _text(component.native_id):
            raise SnapshotError("ambiguous component identity")
        if component.occurrence_id in ids:
            raise SnapshotError("duplicate component occurrence")
        ids.add(component.occurrence_id)
        _source(component.source)
        if component.source != snapshot.source:
            raise SnapshotError("stale component")
        if type(component.state) is not ComponentState or component.state is not ComponentState.FREE:
            raise SnapshotError("component is not explicitly free")
        _transform(component.transform)
    mate_ids: set[str] = set()
    for mate in snapshot.mates:
        if type(mate) is not NativeMate or not _text(mate.mate_id) or not _text(mate.kind):
            raise SnapshotError("invalid native mate")
        _source(mate.source)
        if mate.source != snapshot.source or mate.mate_id in mate_ids:
            raise SnapshotError("stale or duplicate native mate")
        mate_ids.add(mate.mate_id)
        if (type(mate.occurrence_ids) is not tuple or not mate.occurrence_ids
                or any(not _text(x) or x not in ids for x in mate.occurrence_ids)
                or len(set(mate.occurrence_ids)) != len(mate.occurrence_ids)):
            raise SnapshotError("ambiguous native mate references")
    # No interpretation of native mate semantics or intended abstract joints.
    if snapshot.mates:
        raise SnapshotError("native mates prevent a free-motion baseline")


def capture_snapshot(reader: AssemblyReader, expected_source: SourceRevision, *,
                     max_pages: int = 1000, max_items: int = 100000) -> AssemblySnapshot:
    _source(expected_source)
    if any(type(x) is not int or x <= 0 for x in (max_pages, max_items)):
        raise SnapshotError("invalid pagination limits")
    before = reader.read_revision()
    _source(before)
    if before != expected_source:
        raise SnapshotError("source revision mismatch")
    components = _collect(reader, before, mates=False, max_pages=max_pages, max_items=max_items)
    mates = _collect(reader, before, mates=True, max_pages=max_pages, max_items=max_items)
    after = reader.read_revision()
    _source(after)
    if after != before:
        raise SnapshotError("source revision changed during capture")
    snapshot = AssemblySnapshot(before, components, mates)
    _validate(snapshot)
    return snapshot


def _moving(snapshot: AssemblySnapshot, moving: object) -> None:
    if (type(moving) is not tuple or not moving or any(not _text(x) for x in moving)
            or len(set(moving)) != len(moving)
            or not set(moving) <= {c.occurrence_id for c in snapshot.components}):
        raise SnapshotError("invalid or ambiguous motion selection")


def _digest(snapshot: AssemblySnapshot, moving: tuple[str, ...]) -> str:
    payload = {"contract": "assembly-baseline-v1", "snapshot": asdict(snapshot),
               "moving": moving}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False,
                                     separators=(",", ":")).encode()).hexdigest()


def establish_motion_baseline(reader: AssemblyReader, expected_source: SourceRevision,
                              moving_occurrence_ids: tuple[str, ...]) -> VerifiedBaselineReceipt:
    snapshot = capture_snapshot(reader, expected_source)
    _moving(snapshot, moving_occurrence_ids)
    return VerifiedBaselineReceipt(snapshot, moving_occurrence_ids,
                                   _digest(snapshot, moving_occurrence_ids))


def verify_baseline_receipt(receipt: VerifiedBaselineReceipt, reader: AssemblyReader,
                            expected_source: SourceRevision,
                            moving_occurrence_ids: tuple[str, ...]) -> AssemblySnapshot:
    """Revalidate evidence and recapture source before a follow-up executor acts.

    A digest detects altered evidence; it is not a signature or mutation authority.
    """
    if type(receipt) is not VerifiedBaselineReceipt or receipt.contract_version != "assembly-baseline-v1":
        raise SnapshotError("typed baseline receipt required")
    _validate(receipt.snapshot)
    _moving(receipt.snapshot, receipt.moving_occurrence_ids)
    if (receipt.snapshot.source != expected_source
            or receipt.moving_occurrence_ids != moving_occurrence_ids
            or receipt.evidence_digest != _digest(receipt.snapshot, receipt.moving_occurrence_ids)):
        raise SnapshotError("baseline evidence mismatch")
    current = capture_snapshot(reader, expected_source)
    if current != receipt.snapshot:
        raise SnapshotError("baseline no longer matches native evidence")
    return current
