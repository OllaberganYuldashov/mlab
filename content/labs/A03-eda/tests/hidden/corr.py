def test_best_pair(ns, params):
    import mlab
    df = mlab.load(params["dataset"]).select_dtypes("number")
    corr = df.corr()[params["column"]].drop(params["column"]).abs()
    assert ns["best_pair"] == corr.idxmax()
