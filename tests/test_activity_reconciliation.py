from training_sync.domain.reconciliation import OperationKind, SyncScope, TargetResultState
from training_sync.use_cases.activity_reconciliation import apply_plan, build_plan, plan_provider_local_edit


class Adapter:
    def __init__(self, fingerprint="v1"):
        self.fingerprint = fingerprint
        self.mutations = 0

    def fingerprint_for(self, remote_id):
        return self.fingerprint

    def update(self, remote_id, payload):
        self.mutations += 1

    def verify(self, remote_id, payload):
        return True


def test_scope_is_exact_and_all_is_explicit():
    assert SyncScope.targets(("vault", "weightxreps")).providers == ("vault", "weightxreps")
    assert SyncScope.all().all_configured is True


def test_scope_rejects_ambiguous_empty_target_set():
    try:
        SyncScope.targets(())
    except ValueError as exc:
        assert "explicit" in str(exc)
    else:
        raise AssertionError("empty scope accepted")


def test_preview_default_never_mutates_and_apply_verifies_fingerprint():
    adapter = Adapter()
    plan = build_plan(
        scope=SyncScope.targets(("intervals",)),
        adapters={"intervals": adapter},
        operations=[("intervals", OperationKind.UPDATE, "42", {"name": "Fixed"})],
    )

    preview = apply_plan(plan, {"intervals": adapter}, authorized=False)
    assert adapter.mutations == 0
    assert preview.results[0].state is TargetResultState.NOT_ATTEMPTED

    applied = apply_plan(plan, {"intervals": adapter}, authorized=True)
    assert adapter.mutations == 1
    assert applied.results[0].state is TargetResultState.VERIFIED


def test_changed_remote_fingerprint_fails_without_mutation():
    adapter = Adapter()
    plan = build_plan(
        scope=SyncScope.targets(("intervals",)),
        adapters={"intervals": adapter},
        operations=[("intervals", OperationKind.UPDATE, "42", {"name": "Fixed"})],
    )
    adapter.fingerprint = "changed"

    result = apply_plan(plan, {"intervals": adapter}, authorized=True)
    assert result.results[0].state is TargetResultState.FAILED
    assert adapter.mutations == 0


def test_provider_local_edit_selects_only_its_replica():
    intervals = Adapter()
    plan = plan_provider_local_edit(
        provider="intervals", adapter=intervals, remote_id="42", payload={"name": "Fixed"}
    )

    assert plan.scope.providers == ("intervals",)
    assert [operation.provider for operation in plan.operations] == ["intervals"]
