def test_classify(ns, params):
    F = ns.get("F")
    assert F is not None and F.shape == (1797, 9), "`F` 1797×9 bo'lishi kerak (har tasvirdan 9 belgi)"
    for name in ("acc_conv", "acc_raw"):
        value = ns.get(name)
        assert isinstance(value, float) and 0 <= value <= 1, f"`{name}` 0..1 oralig'idagi float bo'lishi kerak"
