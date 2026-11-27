def test_dbscan(ns, params):
    assert isinstance(ns.get("n_clusters"), int), "`n_clusters` butun son bo'lishi kerak"
    assert isinstance(ns.get("n_noise"), int), "`n_noise` butun son bo'lishi kerak"
