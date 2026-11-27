def test_predict(ns, params):
    assert callable(ns.get("predict_one")), "`predict_one(row)` funksiyasi bo'lishi kerak"
    answer = ns.get("answer")
    assert isinstance(answer, tuple) and len(answer) == 2, "`answer` (label, confidence) juftligi bo'lishi kerak"
    assert isinstance(answer[0], str), "label `str` bo'lishi kerak"
    assert isinstance(answer[1], float) and 0 <= answer[1] <= 1, "confidence 0..1 oralig'idagi float bo'lishi kerak"
