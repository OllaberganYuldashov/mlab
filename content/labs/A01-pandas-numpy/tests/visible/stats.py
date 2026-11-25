def test_sonlar(ns, params):
    import numbers
    for name in ("mean_value", "median_value"):
        assert name in ns, f"`{name}` o'zgaruvchisi topilmadi"
        assert isinstance(ns[name], numbers.Real), f"`{name}` son bo'lishi kerak"
