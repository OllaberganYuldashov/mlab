import mlab
import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

df = mlab.load("{dataset}")
X = df.drop(columns=["{target}"])
y = df["{target}"]
Xs = StandardScaler().fit_transform(X)
pca = PCA(n_components={n_components}, svd_solver="full").fit(Xs)
explained = float(pca.explained_variance_ratio_.sum())
X_pca = pca.transform(Xs)
full = PCA(svd_solver="full").fit(Xs)
n95 = int(np.argmax(np.cumsum(full.explained_variance_ratio_) >= 0.95) + 1)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size={test_size}, random_state={seed}, stratify=y)
base = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(X_train, y_train)
acc_full = float(base.score(X_test, y_test))
reduced = make_pipeline(
    StandardScaler(), PCA(n_components={n_components}, svd_solver="full"), LogisticRegression(max_iter=1000)
).fit(X_train, y_train)
acc_pca = float(reduced.score(X_test, y_test))
