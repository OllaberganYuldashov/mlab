def test_model(ns, params):
    from sklearn.pipeline import Pipeline
    assert isinstance(ns.get("model"), Pipeline), "`model` make_pipeline(...) bo'lishi kerak"
    acc = ns.get("acc")
    assert isinstance(acc, float) and 0 <= acc <= 1, "`acc` 0..1 oralig'idagi float bo'lishi kerak"
