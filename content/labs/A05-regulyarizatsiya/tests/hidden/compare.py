def test_best_togri(ns, params):
    from sklearn.linear_model import Lasso, Ridge

    import mlab
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    df = mlab.load(params["dataset"])
    X = df.drop(columns=[params["target"]]).select_dtypes("number")
    y = df[params["target"]]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=params["seed"])
    scaler = StandardScaler().fit(X_train)
    X_train_s, X_test_s = scaler.transform(X_train), scaler.transform(X_test)

    r = Ridge(alpha=params["alpha"]).fit(X_train_s, y_train).score(X_test_s, y_test)
    la = Lasso(alpha=params["alpha"], max_iter=10000).fit(X_train_s, y_train).score(X_test_s, y_test)
    assert ns["best"] == ("ridge" if r >= la else "lasso")
