def test_deep(ns, params):
    assert ns.get("better") in ("deep", "shallow"), "`better` \"deep\" yoki \"shallow\" bo'lishi kerak"
