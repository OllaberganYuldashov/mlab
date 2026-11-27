def test_linear(ns, params):
    from sklearn.svm import SVC
    assert isinstance(ns.get("svm_linear"), SVC), "`svm_linear` SVC bo'lishi kerak"
    assert ns["svm_linear"].kernel == "linear", "kernel=\"linear\" bo'lishi kerak"
    assert "linear_acc" in ns, "`linear_acc` topilmadi"
