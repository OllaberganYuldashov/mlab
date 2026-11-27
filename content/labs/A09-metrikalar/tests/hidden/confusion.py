def test_confusion_qiymatlar(ns, params):
    from sklearn.metrics import confusion_matrix

    import mlab
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    df = mlab.load(params["dataset"])
    X = df.drop(columns=[params["target"]])
    y = (df[params["target"]] == params["positive"]).astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=params["seed"], stratify=y
    )
    scaler = StandardScaler().fit(X_train)
    X_train_s, X_test_s = scaler.transform(X_train), scaler.transform(X_test)
    model = LogisticRegression(max_iter=1000).fit(X_train_s, y_train)
    pred = model.predict(X_test_s)

    tn, fp, fn, tp = (int(v) for v in confusion_matrix(y_test, pred).ravel())
    assert (ns["tn"], ns["fp"], ns["fn"], ns["tp"]) == (tn, fp, fn, tp)
