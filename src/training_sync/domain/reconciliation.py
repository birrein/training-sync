"""Values used to preview and safely apply scoped reconciliation."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class OperationKind(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    NOOP = "noop"


class TargetResultState(StrEnum):
    VERIFIED = "verified"
    FAILED = "failed"
    NOT_ATTEMPTED = "not_attempted"


@dataclass(frozen=True)
class SyncScope:
    providers: tuple[str, ...] = ()
    all_configured: bool = False

    @classmethod
    def targets(cls, providers: tuple[str, ...]) -> "SyncScope":
        if not providers:
            raise ValueError("Mutating scope must name explicit targets")
        if len(set(providers)) != len(providers):
            raise ValueError("Sync targets must be unique")
        return cls(providers=providers)

    @classmethod
    def all(cls) -> "SyncScope":
        return cls(all_configured=True)


@dataclass(frozen=True)
class ReconciliationOperation:
    provider: str
    kind: OperationKind
    remote_id: str | None
    payload: dict[str, Any]
    fingerprint: str | None
    destructive_consequence: str | None = None


@dataclass(frozen=True)
class ReconciliationPlan:
    scope: SyncScope
    operations: tuple[ReconciliationOperation, ...]


@dataclass(frozen=True)
class TargetResult:
    provider: str
    remote_id: str | None
    state: TargetResultState
    detail: str | None = None


@dataclass(frozen=True)
class ReconciliationResult:
    results: tuple[TargetResult, ...]
