def test_pca(ns, params):
    explained = ns.get("explained")
    assert isinstance(explained, float) and 0 < explained <= 1, "`explained` 0..1 oralig'idagi float bo'lishi kerak"
    X_pca = ns.get("X_pca")
    assert X_pca is not None and X_pca.shape[1] == params["n_components"], "`X_pca` da n_components ta ustun bo'lishi kerak"
