from oil_gas_analyst.routes import is_forecast_request, is_time_sensitive, load_route_lists


def test_forecast_verb_russian_hits():
    lists = load_route_lists()
    assert is_forecast_request("спрогнозируй цену Brent на 3 месяца", lists) is True


def test_forecast_verb_english_hits():
    lists = load_route_lists()
    assert is_forecast_request("predict WTI range for 90 days", lists) is True


def test_horizon_without_verb_is_not_forecast_request():
    lists = load_route_lists()
    assert is_forecast_request("Brent in 3 months", lists) is False
    assert is_forecast_request("What's Brent?", lists) is False
    assert is_forecast_request("Where is Brent headed?", lists) is False


def test_prognoz_as_request_hits_but_prognozakh_does_not():
    lists = load_route_lists()
    assert is_forecast_request("прогноз цены Brent на 3 месяца", lists) is True
    assert (
        is_forecast_request(
            "Какой тренд в прогнозах цен на нефть на ближайший месяц?", lists
        )
        is False
    )


def test_time_sensitive_today_hits():
    lists = load_route_lists()
    assert is_time_sensitive("What's Brent today?", lists) is True
    assert is_time_sensitive("what's the weather today?", lists) is True


def test_bare_demand_question_is_not_time_sensitive():
    lists = load_route_lists()
    assert is_time_sensitive("What is OPEC's 2026 world oil demand outlook?", lists) is False
