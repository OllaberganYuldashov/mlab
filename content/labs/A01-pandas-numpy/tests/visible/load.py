def test_df_yuklangan(ns, params):
    import pandas as pd
    assert "df" in ns, "`df` o'zgaruvchisi topilmadi"
    assert isinstance(ns["df"], pd.DataFrame), "`df` pandas DataFrame bo'lishi kerak"


def test_n_rows(ns, params):
    assert "n_rows" in ns, "`n_rows` o'zgaruvchisi topilmadi"
    assert ns["n_rows"] == len(ns["df"]), "`n_rows` qatorlar soniga teng emas"
