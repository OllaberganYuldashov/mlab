def test_lasso_qiymatlar(ns, params):
    import math
    from sklearn.linear_model import Lasso

    import mlab
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    df = mlab.load(params["dataset"])
    X = df.drop(columns=[params["target"]]).select_dtypes("number")
    y = df[params["target"]]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=params["seed"])
    scaler = StandardScaler().fit(X_train)
    X_train_s, X_test_s = scaler.transform(X_train), scaler.transform(X_test)

    ref = Lasso(alpha=params["alpha"], max_iter=10000).fit(X_train_s, y_train)
    assert math.isclose(ns["lasso_r2"], ref.score(X_test_s, y_test), rel_tol=1e-6)
    assert ns["zero_coefs"] == int((ref.coef_ == 0).sum())
