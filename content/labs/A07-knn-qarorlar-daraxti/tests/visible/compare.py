def test_best_model_qiymati(ns, params):
    assert ns.get("best_model") in ("knn", "tree"), "`best_model` \"knn\" yoki \"tree\" bo'lishi kerak"
