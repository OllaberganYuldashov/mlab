def test_best_pair_turi(ns, params):
    assert isinstance(ns.get("best_pair"), str), "`best_pair` ustun nomi (satr) bo'lishi kerak"
    assert ns["best_pair"] != params["column"], "ustunning o'zini emas, boshqa ustunni tanlang"
