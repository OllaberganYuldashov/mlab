def test_predict_qiymat(ns, params):
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
    predict_one = ns["predict_one"]
    for i in (params["sample"], 0, len(X) - 1):
        proba = ref.predict_proba(X.iloc[[i]])[0]
        label, confidence = predict_one(X.iloc[i].to_dict())
        assert label == str(ref.classes_[proba.argmax()])
        assert math.isclose(confidence, float(proba.max()), rel_tol=1e-9)
    assert ns["answer"][0] == str(ref.predict(X.iloc[[params["sample"]]])[0])
