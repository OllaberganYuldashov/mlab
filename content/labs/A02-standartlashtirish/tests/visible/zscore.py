def test_z_series(ns, params):
    import pandas as pd
    assert isinstance(ns.get("z"), pd.Series), "`z` pandas Series bo'lishi kerak"
    assert len(ns["z"]) == len(ns["df"]), "`z` uzunligi `df` bilan bir xil bo'lishi kerak"
