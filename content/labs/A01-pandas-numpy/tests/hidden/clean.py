def test_chegaralar(ns, params):
    import mlab
    df = mlab.load(params["dataset"])
    col, low, high = params["column"], params["low"], params["high"]
    ref = df[(df[col] >= low) & (df[col] <= high)].reset_index(drop=True)
    clean = ns["clean"]
    assert clean.shape == ref.shape
    assert clean[col].between(low, high).all()
    assert (clean[col].to_numpy() == ref[col].to_numpy()).all()


def test_removed(ns, params):
    import mlab
    df = mlab.load(params["dataset"])
    col = params["column"]
    kept = df[col].between(params["low"], params["high"]).sum()
    assert ns["removed"] == len(df) - kept
