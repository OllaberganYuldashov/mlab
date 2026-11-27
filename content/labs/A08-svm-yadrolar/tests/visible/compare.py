def test_best_kernel_qiymati(ns, params):
    assert ns.get("best_kernel") in ("linear", "rbf"), "`best_kernel` \"linear\" yoki \"rbf\" bo'lishi kerak"
