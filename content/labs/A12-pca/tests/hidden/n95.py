def test_n95_qiymat(ns, params):
    import mlab
    import numpy as np
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    df = mlab.load(params["dataset"])
    Xs = StandardScaler().fit_transform(df.drop(columns=[params["target"]]))
    full = PCA(svd_solver="full").fit(Xs)
    assert ns["n95"] == int(np.argmax(np.cumsum(full.explained_variance_ratio_) >= 0.95) + 1)
