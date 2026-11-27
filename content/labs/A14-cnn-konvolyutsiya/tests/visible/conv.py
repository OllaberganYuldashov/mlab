def test_conv(ns, params):
    fmap = ns.get("fmap")
    assert fmap is not None and fmap.shape == (6, 6), "`fmap` 6×6 bo'lishi kerak (8 - 3 + 1 = 6)"
    assert (fmap >= 0).all(), "ReLU dan keyin manfiy qiymat bo'lmaydi (np.maximum(..., 0))"
