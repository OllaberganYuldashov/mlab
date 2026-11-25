def test_metrika_qiymatlari(ns, params):
    import math
    import mlab
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_squared_error, r2_score
    from sklearn.model_selection import train_test_split
    df = mlab.load(params["dataset"])
    X, y = df[params["features"]], df[params["target"]]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=params["test_size"], random_state=params["seed"])
    pred = LinearRegression().fit(X_train, y_train).predict(X_test)
    assert math.isclose(ns["r2"], r2_score(y_test, pred), rel_tol=1e-6)
    assert math.isclose(ns["mse"], mean_squared_error(y_test, pred), rel_tol=1e-6)
