import mlab
from sklearn.linear_model import Lasso, Ridge
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

df = mlab.load("{dataset}")
X = df.drop(columns=["{target}"]).select_dtypes("number")
y = df["{target}"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state={seed})
scaler = StandardScaler().fit(X_train)
X_train_s = scaler.transform(X_train)
X_test_s = scaler.transform(X_test)
ridge = Ridge(alpha={alpha}).fit(X_train_s, y_train)
ridge_r2 = ridge.score(X_test_s, y_test)
lasso = Lasso(alpha={alpha}, max_iter=10000).fit(X_train_s, y_train)
lasso_r2 = lasso.score(X_test_s, y_test)
zero_coefs = int((lasso.coef_ == 0).sum())
best = "ridge" if ridge_r2 >= lasso_r2 else "lasso"
