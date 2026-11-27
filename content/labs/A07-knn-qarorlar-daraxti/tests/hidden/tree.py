def test_tree_qiymatlar(ns, params):
    import math
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

    ref = DecisionTreeClassifier(max_depth=params["max_depth"], random_state=params["seed"]).fit(X_train, y_train)
    assert math.isclose(ns["tree_acc"], ref.score(X_test, y_test), rel_tol=1e-9)
    assert ns["tree_depth"] == ref.get_depth()
