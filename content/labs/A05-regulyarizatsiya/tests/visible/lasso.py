def test_lasso(ns, params):
    from sklearn.linear_model import Lasso
    assert isinstance(ns.get("lasso"), Lasso), "`lasso` Lasso modeli bo'lishi kerak"
    assert isinstance(ns.get("zero_coefs"), int), "`zero_coefs` butun son bo'lishi kerak (int(...))"
