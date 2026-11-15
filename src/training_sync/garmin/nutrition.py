"""Verified food logging through Garmin Connect's unofficial Nutrition API."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any

LOG_PATH = "/nutrition-service/food/logs"
MEALS_PATH = "/nutrition-service/meals"
SEARCH_PATH = "/nutrition-service/food/search"


@dataclass(frozen=True)
class FoodRequest:
    name: str
    quantity: float
    unit: str | None = None
    food_id: str | None = None


@dataclass(frozen=True)
class NutritionLogResult:
    state: str
    date: str
    time: str
    meal_name: str | None
    entries: tuple[dict[str, Any], ...] = ()
    totals: dict[str, Any] | None = None
    message: str | None = None


def parse_food_item(value: str) -> FoodRequest:
    """Parse `FOOD[ @FOOD_ID]=AMOUNT [UNIT]`."""
    if "=" not in value:
        raise ValueError("each --item must use FOOD=AMOUNT [UNIT]")
    name, amount = (part.strip() for part in value.split("=", 1))
    food_id = None
    id_match = re.fullmatch(r"(.+?)\s*@([A-Za-z0-9_-]+)", name)
    if id_match:
        name, food_id = id_match.groups()
    elif "@" in name:
        raise ValueError(f"invalid food ID selector in {value!r}; use FOOD@FOOD_ID=AMOUNT [UNIT]")
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)(?:\s+(.+))?", amount)
    if not name or not match:
        raise ValueError(f"invalid food item {value!r}; use FOOD=AMOUNT [UNIT]")
    quantity = float(match.group(1))
    if not math.isfinite(quantity) or quantity <= 0:
        raise ValueError("food quantity must be a positive finite number")
    return FoodRequest(name=name, quantity=quantity, unit=match.group(2), food_id=food_id)


def log_foods(
    client: Any,
    meal_date: str,
    meal_time: str,
    requests: list[FoodRequest],
    *,
    apply: bool = False,
) -> NutritionLogResult:
    """Preview or add foods once and verify each result with Garmin read-back."""
    date.fromisoformat(meal_date)
    parsed_time = time.fromisoformat(meal_time)
    normalized_time = parsed_time.strftime("%H:%M:%S")
    if not requests:
        raise ValueError("at least one food item is required")
    if any(not request.name.strip() or not math.isfinite(request.quantity) or request.quantity <= 0
           for request in requests):
        raise ValueError("food names and quantities must be non-empty and positive")

    try:
        before = client.connectapi(f"{LOG_PATH}/{meal_date}")
    # Provider lookup failures are reported as operation results before any write.
    except Exception as exc:  # noqa: BLE001
        return _result("failed", meal_date, normalized_time,
                       f"Garmin food log lookup failed ({type(exc).__name__}); no write was sent.")
    try:
        prior_foods = _validated_log_foods(before)
    except ValueError as exc:
        return _result("failed", meal_date, normalized_time,
                       f"Garmin food log response is incomplete or malformed ({exc}); no write was sent.")
    prior_snapshot = _food_snapshot(prior_foods)
    saved_foods = before["loggedFoodsWithServingSizes"]

    resolved: list[dict[str, Any]] = []
    for request in requests:
        saved_matches = [item for item in saved_foods
                         if _norm(item.get("foodMetaData", {}).get("foodName")) == _norm(request.name)]
        selected_saved = [item for item in saved_matches
                          if request.food_id is None
                          or str(item.get("foodMetaData", {}).get("foodId")) == request.food_id]
        choices = [(food, serving) for food in selected_saved
                   for serving in food.get("nutritionContents", [])
                   if request.unit is None or _unit_factor(request.unit, serving.get("servingUnit")) is not None]
        if saved_matches and not choices and (request.food_id is None or selected_saved):
            return _result("conflict", meal_date, normalized_time,
                           f"Existing Garmin food {request.name!r} has no compatible serving.")
        if not choices:
            try:
                found = client.connectapi(
                    SEARCH_PATH,
                    params={"searchExpression": request.name, "start": 0, "limit": 20},
                )
            # Provider search failures become a safe failed result; nothing is written.
            except Exception as exc:  # noqa: BLE001
                return _result("failed", meal_date, normalized_time,
                               f"Garmin food search failed ({type(exc).__name__}).")
            candidates = [item for item in (found or {}).get("results", [])
                          if _norm(item.get("foodMetaData", {}).get("foodName")) == _norm(request.name)]
            candidate_ids = _food_ids(candidates)
            if request.food_id is not None:
                candidates = [item for item in candidates
                              if str(item.get("foodMetaData", {}).get("foodId")) == request.food_id]
            choices = [(food, serving) for food in candidates
                       for serving in food.get("nutritionContents", [])
                       if request.unit is None or _unit_factor(request.unit, serving.get("servingUnit")) is not None]
            if not choices:
                suggestions = sorted({item.get("foodMetaData", {}).get("foodName", "")
                                      for item in (found or {}).get("results", [])
                                      if item.get("foodMetaData", {}).get("foodName")})
                return _result("conflict", meal_date, normalized_time,
                               (f"Food ID {request.food_id!r} did not resolve to a compatible "
                                f"{request.name!r} serving. Available IDs: {', '.join(candidate_ids) or 'none'}."
                                if request.food_id is not None else
                                f"No exact food and serving match for {request.name!r}. "
                                f"Catalog candidates: {', '.join(suggestions[:8]) or 'none'}."))
        if len(choices) != 1:
            return _result("conflict", meal_date, normalized_time,
                           (f"Expected one exact food and compatible serving for {request.name!r}; "
                            f"found {len(choices)}. Select one with @FOOD_ID: "
                            f"{', '.join(_food_ids(food for food, _ in choices)) or 'none'}."))
        food, serving = choices[0]
        meta = food.get("foodMetaData") or {}
        try:
            serving_units = float(serving["numberOfUnits"])
        except (KeyError, TypeError, ValueError):
            serving_units = 0
        if serving_units <= 0 or not math.isfinite(serving_units):
            return _result("conflict", meal_date, normalized_time,
                           f"Garmin returned an invalid serving size for {request.name!r}.")
        if not all(meta.get(key) for key in ("foodId", "source", "regionCode", "languageCode")) or not serving.get("servingId"):
            return _result("conflict", meal_date, normalized_time,
                           f"Garmin's food or serving metadata is incomplete for {request.name!r}.")
        factor = _unit_factor(request.unit, serving.get("servingUnit")) if request.unit else None
        serving_qty = request.quantity if factor is None else request.quantity * factor / serving_units
        resolved.append({"request": request, "meta": meta, "serving": serving,
                         "serving_qty": serving_qty})

    keys = [(item["meta"]["foodId"], item["serving"]["servingId"], item["serving_qty"])
            for item in resolved]
    if len(set(keys)) != len(keys):
        return _result("conflict", meal_date, normalized_time,
                       "The request contains the same food and serving more than once; combine the amounts.")

    try:
        meal_data = client.connectapi(f"{MEALS_PATH}/{meal_date}") or {}
    # Provider meal lookup failures are reported without attempting a write.
    except Exception as exc:  # noqa: BLE001
        return _result("failed", meal_date, normalized_time,
                       f"Garmin meal lookup failed ({type(exc).__name__}).")
    meals = meal_data.get("meals", [])
    meal = _meal_for_time(meals, parsed_time)
    if meal is None:
        return _result("conflict", meal_date, normalized_time,
                       "The requested time does not identify one Garmin meal.")
    for item in resolved:
        if any(_is_duplicate(existing, item, meal["mealId"], normalized_time)
               for existing in prior_foods):
            return _result("conflict", meal_date, normalized_time,
                           f"{item['meta']['foodName']} is already logged at {normalized_time}; nothing was added.",
                           meal_name=meal.get("mealName"))

    payload_items = [_payload_item(item, meal["mealId"], normalized_time) for item in resolved]
    if not apply:
        return NutritionLogResult("preview", meal_date, normalized_time, meal.get("mealName"),
                                  tuple(_public_entry(item) for item in resolved),
                                  message="Preview only; pass --yes to add these foods.")

    payload = {"mealDate": meal_date, "foodLogItems": payload_items}
    write_error = None
    try:
        client.client.put("connectapi", LOG_PATH, json=payload, api=True)
    # The provider may apply the write before losing its response; read back once.
    except Exception as exc:  # noqa: BLE001
        write_error = type(exc).__name__

    try:
        after = client.connectapi(f"{LOG_PATH}/{meal_date}")
    # Failed post-write read-back leaves the outcome uncertain; never retry here.
    except Exception as exc:  # noqa: BLE001
        return _result("uncertain", meal_date, normalized_time,
                       f"Write outcome is unknown; Garmin read-back failed ({type(exc).__name__}). Do not retry yet.",
                       meal_name=meal.get("mealName"))
    try:
        after_foods = _validated_log_foods(after)
    except ValueError as exc:
        return _result("uncertain", meal_date, normalized_time,
                       f"Write outcome is unknown; Garmin read-back is incomplete or malformed ({exc}). Do not retry yet.",
                       meal_name=meal.get("mealName"))
    if not _snapshot_preserved(prior_snapshot, _food_snapshot(after_foods)):
        return _result("verification_failed", meal_date, normalized_time,
                       "Read-back did not preserve every previously logged entry.",
                       meal_name=meal.get("mealName"))

    unmatched = list(after_foods)
    verified_entries = []
    missing_entries = []
    for item in resolved:
        match = next((existing for existing in unmatched
                      if _is_duplicate(existing, item, meal["mealId"], normalized_time)), None)
        if match is None:
            missing_entries.append(item["meta"]["foodName"])
            continue
        unmatched.remove(match)
        verified_entries.append(_public_logged_entry(match))
    if missing_entries:
        return NutritionLogResult(
            "uncertain", meal_date, normalized_time, meal.get("mealName"),
            tuple(verified_entries), after.get("dailyNutritionContent"),
            f"Read-back verified {len(verified_entries)} of {len(resolved)} entries; "
            f"missing or uncertain: {', '.join(missing_entries)}. No retry was sent.",
        )
    totals = after.get("dailyNutritionContent")
    return NutritionLogResult(
        "verified", meal_date, normalized_time, meal.get("mealName"),
        tuple(verified_entries), totals,
        "Verified by Garmin read-back" + (f" after {write_error}" if write_error else ""),
    )


def _meal_for_time(meals: list[dict[str, Any]], requested: time) -> dict[str, Any] | None:
    enabled = [meal for meal in meals if meal.get("enabled", True)]
    matches = []
    for meal in enabled:
        start, end = meal.get("startTime"), meal.get("endTime")
        if not start or not end:
            continue
        start_time, end_time = time.fromisoformat(start), time.fromisoformat(end)
        # Garmin accepts the end instant as part of the meal. Shared boundaries
        # therefore match both meals and must be rejected as ambiguous.
        contains = (start_time <= requested <= end_time if start_time <= end_time
                    else requested >= start_time or requested <= end_time)
        if contains:
            matches.append(meal)
    if len(matches) == 1:
        return matches[0]
    if matches:
        return None
    snacks = [meal for meal in enabled if _norm(meal.get("mealName")) == "snacks"
              and not meal.get("startTime") and not meal.get("endTime")]
    return snacks[0] if len(snacks) == 1 else None


def _payload_item(item: dict[str, Any], meal_id: int, meal_time: str) -> dict[str, Any]:
    meta, serving = item["meta"], item["serving"]
    return {
        "logTimestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "logSource": "GCW", "logCategory": "REGULAR_LOG", "mealTime": meal_time,
        "action": "ADD", "mealId": meal_id, "foodId": meta["foodId"],
        "servingId": serving["servingId"], "source": meta["source"],
        "regionCode": meta["regionCode"], "languageCode": meta["languageCode"],
        "servingQty": item["serving_qty"],
    }


def _validated_log_foods(log: Any) -> list[dict[str, Any]]:
    """Require the day-log fields needed for safe resolution, dedupe, and verification."""
    if not isinstance(log, dict):
        # Payload validation contract uses ValueError for malformed response shapes.
        raise ValueError("expected a JSON object")  # noqa: TRY004
    details = log.get("mealDetails")
    saved = log.get("loggedFoodsWithServingSizes")
    if not isinstance(details, list) or not isinstance(saved, list):
        # Payload validation contract uses ValueError for malformed response shapes.
        raise ValueError("expected mealDetails and loggedFoodsWithServingSizes lists")  # noqa: TRY004
    foods: list[dict[str, Any]] = []
    for detail in details:
        if not isinstance(detail, dict) or not isinstance(detail.get("loggedFoods"), list):
            # Payload validation contract uses ValueError for malformed response shapes.
            raise ValueError("mealDetails entry has no loggedFoods list")  # noqa: TRY004
        foods.extend(detail["loggedFoods"])
    for food in foods:
        if not isinstance(food, dict) or _preservation_key(food) is None:
            raise ValueError("logged food is missing identity, serving, meal, time, or quantity fields")
    for food in saved:
        if (not isinstance(food, dict) or not isinstance(food.get("foodMetaData"), dict)
                or not isinstance(food.get("nutritionContents"), list)):
            # Payload validation contract uses ValueError for malformed response shapes.
            raise ValueError("saved food entry has malformed metadata or serving list")  # noqa: TRY004
    return foods


def _food_snapshot(foods: list[dict[str, Any]]) -> dict[tuple[Any, ...], int]:
    snapshot: dict[tuple[Any, ...], int] = {}
    for food in foods:
        key = _preservation_key(food)
        # Inputs have already been validated, but retain fail-closed semantics if called directly.
        if key is None:
            raise ValueError("cannot snapshot malformed logged food")
        snapshot[key] = snapshot.get(key, 0) + 1
    return snapshot


def _snapshot_preserved(before: dict[tuple[Any, ...], int],
                        after: dict[tuple[Any, ...], int]) -> bool:
    return all(after.get(key, 0) >= count for key, count in before.items())


def _preservation_key(food: dict[str, Any]) -> tuple[Any, ...] | None:
    meta, content = food.get("foodMetaData"), food.get("nutritionContent")
    if not isinstance(meta, dict) or not isinstance(content, dict):
        return None
    log_id, food_id, serving_id = food.get("logId"), meta.get("foodId"), content.get("servingId")
    meal_id, meal_time, quantity = food.get("mealId"), food.get("mealTime"), food.get("servingQty")
    if any(value is None or value == "" for value in
           (log_id, food_id, serving_id, meal_id, meal_time, quantity)):
        return None
    try:
        normalized_time = time.fromisoformat(str(meal_time)).strftime("%H:%M:%S")
        normalized_quantity = round(float(quantity), 8)
        normalized_meal_id = int(meal_id)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(normalized_quantity):
        return None
    return (str(log_id), str(food_id), str(meta.get("source", "")), str(serving_id),
            normalized_meal_id, normalized_time, normalized_quantity)


def _is_duplicate(existing: dict[str, Any], item: dict[str, Any], meal_id: int, meal_time: str) -> bool:
    meta, content = item["meta"], item["serving"]
    old_meta, old_content = existing.get("foodMetaData", {}), existing.get("nutritionContent", {})
    try:
        return (
            old_meta.get("foodId") == meta.get("foodId")
            and old_meta.get("source", meta.get("source")) == meta.get("source")
            and old_content.get("servingId") == content.get("servingId")
            and int(existing.get("mealId", -1)) == int(meal_id)
            and existing.get("mealTime") == meal_time
            and math.isclose(float(existing.get("servingQty", -1)), item["serving_qty"], rel_tol=1e-6)
        )
    except (TypeError, ValueError):
        return False


def _unit_factor(requested: str | None, actual: str | None) -> float | None:
    if requested is None:
        return None
    request_unit, actual_unit = _norm_unit(requested), _norm_unit(actual)
    mass = {"mg": 0.001, "g": 1.0, "kg": 1000.0}
    if request_unit in mass and actual_unit in mass:
        return mass[request_unit] / mass[actual_unit]
    if request_unit == actual_unit:
        return 1.0
    return None


def _norm_unit(value: str | None) -> str:
    value = (value or "").strip().casefold()
    return {"gram": "g", "grams": "g", "gr": "g", "gramo": "g", "gramos": "g",
            "kilogram": "kg", "kilograms": "kg", "kilo": "kg", "kilos": "kg",
            "milligram": "mg", "milligrams": "mg", "miligramo": "mg"}.get(value, value)


def _norm(value: str | None) -> str:
    return " ".join((value or "").strip().casefold().split())


def _food_ids(foods: Any) -> list[str]:
    return sorted({str(food.get("foodMetaData", {}).get("foodId"))
                   for food in foods if food.get("foodMetaData", {}).get("foodId")})


def _public_entry(item: dict[str, Any]) -> dict[str, Any]:
    request, serving = item["request"], item["serving"]
    quantity = request.quantity if request.unit else item["serving_qty"] * float(serving["numberOfUnits"])
    entry = {"name": item["meta"]["foodName"], "quantity": quantity,
             "unit": request.unit or serving["servingUnit"],
             "serving_qty": item["serving_qty"]}
    if request.food_id is not None:
        entry["food_id"] = str(item["meta"]["foodId"])
    return entry


def _public_logged_entry(item: dict[str, Any]) -> dict[str, Any]:
    content = item.get("nutritionContent", {})
    try:
        serving_qty = float(item.get("servingQty"))
        units_per_serving = float(content.get("numberOfUnits"))
        quantity = serving_qty * units_per_serving
    except (TypeError, ValueError):
        # Keep the actual Garmin serving count visible, but don't label it as
        # the food's mass/count when Garmin omits the catalog conversion.
        serving_qty = item.get("servingQty")
        quantity = None
    return {"name": item.get("foodMetaData", {}).get("foodName"),
            "quantity": quantity,
            "unit": content.get("servingUnit") if quantity is not None else None,
            "serving_qty": serving_qty,
            "calories_per_serving": item.get("nutritionContent", {}).get("calories"),
            "protein_per_serving": item.get("nutritionContent", {}).get("protein"),
            "carbs_per_serving": item.get("nutritionContent", {}).get("carbs"),
            "fat_per_serving": item.get("nutritionContent", {}).get("fat"),
            "meal_time": item.get("mealTime")}


def _result(state: str, meal_date: str, meal_time: str, message: str,
            *, meal_name: str | None = None) -> NutritionLogResult:
    return NutritionLogResult(state, meal_date, meal_time, meal_name, message=message)
