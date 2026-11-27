def test_model_qiymatlar(ns, params):
    import math
    from sklearn.linear_model import LogisticRegression

    import mlab
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    df = mlab.load(params["dataset"])
    X = df.drop(columns=[params["target"]])
    y = df[params["target"]]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=params["seed"], stratify=y
    )
    scaler = StandardScaler().fit(X_train)
    X_train_s, X_test_s = scaler.transform(X_train), scaler.transform(X_test)

    ref = LogisticRegression(C=params["c"], max_iter=1000).fit(X_train_s, y_train)
    assert ns["model"].C == params["c"]
    assert math.isclose(ns["acc"], ref.score(X_test_s, y_test), rel_tol=1e-9)
