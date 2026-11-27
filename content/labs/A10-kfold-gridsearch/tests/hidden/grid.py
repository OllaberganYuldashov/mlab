def test_grid_qiymatlar(ns, params):
    import math

    import mlab
    from sklearn.model_selection import KFold
    df = mlab.load(params["dataset"])
    X = df.drop(columns=[params["target"]])
    y = df[params["target"]]
    cv = KFold(n_splits=params["folds"], shuffle=True, random_state=params["seed"])

    from sklearn.model_selection import GridSearchCV
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    ref = GridSearchCV(
        make_pipeline(StandardScaler(), KNeighborsClassifier()),
        param_grid=dict(kneighborsclassifier__n_neighbors=[1, 3, 5, 7, 9, 11]),
        cv=cv,
    ).fit(X, y)

    assert ns["best_k"] == ref.best_params_["kneighborsclassifier__n_neighbors"]
    assert math.isclose(ns["best_score"], float(ref.best_score_), rel_tol=1e-9)
