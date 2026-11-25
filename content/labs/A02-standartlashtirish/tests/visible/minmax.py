def test_oraliq(ns, params):
    s = ns.get("scaled")
    assert s is not None, "`scaled` o'zgaruvchisi topilmadi"
    assert abs(float(s.min())) < 1e-9 and abs(float(s.max()) - 1) < 1e-9, "min 0 va max 1 bo'lishi kerak"
