def test_pca_qiymatlar(ns, params):
    import math

    import mlab
    import numpy as np
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    df = mlab.load(params["dataset"])
    Xs = StandardScaler().fit_transform(df.drop(columns=[params["target"]]))
    ref = PCA(n_components=params["n_components"], svd_solver="full").fit(Xs)
    assert math.isclose(ns["explained"], float(ref.explained_variance_ratio_.sum()), rel_tol=1e-7)
    assert np.allclose(np.abs(ns["X_pca"]), np.abs(ref.transform(Xs)), atol=1e-6)
