def test_model(ns, params):
    from sklearn.linear_model import LinearRegression
    assert isinstance(ns.get("model"), LinearRegression), "`model` LinearRegression bo'lishi kerak"
    assert hasattr(ns["model"], "coef_"), "model o'qitilmagan (fit chaqirilmagan)"
