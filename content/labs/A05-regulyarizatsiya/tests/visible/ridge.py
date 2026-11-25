def test_ridge(ns, params):
    from sklearn.linear_model import Ridge
    assert isinstance(ns.get("ridge"), Ridge), "`ridge` Ridge modeli bo'lishi kerak"
    assert hasattr(ns["ridge"], "coef_"), "Ridge o'qitilmagan"
    assert "ridge_r2" in ns, "`ridge_r2` topilmadi"
