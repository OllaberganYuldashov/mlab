def test_classify_qiymat(ns, params):
    import math

    import mlab
    import numpy as np
    from scipy.signal import correlate2d
    df = mlab.load("digits")
    images = df.drop(columns=["digit"]).to_numpy().reshape(-1, 8, 8)
    K = np.array(params["kernel"])

    def features(img):
        fmap = np.maximum(correlate2d(img, K, mode="valid"), 0)
        return fmap.reshape(3, 2, 3, 2).max(axis=(1, 3))

    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    y = df["digit"]
    F = np.array([features(img).ravel() for img in images])
    assert np.array_equal(np.asarray(ns["F"]), F)
    t, s = params["test_size"], params["seed"]
    F_train, F_test, y_train, y_test = train_test_split(F, y, test_size=t, random_state=s, stratify=y)
    conv = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(F_train, y_train)
    assert math.isclose(ns["acc_conv"], float(conv.score(F_test, y_test)), rel_tol=1e-9)
    P = df.drop(columns=["digit"])
    P_train, P_test, _, _ = train_test_split(P, y, test_size=t, random_state=s, stratify=y)
    raw = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(P_train, y_train)
    assert math.isclose(ns["acc_raw"], float(raw.score(P_test, y_test)), rel_tol=1e-9)
