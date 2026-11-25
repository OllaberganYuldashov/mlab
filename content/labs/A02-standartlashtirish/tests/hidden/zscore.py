def test_z_qiymatlar(ns, params):
    import numpy as np
    import mlab
    s = mlab.load(params["dataset"])[params["column"]]
    ref = (s - s.mean()) / s.std(ddof=0)
    assert np.allclose(ns["z"].to_numpy(dtype=float), ref.to_numpy(), atol=1e-9)
