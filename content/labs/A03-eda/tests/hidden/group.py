def test_group_qiymatlar(ns, params):
    import numpy as np
    import mlab
    df = mlab.load(params["dataset"])
    ref = df.groupby(params["category"])[params["column"]].mean()
    got = ns["group_means"].reindex(ref.index)
    assert np.allclose(got.to_numpy(dtype=float), ref.to_numpy(), rtol=1e-9)
