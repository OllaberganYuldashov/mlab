def test_winner_togri(ns, params):

    import mlab
    from sklearn.model_selection import KFold
    df = mlab.load(params["dataset"])
    X = df.drop(columns=[params["target"]])
    y = df[params["target"]]
    cv = KFold(n_splits=params["folds"], shuffle=True, random_state=params["seed"])

    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    ref_cv = float(cross_val_score(make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)), X, y, cv=cv).mean())

    from sklearn.model_selection import GridSearchCV
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    ref = GridSearchCV(
        make_pipeline(StandardScaler(), KNeighborsClassifier()),
        param_grid=dict(kneighborsclassifier__n_neighbors=[1, 3, 5, 7, 9, 11]),
        cv=cv,
    ).fit(X, y)

    assert ns["winner"] == ("logreg" if ref_cv >= float(ref.best_score_) else "knn")
