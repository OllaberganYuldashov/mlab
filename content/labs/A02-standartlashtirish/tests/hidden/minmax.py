def test_scaled_qiymatlar(ns, params):
    import numpy as np
    import mlab
    s = mlab.load(params["dataset"])[params["column"]]
    ref = (s - s.min()) / (s.max() - s.min())
    assert np.allclose(np.asarray(ns["scaled"], dtype=float), ref.to_numpy(), atol=1e-9)
