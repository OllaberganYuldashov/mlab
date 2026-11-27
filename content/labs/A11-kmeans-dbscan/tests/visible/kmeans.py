def test_kmeans(ns, params):
    labels = ns.get("labels")
    assert labels is not None and len(set(labels)) == params["k"], "`labels` da aynan k ta klaster bo'lishi kerak"
    assert isinstance(ns.get("inertia"), float), "`inertia` oddiy son bo'lishi kerak (float(...))"
