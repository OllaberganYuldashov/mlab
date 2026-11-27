def test_model(ns, params):
    from sklearn.linear_model import LogisticRegression
    assert isinstance(ns.get("model"), LogisticRegression), "`model` LogisticRegression bo'lishi kerak"
    assert hasattr(ns["model"], "coef_"), "Model o'qitilmagan (.fit)"
    assert "acc" in ns, "`acc` topilmadi"
