def test_unsure(ns, params):
    assert isinstance(ns.get("least_sure"), int), "`least_sure` butun son bo'lishi kerak (int(...))"
    assert "least_sure_class" in ns, "`least_sure_class` topilmadi"
