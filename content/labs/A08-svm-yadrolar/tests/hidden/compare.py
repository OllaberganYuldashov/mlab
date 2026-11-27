def test_best_kernel_togri(ns, params):
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

    lin = SVC(kernel="linear", C=params["c"]).fit(X_train_s, y_train).score(X_test_s, y_test)
    rbf = SVC(kernel="rbf", C=params["c"], gamma="scale").fit(X_train_s, y_train).score(X_test_s, y_test)
    assert ns["best_kernel"] == ("linear" if lin >= rbf else "rbf")
