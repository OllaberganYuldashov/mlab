import mlab
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

df = mlab.load("{dataset}")
X = df.drop(columns=["{target}"])
y = df["{target}"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state={seed}, stratify=y)
scaler = StandardScaler().fit(X_train)
X_train_s = scaler.transform(X_train)
X_test_s = scaler.transform(X_test)

knn = KNeighborsClassifier(n_neighbors={k}).fit(X_train_s, y_train)
knn_acc = knn.score(X_test_s, y_test)
tree = DecisionTreeClassifier(max_depth={max_depth}, random_state={seed}).fit(X_train, y_train)
tree_acc = tree.score(X_test, y_test)
tree_depth = tree.get_depth()
best_model = "knn" if knn_acc >= tree_acc else "tree"
