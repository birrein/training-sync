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

    def payload(self) -> dict:
        return {
            "incoming_exercise": self.incoming_exercise,
            "normalized_name": self.normalized_name,
            "reason": self.reason,
            "candidates": [candidate.payload() for candidate in self.candidates],
            "allowed_actions": ALLOWED_ACTIONS,
        }


class ExerciseResolutionRequired(RuntimeError):
    def __init__(self, date: str, unresolved: list[UnresolvedExercise]) -> None:
        self.date = date
        self.unresolved = unresolved
        super().__init__("Weight x Reps exercise resolution required")

    def payload(self) -> dict:
        first = self.unresolved[0].incoming_exercise
        return {
            "status": "exercise_resolution_required",
            "date": self.date,
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
) -> dict[str, int]:
    local_index = _local_alias_index(local_mappings)
    remote_index = {
        normalize_exercise_name(name): (name, exercise_id)
        for name, exercise_id in remote_exercise_ids.items()
    }

    resolved: dict[str, int] = {}
    unresolved: list[UnresolvedExercise] = []
    for exercise_name in exercise_names:
        normalized_name = normalize_exercise_name(exercise_name)
        mapping = local_index.get(normalized_name)
        if mapping is not None:
            if mapping.weightxreps_id is not None:
                resolved[exercise_name] = mapping.weightxreps_id
                continue

            remote_match = remote_index.get(normalize_exercise_name(mapping.weightxreps_name))
            if remote_match is not None:
                resolved[exercise_name] = remote_match[1]
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
        raise ExerciseResolutionRequired(date, unresolved)

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
    scored: list[tuple[float, ExerciseCandidate]] = []
    incoming_tokens = set(normalized_name.split())
    for remote_name, exercise_id in remote_exercise_ids.items():
        normalized_remote = normalize_exercise_name(remote_name)
        remote_tokens = set(normalized_remote.split())
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

    return [
        candidate
        for _, candidate in sorted(scored, key=lambda item: item[0], reverse=True)[:5]
    ]
