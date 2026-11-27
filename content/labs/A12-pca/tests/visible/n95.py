def test_n95(ns, params):
    n95 = ns.get("n95")
    assert isinstance(n95, int) and n95 >= 1, "`n95` musbat butun son bo'lishi kerak (int(...))"
