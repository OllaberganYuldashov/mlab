def test_bittadan(ns, params):
    import pandas as pd
    enc = ns.get("encoded")
    assert isinstance(enc, pd.DataFrame), "`encoded` DataFrame bo'lishi kerak"
    assert (enc.astype(int).sum(axis=1) == 1).all(), "har qatorda aynan bitta 1 bo'lishi kerak"
