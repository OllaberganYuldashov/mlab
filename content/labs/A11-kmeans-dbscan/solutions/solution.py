import mlab
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

df = mlab.load("{dataset}")
X = StandardScaler().fit_transform(df.drop(columns=["{target}"]))
km = KMeans(n_clusters={k}, n_init=10, random_state={seed}).fit(X)
labels = km.labels_
inertia = float(km.inertia_)
sil = float(silhouette_score(X, labels))
scores = []
for kk in range(2, 7):
    lab = KMeans(n_clusters=kk, n_init=10, random_state={seed}).fit(X).labels_
    scores.append((silhouette_score(X, lab), kk))
best_k = max(scores, key=lambda s: (s[0], -s[1]))[1]
db = DBSCAN(eps={eps}, min_samples={min_samples}).fit(X)
n_clusters = len(set(db.labels_) - set([-1]))
n_noise = int((db.labels_ == -1).sum())
