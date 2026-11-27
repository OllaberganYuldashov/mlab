def test_cv_qiymat(ns, params):
    import math

    import mlab
    from sklearn.model_selection import KFold
    df = mlab.load(params["dataset"])
    X = df.drop(columns=[params["target"]])
    y = df[params["target"]]
    cv = KFold(n_splits=params["folds"], shuffle=True, random_state=params["seed"])

    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import cross_val_score
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    ref_cv = float(cross_val_score(make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)), X, y, cv=cv).mean())

    assert math.isclose(ns["cv_mean"], ref_cv, rel_tol=1e-9)
