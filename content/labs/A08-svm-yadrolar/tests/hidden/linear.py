def test_linear_qiymatlar(ns, params):
    import math
    from sklearn.svm import SVC

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

    ref = SVC(kernel="linear", C=params["c"]).fit(X_train_s, y_train)
    assert ns["svm_linear"].C == params["c"]
    assert math.isclose(ns["linear_acc"], ref.score(X_test_s, y_test), rel_tol=1e-9)
