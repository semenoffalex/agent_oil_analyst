from oil_gas_analyst.denylist import is_denied, load_denylist


def test_kp_and_subdomain_denied():
    domains = load_denylist()
    assert is_denied("https://www.kp.ru/daily/oil", domains) is True
    assert is_denied("https://news.kp.ru/x", domains) is True


def test_reuters_not_denied():
    domains = load_denylist()
    assert is_denied("https://www.reuters.com/markets/brent", domains) is False
