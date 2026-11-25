def test_group_means(ns, params):
    import pandas as pd
    g = ns.get("group_means")
    assert isinstance(g, pd.Series), "`group_means` pandas Series bo'lishi kerak"
    assert len(g) == ns["df"][params["category"]].nunique(), "har kategoriya uchun bitta qiymat bo'lishi kerak"
