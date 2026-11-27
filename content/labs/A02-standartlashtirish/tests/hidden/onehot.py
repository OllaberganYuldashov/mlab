def test_ustunlar(ns, params):
    import mlab
    cat = params["category"]
    values = mlab.load(params["dataset"])[cat]
    pre = params["prefix"]
    enc = ns["encoded"]
    assert set(enc.columns) == {f"{pre}_{v}" for v in values.unique()}
    for v in values.unique():
        assert (enc[f"{pre}_{v}"].astype(bool) == (values == v)).all()
