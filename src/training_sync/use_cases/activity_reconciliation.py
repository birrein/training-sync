"""Capability-based plan, apply, and independent read-back verification."""

from collections.abc import Mapping, Sequence
from typing import Any

from training_sync.domain.reconciliation import (
    OperationKind,
    ReconciliationOperation,
    ReconciliationPlan,
    ReconciliationResult,
    SyncScope,
    TargetResult,
    TargetResultState,
)


def build_plan(
    *, scope: SyncScope, adapters: Mapping[str, object], operations: Sequence[tuple[str, OperationKind, str | None, dict[str, Any]]]
) -> ReconciliationPlan:
    selected = tuple(adapters) if scope.all_configured else scope.providers
    planned = []
    for provider, kind, remote_id, payload in operations:
        if provider not in selected:
            raise ValueError(f"Operation target is outside scope: {provider}")
        adapter = adapters.get(provider)
        if adapter is None:
            raise ValueError(f"No adapter configured for {provider}")
        method = "delete" if kind is OperationKind.DELETE else kind.value
        if kind is not OperationKind.NOOP and not hasattr(adapter, method):
            raise ValueError(f"{provider} does not support {kind.value}")
        fingerprint = adapter.fingerprint_for(remote_id) if remote_id is not None else None
        planned.append(ReconciliationOperation(provider, kind, remote_id, payload, fingerprint))
    return ReconciliationPlan(scope, tuple(planned))


def apply_plan(plan: ReconciliationPlan, adapters: Mapping[str, object], *, authorized: bool) -> ReconciliationResult:
    results = []
    for operation in plan.operations:
        if not authorized:
            results.append(TargetResult(operation.provider, operation.remote_id, TargetResultState.NOT_ATTEMPTED, "preview"))
            continue
        adapter = adapters[operation.provider]
        if operation.remote_id is not None and adapter.fingerprint_for(operation.remote_id) != operation.fingerprint:
            results.append(TargetResult(operation.provider, operation.remote_id, TargetResultState.FAILED, "remote fingerprint changed; re-plan required"))
            continue
        try:
            verified_id = operation.remote_id
            if operation.kind is not OperationKind.NOOP:
                returned = getattr(adapter, operation.kind.value)(operation.remote_id, operation.payload)
                # Create/upload providers commonly allocate their remote id.
                if operation.kind is OperationKind.CREATE and returned is not None:
                    verified_id = str(returned)
            verified = operation.kind is OperationKind.NOOP or adapter.verify(verified_id, operation.payload)
            state = TargetResultState.VERIFIED if verified else TargetResultState.FAILED
            results.append(TargetResult(operation.provider, verified_id, state, None if verified else "read-back mismatch"))
        except Exception as exc:
            results.append(TargetResult(operation.provider, operation.remote_id, TargetResultState.FAILED, str(exc)))
    return ReconciliationResult(tuple(results))


def plan_provider_local_edit(
    *, provider: str, adapter: object, remote_id: str, payload: dict[str, Any]
) -> ReconciliationPlan:
    """Plan an isolated provider edit; it never selects another destination."""
    return build_plan(
        scope=SyncScope.targets((provider,)),
        adapters={provider: adapter},
        operations=[(provider, OperationKind.UPDATE, remote_id, payload)],
    )
