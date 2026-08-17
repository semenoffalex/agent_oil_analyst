# Demo rate limit tests

from oil_gas_analyst.rate_limit import RateLimitConfig, RateLimiter, client_key


def test_rate_limit_disabled_when_max_zero():
    limiter = RateLimiter()
    cfg = RateLimitConfig(max_requests=0, window_sec=3600)
    allowed, retry_after = limiter.check("ip:1.2.3.4", cfg)
    assert allowed is True
    assert retry_after == 0


def test_rate_limit_blocks_after_max_in_window():
    limiter = RateLimiter()
    cfg = RateLimitConfig(max_requests=2, window_sec=60)
    assert limiter.check("ip:1.2.3.4", cfg)[0] is True
    assert limiter.check("ip:1.2.3.4", cfg)[0] is True
    allowed, retry_after = limiter.check("ip:1.2.3.4", cfg)
    assert allowed is False
    assert retry_after >= 1


def test_rate_limit_keys_are_per_client():
    limiter = RateLimiter()
    cfg = RateLimitConfig(max_requests=1, window_sec=60)
    assert limiter.check("ip:1.2.3.4", cfg)[0] is True
    assert limiter.check("ip:5.6.7.8", cfg)[0] is True
    assert limiter.check("ip:1.2.3.4", cfg)[0] is False


def test_client_key_prefers_forwarded_for():
    assert client_key({"HTTP_X_FORWARDED_FOR": "203.0.113.9, 10.0.0.1"}, "sess") == "ip:203.0.113.9"


def test_client_key_falls_back_to_session():
    assert client_key({}, "abc") == "session:abc"
