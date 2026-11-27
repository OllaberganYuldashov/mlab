def test_silhouette_qiymatlar(ns, params):
    import math

    import mlab
    from sklearn.preprocessing import StandardScaler
    df = mlab.load(params["dataset"])
    X = StandardScaler().fit_transform(df.drop(columns=[params["target"]]))

    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    labels = KMeans(n_clusters=params["k"], n_init=10, random_state=params["seed"]).fit(X).labels_
    assert math.isclose(ns["sil"], float(silhouette_score(X, labels)), rel_tol=1e-7)
    scores = []
    for kk in range(2, 7):
        lab = KMeans(n_clusters=kk, n_init=10, random_state=params["seed"]).fit(X).labels_
        scores.append((silhouette_score(X, lab), kk))
    assert ns["best_k"] == max(scores, key=lambda s: (s[0], -s[1]))[1]
