def test_split_togri(ns, params):
    import mlab
    from sklearn.model_selection import train_test_split
    df = mlab.load(params["dataset"])
    X, y = df[params["features"]], df[params["target"]]
    _, X_test, _, _ = train_test_split(X, y, test_size=params["test_size"], random_state=params["seed"])
    assert list(ns["X_test"].index) == list(X_test.index)
    assert list(ns["X_test"].columns) == params["features"]
