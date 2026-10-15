"""Open-ended native CAD capability registry and bounded synthetic router.

No CAD host, SDK, shell, arbitrary reflection, user-supplied code or network path.
Real native handlers must be pre-registered by a separately approved, trusted
workstation provider module. A session grant is not cryptographic evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from collections.abc import Callable, Mapping
from copy import deepcopy
import json
import math
import re
import time
from typing import Any

_ID = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.:-]{0,127}$")
_VERSION = re.compile(r"^[0-9]{4}(?:\.[0-9]{1,3}){0,2}$")
_KINDS = frozenset({"string", "integer", "number", "boolean", "object", "array"})
_MAX_JSON = 65536


class CapabilityDenied(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _safe_id(value: Any, *, dotted: bool = False) -> str:
    if not isinstance(value, str) or not ( _ID if dotted else _NAME).fullmatch(value):
        raise CapabilityDenied("INVALID_IDENTIFIER")
    return value


def _version_tuple(value: str) -> tuple[int, ...]:
    if not isinstance(value, str) or not _VERSION.fullmatch(value):
        raise CapabilityDenied("INVALID_CAD_VERSION")
    segments = tuple(int(v) for v in value.split("."))
    return (segments + (0, 0, 0))[:3]


def _json_safe(data: Any) -> None:
    try:
        body = json.dumps(data, allow_nan=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise CapabilityDenied("NON_JSON_ARGUMENT") from exc
    if len(body.encode("utf-8")) > _MAX_JSON:
        raise CapabilityDenied("ARGUMENT_TOO_LARGE")


class Effect(StrEnum):
    READ = "READ"
    MUTATE = "MUTATE"
    DESTRUCTIVE = "DESTRUCTIVE"
    AUTOMATE = "AUTOMATE"


class Profile(StrEnum):
    READ_ONLY = "READ_ONLY"
    BOUNDED = "BOUNDED"
    FULL_CAD_WORKSPACE = "FULL_CAD_WORKSPACE"


@dataclass(frozen=True)
class OperationDescriptor:
    operation_id: str
    module: str
    effect: Effect
    arguments: Mapping[str, str] = field(default_factory=dict)
    required: frozenset[str] = field(default_factory=frozenset)
    since_version: str = "2022"
    until_version: str | None = None
    native_transaction_supported: bool = False
    reversible: bool = False

    def __post_init__(self) -> None:
        _safe_id(self.operation_id, dotted=True)
        _safe_id(self.module)
        try:
            object.__setattr__(self, "effect", Effect(self.effect))
        except (TypeError, ValueError) as exc:
            raise CapabilityDenied("INVALID_EFFECT") from exc
        args = dict(self.arguments)
        if any(not isinstance(k, str) or not _NAME.fullmatch(k) or v not in _KINDS for k, v in args.items()):
            raise CapabilityDenied("INVALID_ARGUMENT_SCHEMA")
        required = frozenset(self.required)
        if any(not isinstance(x, str) for x in required):
            raise CapabilityDenied("INVALID_REQUIRED_ARGUMENT")
        if not required.issubset(args):
            raise CapabilityDenied("UNKNOWN_REQUIRED_ARGUMENT")
        minimum = _version_tuple(self.since_version)
        if self.until_version is not None and _version_tuple(self.until_version) < minimum:
            raise CapabilityDenied("INVALID_VERSION_RANGE")
        if not isinstance(self.native_transaction_supported, bool) or not isinstance(self.reversible, bool):
            raise CapabilityDenied("INVALID_CAPABILITY_FLAG")
        object.__setattr__(self, "arguments", args)
        object.__setattr__(self, "required", required)

    def accepts_version(self, version: str) -> bool:
        actual = _version_tuple(version)
        minimum = _version_tuple(self.since_version)
        maximum = _version_tuple(self.until_version) if self.until_version else None
        return actual >= minimum and (maximum is None or actual <= maximum)

    def validate_arguments(self, values: Mapping[str, Any]) -> None:
        if not isinstance(values, Mapping):
            raise CapabilityDenied("INVALID_ARGUMENTS")
        args = dict(values)
        if any(not isinstance(k, str) for k in args):
            raise CapabilityDenied("INVALID_ARGUMENT_KEY")
        if not self.required.issubset(args) or set(args) - set(self.arguments):
            raise CapabilityDenied("ARGUMENT_BOUNDARY")
        for name, val in args.items():
            kind = self.arguments[name]
            match = {
                "string": isinstance(val, str),
                "integer": type(val) is int,
                "number": type(val) in (float, int) and math.isfinite(val),
                "boolean": type(val) is bool,
                "object": isinstance(val, dict),
                "array": isinstance(val, list),
            }[kind]
            if not match:
                raise CapabilityDenied("ARGUMENT_TYPE_MISMATCH")
        _json_safe(args)


@dataclass(frozen=True)
class CADSession:
    node_id: str
    application_id: str
    workspace_id: str
    lease_id: str
    provider_id: str
    expires_at: float
    profile: Profile
    allowed_operations: frozenset[str] = field(default_factory=frozenset)
    revoked: bool = False

    def __post_init__(self) -> None:
        for x in (self.node_id, self.application_id, self.workspace_id, self.lease_id):
            _safe_id(x)
        _safe_id(self.provider_id, dotted=True)
        try:
            object.__setattr__(self, "profile", Profile(self.profile))
        except ValueError as exc:
            raise CapabilityDenied("INVALID_PROFILE") from exc
        if type(self.expires_at) not in (int, float) or not math.isfinite(self.expires_at):
            raise CapabilityDenied("INVALID_LEASE_EXPIRY")
        if not isinstance(self.revoked, bool):
            raise CapabilityDenied("INVALID_LEASE_STATE")
        allow = frozenset(self.allowed_operations)
        for op in allow:
            _safe_id(op, dotted=True)
        if self.profile == Profile.BOUNDED and not allow:
            raise CapabilityDenied("EMPTY_BOUNDED_GRANT")
        object.__setattr__(self, "allowed_operations", allow)


@dataclass(frozen=True)
class CADRequest:
    node_id: str
    application_id: str
    workspace_id: str
    lease_id: str
    provider_id: str
    operation_id: str
    arguments: Mapping[str, Any]

    def __post_init__(self) -> None:
        for value in (self.node_id, self.application_id, self.workspace_id, self.lease_id):
            _safe_id(value)
        _safe_id(self.provider_id, dotted=True)
        _safe_id(self.operation_id, dotted=True)
        if not isinstance(self.arguments, Mapping):
            raise CapabilityDenied("INVALID_ARGUMENTS")
        safe = deepcopy(dict(self.arguments))
        _json_safe(safe)
        object.__setattr__(self, "arguments", safe)


@dataclass(frozen=True)
class CapabilityReceipt:
    status: str
    reason: str
    effect: str
    provider_verified: bool = False

    def public(self) -> dict[str, object]:
        return {"status": self.status, "reason": self.reason,
                "effect": self.effect, "provider_verified": self.provider_verified}


class CapabilityRouter:
    """Trusted host registers handlers at bootstrap. User commands cannot register any.

    This is a public contract; upstream Gate must independently authenticate the
    session and signed exact request, and handle journal/idempotency per command.
    Native output remains private and is deliberately not returned here.
    """
    def __init__(self, *, provider_id: str, version: str, licensed_modules: frozenset[str],
                 descriptors: tuple[OperationDescriptor, ...],
                 handlers: Mapping[str, Callable[[Mapping[str, Any]], object]],
                 clock: Callable[[], float] = time.time,
                 trusted_admission: Callable[[CADRequest, CADSession], bool] | None = None) -> None:
        _safe_id(provider_id, dotted=True)
        _version_tuple(version)
        if not isinstance(licensed_modules, frozenset) or not all(
                isinstance(v, str) and _NAME.fullmatch(v) for v in licensed_modules):
            raise CapabilityDenied("INVALID_MODULE_INVENTORY")
        available: dict[str, OperationDescriptor] = {}
        for d in descriptors:
            if not isinstance(d, OperationDescriptor) or d.operation_id in available:
                raise CapabilityDenied("INVALID_OR_DUPLICATE_DESCRIPTOR")
            parts = d.operation_id.split(".")
            if (len(parts) < 3 or parts[0] != provider_id.split(".", 1)[0]
                    or parts[1] != d.module):
                raise CapabilityDenied("OPERATION_PROVIDER_OR_MODULE_MISMATCH")
            available[d.operation_id] = d
        if not isinstance(handlers, Mapping) or any(k not in available or not callable(fn) for k, fn in handlers.items()):
            raise CapabilityDenied("INVALID_TRUSTED_HANDLER")
        if trusted_admission is not None and not callable(trusted_admission):
            raise CapabilityDenied("INVALID_TRUSTED_ADMISSION")
        self._provider = provider_id
        self._version = version
        self._modules = licensed_modules
        self._catalog = available
        self._handlers = dict(handlers)
        self._clock = clock
        self._trusted_admission = trusted_admission  # must be verified Skeleton Gate at runtime

    @classmethod
    def from_manifest(cls, manifest: Mapping[str, Any], *,
                      handlers: Mapping[str, Callable[[Mapping[str, Any]], object]],
                      trusted_admission: Callable[[CADRequest, CADSession], bool] | None = None,
                      clock: Callable[[], float] = time.time) -> "CapabilityRouter":
        """Load a public-safe description, never dynamically import a handler.

        The host must independently verify the manifest's provenance before
        invoking this loader and must supply registered handlers separately.
        A manifest alone never grants authority or binds native CAD operations.
        """
        keys = {"schema", "provider_id", "application_version", "modules", "operations"}
        if not isinstance(manifest, Mapping) or set(manifest) != keys:
            raise CapabilityDenied("MANIFEST_FIELDS_INVALID")
        if manifest["schema"] != "dios.cad_provider_capabilities.v1":
            raise CapabilityDenied("MANIFEST_SCHEMA_UNSUPPORTED")
        modules = manifest["modules"]
        operations = manifest["operations"]
        if (not isinstance(modules, list) or len(modules) > 4096
                or any(not isinstance(m, str) or not _NAME.fullmatch(m) for m in modules)
                or len(modules) != len(set(modules))
                or not isinstance(operations, list) or len(operations) > 50000):
            raise CapabilityDenied("MANIFEST_INVENTORY_INVALID")
        expected = {"operation_id", "module", "effect", "arguments", "required",
                    "since_version", "native_transaction_supported", "reversible"}
        descriptors = []
        for row in operations:
            if not isinstance(row, Mapping) or set(row) not in (expected, expected | {"until_version"}):
                raise CapabilityDenied("MANIFEST_OPERATION_FIELDS_INVALID")
            if (not isinstance(row["arguments"], Mapping) or not isinstance(row["required"], list)
                    or any(not isinstance(v, str) for v in row["required"])):
                raise CapabilityDenied("MANIFEST_OPERATION_TYPES_INVALID")
            descriptors.append(OperationDescriptor(
                operation_id=row["operation_id"], module=row["module"],
                effect=row["effect"], arguments=dict(row["arguments"]),
                required=frozenset(row["required"]),
                since_version=row["since_version"], until_version=row.get("until_version"),
                native_transaction_supported=row["native_transaction_supported"],
                reversible=row["reversible"],
            ))
        return cls(provider_id=manifest["provider_id"],
                   version=manifest["application_version"],
                   licensed_modules=frozenset(modules),
                   descriptors=tuple(descriptors), handlers=handlers,
                   clock=clock, trusted_admission=trusted_admission)

    def public_coverage(self) -> dict[str, int | str]:
        available = [d for d in self._catalog.values() if d.module in self._modules and d.accepts_version(self._version)]
        registered = sum(d.operation_id in self._handlers for d in available)
        return {"schema": "dios.cad_coverage.v1", "declared": len(self._catalog),
                "available": len(available), "registered_handlers": registered,
                "native_bound": 0, "provider_verified": 0}
        # Registered callbacks here are synthetic until independently validated
        # against a native CAD application with a trusted runtime and release.


    def execute(self, request: CADRequest, *, approved_session: CADSession) -> CapabilityReceipt:
        if not isinstance(request, CADRequest) or not isinstance(approved_session, CADSession):
            raise CapabilityDenied("TYPED_SESSION_AND_REQUEST_REQUIRED")
        for key in ("node_id", "application_id", "workspace_id", "lease_id", "provider_id"):
            if getattr(request, key) != getattr(approved_session, key):
                raise CapabilityDenied("SESSION_BOUNDARY_MISMATCH")
        if approved_session.provider_id != self._provider:
            raise CapabilityDenied("PROVIDER_MISMATCH")
        now = self._clock()
        if (not isinstance(now, (int, float)) or isinstance(now, bool)
                or not math.isfinite(now) or approved_session.revoked
                or now >= approved_session.expires_at):
            raise CapabilityDenied("LEASE_REVOKED_OR_EXPIRED")
        operation = self._catalog.get(request.operation_id)
        if operation is None:
            raise CapabilityDenied("UNKNOWN_PROVIDER_OPERATION")
        if operation.module not in self._modules or not operation.accepts_version(self._version):
            raise CapabilityDenied("MODULE_OR_VERSION_UNAVAILABLE")
        if approved_session.profile == Profile.READ_ONLY and operation.effect != Effect.READ:
            raise CapabilityDenied("READ_ONLY_DENIED")
        if approved_session.profile == Profile.BOUNDED and operation.operation_id not in approved_session.allowed_operations:
            raise CapabilityDenied("BOUNDED_OPERATION_DENIED")
        # A destructive or special provider operation remains within the approved
        # workspace only. External OS/security/network controls are NOT handlers.
        operation.validate_arguments(request.arguments)
        handler = self._handlers.get(operation.operation_id)
        if handler is None:
            raise CapabilityDenied("NATIVE_HANDLER_NOT_REGISTERED")
        # No CADRequest or self-declared session can authorize a native call.
        # The trusted host must inject an exact-request admission decision from
        # the registered signed Skeleton Gate; absence and errors fail closed.
        if self._trusted_admission is None:
            raise CapabilityDenied("TRUSTED_ADMISSION_MISSING")
        safe_values = deepcopy(dict(request.arguments))
        safe_request = CADRequest(request.node_id, request.application_id,
                                  request.workspace_id, request.lease_id,
                                  request.provider_id, request.operation_id,
                                  deepcopy(safe_values))
        try:
            admitted = self._trusted_admission(safe_request, approved_session)
        except Exception:
            raise CapabilityDenied("TRUSTED_ADMISSION_UNAVAILABLE") from None
        if admitted is not True:
            raise CapabilityDenied("TRUSTED_ADMISSION_DENIED")
        try:
            handler(safe_values)
        except Exception:
            return CapabilityReceipt("BLOCKED", "NATIVE_HANDLER_FAILED", operation.effect.value)
        return CapabilityReceipt("IN_PROCESS_HANDLER_CALLED", "REGISTERED_HANDLER", operation.effect.value)
