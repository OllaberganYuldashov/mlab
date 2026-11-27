def test_tree(ns, params):
    from sklearn.tree import DecisionTreeClassifier
    assert isinstance(ns.get("tree"), DecisionTreeClassifier), "`tree` DecisionTreeClassifier bo'lishi kerak"
    assert isinstance(ns.get("tree_depth"), int), "`tree_depth` butun son bo'lishi kerak"
