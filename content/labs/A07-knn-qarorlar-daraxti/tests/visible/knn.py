def test_knn(ns, params):
    from sklearn.neighbors import KNeighborsClassifier
    assert isinstance(ns.get("knn"), KNeighborsClassifier), "`knn` KNeighborsClassifier bo'lishi kerak"
    assert "knn_acc" in ns, "`knn_acc` topilmadi"
