def test_kmeans_qiymatlar(ns, params):
    import math

    import mlab
    from sklearn.preprocessing import StandardScaler
    df = mlab.load(params["dataset"])
    X = StandardScaler().fit_transform(df.drop(columns=[params["target"]]))

    from sklearn.cluster import KMeans
    ref = KMeans(n_clusters=params["k"], n_init=10, random_state=params["seed"]).fit(X)
    assert list(ns["labels"]) == list(ref.labels_)
    assert math.isclose(ns["inertia"], float(ref.inertia_), rel_tol=1e-7)
