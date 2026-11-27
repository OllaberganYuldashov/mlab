def test_model_qiymat(ns, params):
    import math

    import mlab
    from sklearn.linear_model import LogisticRegression
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.tree import DecisionTreeClassifier
    df = mlab.load(params["dataset"])
    X = df.drop(columns=[params["target"]])
    y = df[params["target"]]

    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=params["test_size"], random_state=params["seed"], stratify=y
    )

    estimators = dict(
        logreg=LogisticRegression(max_iter=1000),
        knn=KNeighborsClassifier(n_neighbors=5),
        tree=DecisionTreeClassifier(max_depth=4, random_state=0),
    )
    ref = make_pipeline(StandardScaler(), estimators[params["kind"]]).fit(X_train, y_train)
    assert math.isclose(ns["acc"], float(ref.score(X_test, y_test)), rel_tol=1e-9)
    assert list(ns["model"].predict(X_test)) == list(ref.predict(X_test))
