def test_split_bor(ns, params):
    for name in ("X_train", "X_test", "y_train", "y_test"):
        assert name in ns, f"`{name}` o'zgaruvchisi topilmadi"
    assert len(ns["X_train"]) == len(ns["y_train"]), "X_train va y_train uzunligi bir xil bo'lishi kerak"
