def test_qiymatlar(ns, params):
    import math
    import mlab
    s = mlab.load(params["dataset"])[params["column"]]
    assert math.isclose(ns["mean_value"], float(s.mean()), rel_tol=1e-9)
    assert math.isclose(ns["median_value"], float(s.median()), rel_tol=1e-9)
