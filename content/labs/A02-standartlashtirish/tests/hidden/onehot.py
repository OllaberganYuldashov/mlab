def test_ustunlar(ns, params):
    import mlab
    cat = params["category"]
    values = mlab.load(params["dataset"])[cat]
    enc = ns["encoded"]
    assert set(enc.columns) == {f"{cat}_{v}" for v in values.unique()}
    for v in values.unique():
        assert (enc[f"{cat}_{v}"].astype(bool) == (values == v)).all()
