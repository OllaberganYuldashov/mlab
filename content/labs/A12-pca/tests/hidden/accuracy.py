def test_aniqliklar(ns, params):
    import math

    import mlab
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    df = mlab.load(params["dataset"])
    X = df.drop(columns=[params["target"]])
    y = df[params["target"]]

    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=params["test_size"], random_state=params["seed"], stratify=y
    )

    base = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(X_train, y_train)
    reduced = make_pipeline(
        StandardScaler(), PCA(n_components=params["n_components"], svd_solver="full"), LogisticRegression(max_iter=1000)
    ).fit(X_train, y_train)
    assert math.isclose(ns["acc_full"], float(base.score(X_test, y_test)), rel_tol=1e-9)
    assert math.isclose(ns["acc_pca"], float(reduced.score(X_test, y_test)), rel_tol=1e-9)
