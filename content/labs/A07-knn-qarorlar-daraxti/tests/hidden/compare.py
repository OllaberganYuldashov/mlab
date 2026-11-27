def test_best_model_togri(ns, params):
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.tree import DecisionTreeClassifier

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

    k = KNeighborsClassifier(n_neighbors=params["k"]).fit(X_train_s, y_train).score(X_test_s, y_test)
    t = DecisionTreeClassifier(max_depth=params["max_depth"], random_state=params["seed"])
    t = t.fit(X_train, y_train).score(X_test, y_test)
    assert ns["best_model"] == ("knn" if k >= t else "tree")
