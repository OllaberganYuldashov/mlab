def test_winner_qiymati(ns, params):
    assert ns.get("winner") in ("logreg", "knn"), "`winner` \"logreg\" yoki \"knn\" bo'lishi kerak"
