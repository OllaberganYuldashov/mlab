def test_metrics(ns, params):
    for name in ("precision", "recall", "f1"):
        assert isinstance(ns.get(name), float), f"`{name}` oddiy son bo'lishi kerak (float(...))"
        assert 0 <= ns[name] <= 1, f"`{name}` 0 va 1 orasida bo'lishi kerak"
