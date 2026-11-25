def test_togri_dataset(ns, params):
    import mlab
    ref = mlab.load(params["dataset"])
    assert ns["df"].shape == ref.shape
    assert list(ns["df"].columns) == list(ref.columns)
