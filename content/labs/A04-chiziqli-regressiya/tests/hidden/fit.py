def test_koeffitsientlar(ns, params):
    import numpy as np
    import mlab
    from sklearn.linear_model import LinearRegression
    from sklearn.model_selection import train_test_split
    df = mlab.load(params["dataset"])
    X, y = df[params["features"]], df[params["target"]]
    X_train, _, y_train, _ = train_test_split(X, y, test_size=params["test_size"], random_state=params["seed"])
    ref = LinearRegression().fit(X_train, y_train)
    assert np.allclose(ns["model"].coef_, ref.coef_, rtol=1e-6)
    assert np.isclose(ns["model"].intercept_, ref.intercept_, rtol=1e-6)
