def test_rbf(ns, params):
    from sklearn.svm import SVC
    assert isinstance(ns.get("svm_rbf"), SVC), "`svm_rbf` SVC bo'lishi kerak"
    assert isinstance(ns.get("n_support"), int), "`n_support` butun son bo'lishi kerak (int(...))"
