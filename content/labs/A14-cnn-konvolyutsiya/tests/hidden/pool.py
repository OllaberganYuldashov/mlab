def test_pool_qiymat(ns, params):

    import mlab
    import numpy as np
    from scipy.signal import correlate2d
    df = mlab.load("digits")
    images = df.drop(columns=["digit"]).to_numpy().reshape(-1, 8, 8)
    K = np.array(params["kernel"])

    def features(img):
        fmap = np.maximum(correlate2d(img, K, mode="valid"), 0)
        return fmap.reshape(3, 2, 3, 2).max(axis=(1, 3))

    assert np.array_equal(np.asarray(ns["pooled"]), features(images[params["image"]]))
