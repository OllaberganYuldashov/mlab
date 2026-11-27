def test_metrics_qiymatlar(ns, params):
    import math
    from sklearn.metrics import f1_score, precision_score, recall_score

    import mlab
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    df = mlab.load(params["dataset"])
    X = df.drop(columns=[params["target"]])
    y = (df[params["target"]] == params["positive"]).astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=params["seed"], stratify=y
    )
    scaler = StandardScaler().fit(X_train)
    X_train_s, X_test_s = scaler.transform(X_train), scaler.transform(X_test)
    model = LogisticRegression(max_iter=1000).fit(X_train_s, y_train)
    pred = model.predict(X_test_s)

    assert math.isclose(ns["precision"], precision_score(y_test, pred), rel_tol=1e-9)
    assert math.isclose(ns["recall"], recall_score(y_test, pred), rel_tol=1e-9)
    assert math.isclose(ns["f1"], f1_score(y_test, pred), rel_tol=1e-9)
