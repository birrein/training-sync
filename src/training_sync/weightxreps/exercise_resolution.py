"""Resolve vault exercise names to Weight x Reps exercise IDs."""

from dataclasses import dataclass
from difflib import SequenceMatcher

from training_sync.weightxreps.exercise_mapping import (
    ExerciseMapping,
    normalize_exercise_name,
)


ALLOWED_ACTIONS = [
    "map_to_existing",
    "create_new",
    "skip_workout",
]


@dataclass(frozen=True)
class ExerciseCandidate:
    weightxreps_id: int
    weightxreps_name: str
    match_reason: str

    def payload(self) -> dict:
        return {
            "weightxreps_id": self.weightxreps_id,
            "weightxreps_name": self.weightxreps_name,
            "match_reason": self.match_reason,
        }


@dataclass(frozen=True)
class UnresolvedExercise:
    incoming_exercise: str
    normalized_name: str
    reason: str
    candidates: list[ExerciseCandidate]
    mapped_weightxreps_id: int | None = None
    mapped_weightxreps_name: str | None = None

    def payload(self) -> dict:
        payload = {
            "incoming_exercise": self.incoming_exercise,
            "normalized_name": self.normalized_name,
            "reason": self.reason,
            "candidates": [candidate.payload() for candidate in self.candidates],
            "allowed_actions": ALLOWED_ACTIONS,
        }
        if self.mapped_weightxreps_id is not None:
            payload["mapped_weightxreps_id"] = self.mapped_weightxreps_id
        if self.mapped_weightxreps_name is not None:
            payload["mapped_weightxreps_name"] = self.mapped_weightxreps_name
        return payload


class ExerciseResolutionRequired(RuntimeError):
    def __init__(
        self,
        date: str,
        unresolved: list[UnresolvedExercise],
        catalog_source: str = "unknown",
    ) -> None:
        self.date = date
        self.unresolved = unresolved
        self.catalog_source = catalog_source
        super().__init__("Weight x Reps exercise resolution required")

    def payload(self) -> dict:
        first = self.unresolved[0].incoming_exercise
        return {
            "status": "exercise_resolution_required",
            "date": self.date,
            "catalog_source": self.catalog_source,
            "unresolved": [exercise.payload() for exercise in self.unresolved],
            "suggested_agent_question": (
                f"How should I resolve '{first}': map it to an existing candidate, "
                "create it as a new Weight x Reps exercise, or skip this sync?"
            ),
        }


def resolve_exercise_ids(
    date: str,
    exercise_names: list[str],
    local_mappings: list[ExerciseMapping],
    remote_exercise_ids: dict[str, int],
    catalog_source: str = "unknown",
) -> dict[str, int | None]:
    local_index = _local_alias_index(local_mappings)
    remote_index = {
        normalize_exercise_name(name): (name, exercise_id)
        for name, exercise_id in remote_exercise_ids.items()
    }
    remote_ids = set(remote_exercise_ids.values())

    resolved: dict[str, int | None] = {}
    unresolved: list[UnresolvedExercise] = []
    for exercise_name in exercise_names:
        normalized_name = normalize_exercise_name(exercise_name)
        mapping = local_index.get(normalized_name)
        if mapping is not None:
            if mapping.weightxreps_id is not None:
                if (
                    catalog_source == "partial_jeditor"
                    or mapping.weightxreps_id in remote_ids
                ):
                    resolved[exercise_name] = mapping.weightxreps_id
                    continue

                unresolved.append(
                    UnresolvedExercise(
                        incoming_exercise=exercise_name,
                        normalized_name=normalized_name,
                        reason="mapped_id_not_in_remote_catalog",
                        candidates=_candidate_matches_for_names(
                            [
                                normalized_name,
                                normalize_exercise_name(mapping.weightxreps_name),
                            ],
                            remote_exercise_ids,
                        ),
                        mapped_weightxreps_id=mapping.weightxreps_id,
                        mapped_weightxreps_name=mapping.weightxreps_name,
                    )
                )
                continue

            remote_match = remote_index.get(normalize_exercise_name(mapping.weightxreps_name))
            if remote_match is not None:
                resolved[exercise_name] = remote_match[1]
                continue

            if mapping.create_if_missing:
                if catalog_source == "full_catalog":
                    resolved[exercise_name] = None
                    continue

                unresolved.append(
                    UnresolvedExercise(
                        incoming_exercise=exercise_name,
                        normalized_name=normalized_name,
                        reason="create_requires_full_catalog",
                        candidates=_candidate_matches_for_names(
                            [
                                normalized_name,
                                normalize_exercise_name(mapping.weightxreps_name),
                            ],
                            remote_exercise_ids,
                        ),
                        mapped_weightxreps_name=mapping.weightxreps_name,
                    )
                )
                continue

        remote_match = remote_index.get(normalized_name)
        if remote_match is not None:
            resolved[exercise_name] = remote_match[1]
            continue

        unresolved.append(
            UnresolvedExercise(
                incoming_exercise=exercise_name,
                normalized_name=normalized_name,
                reason="no_local_mapping",
                candidates=_candidate_matches(normalized_name, remote_exercise_ids),
            )
        )

    if unresolved:
        raise ExerciseResolutionRequired(date, unresolved, catalog_source)

    return resolved


def _local_alias_index(mappings: list[ExerciseMapping]) -> dict[str, ExerciseMapping]:
    index: dict[str, ExerciseMapping] = {}
    for mapping in mappings:
        names = [mapping.weightxreps_name, *mapping.aliases]
        for name in names:
            index[normalize_exercise_name(name)] = mapping
    return index


def _candidate_matches(
    normalized_name: str,
    remote_exercise_ids: dict[str, int],
) -> list[ExerciseCandidate]:
    return _candidate_matches_for_names([normalized_name], remote_exercise_ids)


def _candidate_matches_for_names(
    normalized_names: list[str],
    remote_exercise_ids: dict[str, int],
) -> list[ExerciseCandidate]:
    scored: list[tuple[float, ExerciseCandidate]] = []
    for remote_name, exercise_id in remote_exercise_ids.items():
        normalized_remote = normalize_exercise_name(remote_name)
        remote_tokens = set(normalized_remote.split())
        for normalized_name in normalized_names:
            incoming_tokens = set(normalized_name.split())
            score = SequenceMatcher(None, normalized_name, normalized_remote).ratio()
            shared_tokens = incoming_tokens & remote_tokens
            if score >= 0.65 or (shared_tokens and remote_tokens <= incoming_tokens):
                reason = "similar_name" if score >= 0.65 else "shared_tokens"
                scored.append(
                    (
                        score + (len(shared_tokens) / 10),
                        ExerciseCandidate(
                            weightxreps_id=exercise_id,
                            weightxreps_name=remote_name,
                            match_reason=reason,
                        ),
                    )
                )

    candidates: list[ExerciseCandidate] = []
    seen_ids: set[int] = set()
    for _, candidate in sorted(scored, key=lambda item: item[0], reverse=True):
        if candidate.weightxreps_id in seen_ids:
            continue
        candidates.append(candidate)
        seen_ids.add(candidate.weightxreps_id)
        if len(candidates) == 5:
            break

    return candidates
