def test_accuracy(ns, params):
    for name in ("acc_full", "acc_pca"):
        value = ns.get(name)
        assert isinstance(value, float) and 0 <= value <= 1, f"`{name}` 0..1 oralig'idagi float bo'lishi kerak"
