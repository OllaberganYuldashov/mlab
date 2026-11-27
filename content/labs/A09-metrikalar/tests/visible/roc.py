def test_auc(ns, params):
    assert isinstance(ns.get("auc"), float), "`auc` oddiy son bo'lishi kerak (float(...))"
    assert 0 <= ns["auc"] <= 1, "`auc` 0 va 1 orasida bo'lishi kerak"
