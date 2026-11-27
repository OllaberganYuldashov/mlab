def test_save(ns, params):
    assert isinstance(ns.get("blob"), bytes), "`blob` pickle.dumps(model) natijasi (bytes) bo'lishi kerak"
    assert ns.get("same") is True, "Yuklangan model bir xil bashorat berishi kerak"
