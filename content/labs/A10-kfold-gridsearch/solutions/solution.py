import mlab
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, KFold, cross_val_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

df = mlab.load("{dataset}")
X = df.drop(columns=["{target}"])
y = df["{target}"]
cv = KFold(n_splits={folds}, shuffle=True, random_state={seed})
scores = cross_val_score(make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)), X, y, cv=cv)
cv_mean = float(scores.mean())
grid = GridSearchCV(
    make_pipeline(StandardScaler(), KNeighborsClassifier()),
    param_grid=dict(kneighborsclassifier__n_neighbors=[1, 3, 5, 7, 9, 11]),
    cv=cv,
).fit(X, y)
best_k = grid.best_params_["kneighborsclassifier__n_neighbors"]
best_score = float(grid.best_score_)
winner = "logreg" if cv_mean >= best_score else "knn"
