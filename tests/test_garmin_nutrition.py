from training_sync.garmin.nutrition import (
    FoodRequest,
    log_foods,
    parse_food_item,
)


class FakeClient:
    def __init__(self, meals, log, search):
        self.meals = meals
        self.log = log
        self.search = search
        self.calls = []
        self.put_calls = []
        self.client = self

    def connectapi(self, path, **kwargs):
        self.calls.append((path, kwargs))
        if path.startswith("/nutrition-service/meals/"):
            return self.meals
        if path.startswith("/nutrition-service/food/logs/"):
            return self.log
        if path == "/nutrition-service/food/search":
            return self.search
        raise AssertionError(path)

    def put(self, domain, path, **kwargs):
        self.put_calls.append((domain, path, kwargs))
        for item in kwargs["json"]["foodLogItems"]:
            food = next(x for x in self.search["results"]
                        if x["foodMetaData"]["foodId"] == item["foodId"])
            content = next(x for x in food["nutritionContents"]
                           if x["servingId"] == item["servingId"])
            self.log["mealDetails"][0]["loggedFoods"].append({
                "logId": f"new-{item['foodId']}", "mealId": item["mealId"],
                "mealTime": item["mealTime"], "servingQty": item["servingQty"],
                "foodMetaData": food["foodMetaData"], "nutritionContent": content,
            })
        return {"accepted": True}


def _food(name, food_id, serving_id, unit, units, *, region="CL", language="es"):
    return {
        "foodMetaData": {
            "foodId": food_id,
            "foodName": name,
            "source": "FATSECRET",
            "regionCode": region,
            "languageCode": language,
        },
        "nutritionContents": [{
            "servingId": serving_id,
            "servingUnit": unit,
            "numberOfUnits": units,
            "calories": 91,
            "protein": 6.0,
            "carbs": 16.6,
            "fat": 0.3,
        }],
    }


def _client(*, existing=(), time_range=("16:00:00", "18:00:00")):
    meals = {"meals": [
        {"mealId": 10, "mealName": "LUNCH", "enabled": True,
         "startTime": "12:00:00", "endTime": "14:00:00"},
        {"mealId": 11, "mealName": "SNACKS", "enabled": True,
         "startTime": time_range[0], "endTime": time_range[1]},
    ]}
    log = {"mealDate": "2026-09-30", "mealDetails": [
        {"meal": {"mealId": 11, "mealName": "SNACKS"}, "loggedFoods": list(existing)}
    ], "loggedFoodsWithServingSizes": []}
    return FakeClient(meals, log, {"results": [_food("Porotos Negros", "beans", "b100", "g", 100),
                                               _food("Huevo Duro", "egg", "e1", "grande", 1)]})


def test_parse_item_converts_requested_measure_to_catalog_servings():
    beans = parse_food_item("Porotos Negros=100 g")
    eggs = parse_food_item("Huevo Duro=2 grande")

    assert beans == FoodRequest("Porotos Negros", 100, "g")
    assert eggs == FoodRequest("Huevo Duro", 2, "grande")


def test_log_foods_converts_metric_units_and_defaults_to_serving_count():
    client = _client()

    grams = log_foods(client, "2026-09-30", "17:50", [FoodRequest("Porotos Negros", 0.1, "kg")])
    servings = log_foods(client, "2026-09-30", "17:50", [FoodRequest("Huevo Duro", 2)])

    assert grams.entries[0]["serving_qty"] == 1
    assert servings.entries[0]["serving_qty"] == 2


def test_log_foods_uses_catalog_locale_meal_and_verified_batch_payload():
    client = _client()

    result = log_foods(
        client, "2026-09-30", "17:50", [
            FoodRequest("Porotos Negros", 100, "g"),
            FoodRequest("Huevo Duro", 2, "grande"),
        ], apply=True,
    )

    assert result.state == "verified"
    assert [(entry["quantity"], entry["unit"], entry["serving_qty"])
            for entry in result.entries] == [(100, "g", 1), (2, "grande", 2)]
    assert len(client.put_calls) == 1
    domain, path, kwargs = client.put_calls[0]
    assert (domain, path) == ("connectapi", "/nutrition-service/food/logs")
    items = kwargs["json"]["foodLogItems"]
    assert kwargs["json"]["mealDate"] == "2026-09-30"
    assert [(i["foodId"], i["servingId"], i["servingQty"], i["mealId"], i["mealTime"])
            for i in items] == [("beans", "b100", 1, 11, "17:50:00"),
                                ("egg", "e1", 2, 11, "17:50:00")]
    assert all(i["source"] == "FATSECRET" and i["regionCode"] == "CL"
               and i["languageCode"] == "es" for i in items)


def test_log_foods_preview_does_not_write():
    client = _client()

    result = log_foods(client, "2026-09-30", "17:50", [FoodRequest("Huevo Duro", 2, "grande")])

    assert result.state == "preview"
    assert client.put_calls == []


def test_log_foods_fails_closed_on_incomplete_initial_log_response():
    client = _client()
    client.log = {"mealDetails": []}  # missing saved-serving list: duplicate check isn't trustworthy

    result = log_foods(client, "2026-09-30", "17:50", [FoodRequest("Huevo Duro", 2)], apply=True)

    assert result.state == "failed"
    assert "incomplete" in result.message.casefold()
    assert client.put_calls == []


def test_log_foods_preview_reports_resolved_mass_not_one_gram():
    client = _client()

    result = log_foods(client, "2026-09-30", "17:50", [FoodRequest("Porotos Negros", 1)])

    assert result.state == "preview"
    assert result.entries[0]["quantity"] == 100
    assert result.entries[0]["unit"] == "g"


def test_log_foods_detects_prior_entry_mutation_even_when_log_id_remains():
    prior = {
        "logId": "old", "mealId": 11, "mealTime": "16:10:00", "servingQty": 1,
        "foodMetaData": {"foodId": "beans", "source": "FATSECRET"},
        "nutritionContent": {"servingId": "b100", "servingUnit": "g", "numberOfUnits": 100},
    }
    client = _client(existing=[prior])

    def mutate_during_put(*args, **kwargs):
        # The same log id appears in the readback, but its recorded amount changed.
        prior["servingQty"] = 2

    client.put = mutate_during_put
    result = log_foods(client, "2026-09-30", "17:50", [FoodRequest("Huevo Duro", 2, "grande")], apply=True)

    assert result.state == "verification_failed"


def test_log_foods_rejects_ambiguous_match_before_write():
    client = _client()
    client.search["results"].append(_food("Porotos Negros", "beans2", "b2", "g", 100))

    result = log_foods(client, "2026-09-30", "17:50", [FoodRequest("Porotos Negros", 100, "g")], apply=True)

    assert result.state == "conflict"
    assert client.put_calls == []


def test_log_foods_prefers_existing_account_food_and_serving():
    client = _client()
    preferred = _food("Porotos Negros", "account-choice", "saved-100g", "g", 100)
    client.log["loggedFoodsWithServingSizes"] = [preferred]
    client.search["results"].append(_food("Porotos Negros", "other-choice", "other-100g", "g", 100))

    result = log_foods(client, "2026-09-30", "17:50", [FoodRequest("Porotos Negros", 100, "g")])

    assert result.state == "preview"
    assert not any(path == "/nutrition-service/food/search" for path, _ in client.calls)


def test_log_foods_rejects_duplicate_before_write():
    client = _client(existing=[{
        "logId": "old", "mealId": 11, "mealTime": "17:50:00", "servingQty": 1,
        "foodMetaData": {"foodId": "beans", "source": "FATSECRET"},
        "nutritionContent": {"servingId": "b100", "servingUnit": "g", "numberOfUnits": 100},
    }])

    result = log_foods(client, "2026-09-30", "17:50", [FoodRequest("Porotos Negros", 100, "g")], apply=True)

    assert result.state == "conflict"
    assert client.put_calls == []


def test_log_foods_rejects_duplicate_items_in_one_request():
    client = _client()
    request = FoodRequest("Huevo Duro", 2, "grande")

    result = log_foods(client, "2026-09-30", "17:50", [request, request], apply=True)

    assert result.state == "conflict"
    assert "combine" in result.message
    assert client.put_calls == []


def test_log_foods_reconciles_lost_put_without_retry():
    client = _client()
    attempts = []
    client.put = lambda *a, **k: (attempts.append(1), (_ for _ in ()).throw(TimeoutError("lost response")))[1]

    result = log_foods(client, "2026-09-30", "17:50", [FoodRequest("Huevo Duro", 2, "grande")], apply=True)

    assert result.state == "uncertain"
    assert len(client.calls) >= 3
    assert attempts == [1]


def test_log_foods_reports_partial_readback_without_retry():
    client = _client()
    client.put = lambda *a, **k: {"accepted": True}

    result = log_foods(client, "2026-09-30", "17:50", [FoodRequest("Huevo Duro", 2, "grande")], apply=True)

    assert result.state == "uncertain"
    assert "no retry" in result.message.casefold()


def test_log_foods_supports_overnight_windows():
    client = _client(time_range=("22:00:00", "02:00:00"))

    result = log_foods(client, "2026-09-30", "23:30", [FoodRequest("Huevo Duro", 1, "grande")])

    assert result.state == "preview"
    assert result.meal_name == "SNACKS"
