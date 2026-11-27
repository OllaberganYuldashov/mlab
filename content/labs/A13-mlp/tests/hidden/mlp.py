def test_mlp_qiymat(ns, params):
    import math

    import mlab
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    df = mlab.load(params["dataset"])
    X = df.drop(columns=[params["target"]])
    y = df[params["target"]]

    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=params["test_size"], random_state=params["seed"], stratify=y
    )

    h = params["hidden"]
    ref = make_pipeline(
        StandardScaler(), MLPClassifier(hidden_layer_sizes=(h,), alpha=params["alpha"], max_iter=500, random_state=params["seed"])
    ).fit(X_train, y_train)
    assert math.isclose(ns["acc"], float(ref.score(X_test, y_test)), rel_tol=1e-9)
    assert list(ns["model"].predict(X_test)) == list(ref.predict(X_test))
