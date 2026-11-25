def test_metrikalar(ns, params):
    import numbers
    assert isinstance(ns.get("r2"), numbers.Real), "`r2` son bo'lishi kerak"
    assert isinstance(ns.get("mse"), numbers.Real), "`mse` son bo'lishi kerak"
    assert ns["mse"] >= 0, "MSE manfiy bo'lmaydi"
