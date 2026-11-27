def test_cv(ns, params):
    assert len(ns.get("scores", [])) == params["folds"], "`scores` da har fold uchun bitta natija bo'lishi kerak"
    assert isinstance(ns.get("cv_mean"), float), "`cv_mean` oddiy son bo'lishi kerak (float(...))"
