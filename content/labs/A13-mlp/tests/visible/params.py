def test_params(ns, params):
    n_params = ns.get("n_params")
    assert isinstance(n_params, int) and n_params > 0, "`n_params` musbat butun son bo'lishi kerak (int(...))"
