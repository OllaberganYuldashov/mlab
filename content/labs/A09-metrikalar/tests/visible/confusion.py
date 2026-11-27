def test_confusion(ns, params):
    assert "cm" in ns, "`cm` topilmadi"
    for name in ("tn", "fp", "fn", "tp"):
        assert isinstance(ns.get(name), int), f"`{name}` butun son bo'lishi kerak (int(...))"
