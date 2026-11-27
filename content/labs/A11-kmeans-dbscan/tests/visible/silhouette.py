def test_silhouette(ns, params):
    sil = ns.get("sil")
    assert isinstance(sil, float) and -1 <= sil <= 1, "`sil` -1..1 oralig'idagi float bo'lishi kerak"
    assert ns.get("best_k") in (2, 3, 4, 5, 6), "`best_k` 2..6 oralig'ida bo'lishi kerak"
