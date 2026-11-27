def test_grid(ns, params):
    from sklearn.model_selection import GridSearchCV
    assert isinstance(ns.get("grid"), GridSearchCV), "`grid` GridSearchCV bo'lishi kerak"
    assert ns.get("best_k") in (1, 3, 5, 7, 9, 11), "`best_k` qidiruv ro'yxatidagi qiymat bo'lishi kerak"
