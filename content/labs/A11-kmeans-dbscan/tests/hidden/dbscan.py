def test_dbscan_qiymatlar(ns, params):

    import mlab
    from sklearn.preprocessing import StandardScaler
    df = mlab.load(params["dataset"])
    X = StandardScaler().fit_transform(df.drop(columns=[params["target"]]))

    from sklearn.cluster import DBSCAN
    db = DBSCAN(eps=params["eps"], min_samples=params["min_samples"]).fit(X)
    assert ns["n_clusters"] == len(set(db.labels_) - set([-1]))
    assert ns["n_noise"] == int((db.labels_ == -1).sum())
