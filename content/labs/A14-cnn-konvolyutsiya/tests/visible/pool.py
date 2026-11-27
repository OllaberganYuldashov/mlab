def test_pool(ns, params):
    pooled = ns.get("pooled")
    assert pooled is not None and pooled.shape == (3, 3), "`pooled` 3×3 bo'lishi kerak"
