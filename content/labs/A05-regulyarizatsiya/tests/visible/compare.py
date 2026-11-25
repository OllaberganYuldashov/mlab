def test_best_qiymati(ns, params):
    assert ns.get("best") in ("ridge", "lasso"), "`best` \"ridge\" yoki \"lasso\" bo'lishi kerak"
