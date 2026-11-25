def test_clean_shakli(ns, params):
    import pandas as pd
    assert isinstance(ns.get("clean"), pd.DataFrame), "`clean` DataFrame bo'lishi kerak"
    assert list(ns["clean"].index) == list(range(len(ns["clean"]))), "indeks 0, 1, 2, ... bo'lishi kerak"
