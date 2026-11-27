def test_params_qiymat(ns, params):
    import math

    import mlab
    from sklearn.neural_network import MLPClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    df = mlab.load(params["dataset"])
    X = df.drop(columns=[params["target"]])
    y = df[params["target"]]

    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=params["test_size"], random_state=params["seed"], stratify=y
    )

    h = params["hidden"]
    n_in = X.shape[1]
    n_classes = y.nunique()
    n_out = 1 if n_classes == 2 else n_classes
    assert ns["n_params"] == n_in * h + h + h * n_out + n_out
