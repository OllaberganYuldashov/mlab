def test_proba(ns, params):
    assert "proba" in ns, "`proba` topilmadi"
    assert isinstance(ns.get("confidence"), float), "`confidence` oddiy son bo'lishi kerak (float(...))"
